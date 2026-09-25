"""
http_client.py
--------------
Lightweight HTTP client with disk caching, exponential backoff,
and academic API compliance headers.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError as UrllibHTTPError
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class HttpError(RuntimeError):
    """Raised for HTTP, network, decoding, or response-size failures."""


class HttpClient:
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        timeout: float = 25.0,
        retries: int = 2,
        user_agent: str = "BiologyAIResearcher/1.0 (https://github.com/biology-ai; mailto:researcher@biopipeline.org)",
    ):
        self.timeout = float(timeout)
        self.retries = max(0, int(retries))
        self.user_agent = user_agent
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        max_bytes: int = 20 * 1024 * 1024,
    ) -> Any:
        raw = self.get_bytes(url, params=params, max_bytes=max_bytes)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HttpError(f"Invalid JSON response from {url}: {exc}") from exc

    def get_text(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        max_bytes: int = 20 * 1024 * 1024,
        encoding: str = "utf-8",
    ) -> str:
        raw = self.get_bytes(url, params=params, max_bytes=max_bytes)
        try:
            return raw.decode(encoding, errors="replace")
        except Exception as exc:
            raise HttpError(f"Could not decode response from {url}: {exc}") from exc

    def get_bytes(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        max_bytes: int = 50 * 1024 * 1024,
    ) -> bytes:
        full_url = self._build_url(url, params)
        cache_path = self._cache_path(full_url)

        if cache_path and cache_path.exists():
            try:
                data = cache_path.read_bytes()
                if len(data) <= max_bytes:
                    return data
                cache_path.unlink(missing_ok=True)
            except OSError:
                pass

        last_error: Optional[Exception] = None

        for attempt in range(self.retries + 1):
            try:
                request = Request(
                    full_url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "application/json, text/xml, */*",
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                    method="GET",
                )

                with urlopen(request, timeout=self.timeout) as response:
                    status = getattr(response, "status", 200)
                    if status < 200 or status >= 300:
                        raise HttpError(f"HTTP {status} from {full_url}")

                    data = self._read_limited(response, max_bytes)

                if cache_path:
                    self._write_cache(cache_path, data)

                return data

            except UrllibHTTPError as exc:
                last_error = exc
                retryable = exc.code == 429 or 500 <= exc.code <= 599
                if not retryable or attempt >= self.retries:
                    body = ""
                    try:
                        body = exc.read(300).decode("utf-8", errors="replace")
                    except Exception:
                        pass
                    detail = f"HTTP {exc.code} from {full_url}"
                    if body:
                        detail += f": {body[:300]}"
                    raise HttpError(detail) from exc

            except (URLError, TimeoutError, OSError, HttpError) as exc:
                last_error = exc
                if isinstance(exc, HttpError) and "exceeds limit" in str(exc):
                    raise
                if attempt >= self.retries:
                    raise HttpError(f"Request failed for {full_url}: {exc}") from exc

            time.sleep(min(1.5 ** (attempt + 1), 3.0))

        raise HttpError(f"Request failed for {full_url}: {last_error}")

    @staticmethod
    def _build_url(url: str, params: Optional[Dict[str, Any]]) -> str:
        if not params:
            return url
        clean = []
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                for item in value:
                    clean.append((key, str(item)))
            else:
                clean.append((key, str(value)))
        if not clean:
            return url
        separator = "&" if "?" in url else "?"
        return url + separator + urlencode(clean)

    @staticmethod
    def _read_limited(response: Any, max_bytes: int) -> bytes:
        chunks = []
        total = 0
        chunk_size = 64 * 1024
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise HttpError(f"Response exceeds limit of {max_bytes:,} bytes.")
            chunks.append(chunk)
        return b"".join(chunks)

    def _cache_path(self, url: str) -> Optional[Path]:
        if not self.cache_dir:
            return None
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.bin"

    @staticmethod
    def _write_cache(path: Path, data: bytes) -> None:
        try:
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, path)
        except OSError:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass