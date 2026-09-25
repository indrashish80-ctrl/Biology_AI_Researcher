"""
ai_router.py
------------
High-throughput AI Router with prioritized fast failover and auto-recovery:
    Groq (llama-3.3-70b-versatile -> 8b fallback) -> NVIDIA NIM (with 503 retry) -> Gemini (gemini-3.8-flash)
"""

from __future__ import annotations

import concurrent.futures
import os
import time
import warnings
from typing import Any, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import OpenAI
from provider_health import ProviderHealthTracker

load_dotenv()
warnings.filterwarnings("ignore", category=UserWarning)

# Verified active model identifiers
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_FALLBACK_MODEL = "llama-3.1-8b-instant"
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b")

PROVIDER_PRIORITY = ("groq", "nvidia", "gemini")


class AIRouter:
    def __init__(self, health_tracker: Optional[ProviderHealthTracker] = None):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.nvidia_key = os.getenv("NVIDIA_NIM_API_KEY")

        self.gemini = genai.Client(api_key=self.gemini_key) if self.gemini_key else None
        self.groq = OpenAI(api_key=self.groq_key, base_url="https://api.groq.com/openai/v1") if self.groq_key else None
        self.nvidia = OpenAI(api_key=self.nvidia_key, base_url="https://integrate.api.nvidia.com/v1") if self.nvidia_key else None

        self.health = health_tracker or ProviderHealthTracker()

    def configured_providers(self) -> List[str]:
        providers = []
        if self.groq:
            providers.append("groq")
        if self.nvidia:
            providers.append("nvidia")
        if self.gemini:
            providers.append("gemini")
        return providers

    def get_available_providers(self) -> List[str]:
        available = [p for p in self.configured_providers() if self.health.is_available(p)]
        return sorted(available, key=lambda p: PROVIDER_PRIORITY.index(p) if p in PROVIDER_PRIORITY else 99)

    def ask_groq(self, prompt: str, model: str = GROQ_MODEL) -> str:
        if not self.groq or not self.health.is_available("groq"):
            raise RuntimeError("Groq unavailable.")
        started = time.perf_counter()
        try:
            resp = self.groq.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2048,
            )
            self.health.record_success("groq", (time.perf_counter() - started) * 1000)
            return resp.choices[0].message.content or ""
        except Exception as error:
            err_msg = str(error)
            # If 429 rate limit or 413 token limit, try the ultra-fast instant model before failing
            if ("429" in err_msg or "rate_limit" in err_msg or "413" in err_msg) and model != GROQ_FALLBACK_MODEL:
                time.sleep(1.5)
                try:
                    resp = self.groq.chat.completions.create(
                        model=GROQ_FALLBACK_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2,
                        max_tokens=1500,
                    )
                    self.health.record_success("groq", (time.perf_counter() - started) * 1000)
                    return resp.choices[0].message.content or ""
                except Exception:
                    pass
            self.health.record_failure("groq", err_msg, (time.perf_counter() - started) * 1000)
            raise

    def ask_nvidia(self, prompt: str, model: str = NVIDIA_MODEL) -> str:
        if not self.nvidia or not self.health.is_available("nvidia"):
            raise RuntimeError("NVIDIA NIM unavailable.")
        started = time.perf_counter()
        
        # Try once, and if 503 (service temporarily overloaded), wait 2s and retry once
        for attempt in range(2):
            try:
                resp = self.nvidia.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=2048,
                )
                self.health.record_success("nvidia", (time.perf_counter() - started) * 1000)
                return resp.choices[0].message.content or ""
            except Exception as error:
                err_msg = str(error)
                if ("503" in err_msg or "overloaded" in err_msg) and attempt == 0:
                    time.sleep(2.0)
                    continue
                self.health.record_failure("nvidia", err_msg, (time.perf_counter() - started) * 1000)
                raise

    def ask_gemini(self, prompt: str, model: str = GEMINI_MODEL) -> str:
        if not self.gemini or not self.health.is_available("gemini"):
            raise RuntimeError("Gemini unavailable.")
        started = time.perf_counter()
        try:
            config = types.GenerateContentConfig(temperature=0.2)
            resp = self.gemini.models.generate_content(model=model, contents=prompt, config=config)
            self.health.record_success("gemini", (time.perf_counter() - started) * 1000)
            return resp.text or ""
        except Exception as error:
            self.health.record_failure("gemini", str(error), (time.perf_counter() - started) * 1000)
            raise

    def _ask_specific(self, prompt: str, provider: str) -> str:
        if provider == "groq":
            return self.ask_groq(prompt)
        if provider == "nvidia":
            return self.ask_nvidia(prompt)
        if provider == "gemini":
            return self.ask_gemini(prompt)
        raise ValueError(f"Unknown provider '{provider}'")

    def ask(self, prompt: str, provider: Optional[str] = None, fallback: bool = True) -> str:
        candidates = [provider] if provider else self.get_available_providers()
        if fallback and provider:
            candidates.extend(p for p in self.get_available_providers() if p != provider)

        if not candidates:
            # If all are cooling down, force clear Groq and try again
            self.health.enable("groq")
            candidates = ["groq"]

        errors = []
        for candidate in candidates:
            if not self.health.is_available(candidate):
                continue
            try:
                return self._ask_specific(prompt, candidate)
            except Exception as exc:
                errors.append(f"{candidate}: {exc}")
                if provider and not fallback:
                    raise

        raise RuntimeError(f"All AI providers failed: {' | '.join(errors)}")

    def ask_parallel(
        self,
        prompts: List[str],
        max_workers: int = 3,
        provider: Optional[str] = None,
    ) -> List[Optional[str]]:
        results: List[Optional[str]] = [None] * len(prompts)

        def _worker(idx: int, p: str):
            try:
                return idx, self.ask(p, provider=provider, fallback=True)
            except Exception:
                return idx, None

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_worker, i, p) for i, p in enumerate(prompts)]
            for future in concurrent.futures.as_completed(futures):
                idx, res = future.result()
                results[idx] = res

        return results