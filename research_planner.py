import json
import re
import time

from ai_router import AIRouter


# ==========================================================
# CONFIGURATION
# ==========================================================

MAX_PLANNER_RETRIES = 3


# ==========================================================
# PROMPT
# ==========================================================

PLANNER_PROMPT = """
You are one component of a general-purpose biology research AI.

The user has supplied this research question:

{question}

Your job is to design a literature-search strategy for this
question.

Generate exactly 5 distinct scientific literature search
queries.

The queries should collectively cover different relevant
dimensions of the question, such as:

- mechanisms
- molecular or cellular causes
- biological pathways
- environmental or physiological factors
- experimental evidence
- conflicting findings
- relevant organisms or disease models
- established terminology and synonyms

Do NOT assume that the question belongs to one particular
subfield of biology.

Use terminology appropriate for scientific literature
databases such as Europe PMC.

Important:
- Do not answer the research question.
- Do not write explanations.
- Do not invent papers.
- Do not cite sources.
- Do not make unsupported scientific claims.
- Return ONLY valid JSON.

Return exactly this structure:

{{
    "research_question": "{question_json}",
    "search_queries": [
        "query 1",
        "query 2",
        "query 3",
        "query 4",
        "query 5"
    ]
}}
"""


# ==========================================================
# JSON PARSER
# ==========================================================

def parse_json_response(text):
    """
    Extract JSON from a model response.

    Models sometimes return JSON inside markdown code fences.
    """

    if not text:
        raise ValueError(
            "Model returned an empty response."
        )

    text = text.strip()

    # Remove markdown code fences.
    if text.startswith("```"):

        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"\s*```$",
            "",
            text
        )

        text = text.strip()

    # Find JSON object if the model added surrounding text.
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:

        raise ValueError(
            "No JSON object found in model response."
        )

    text = text[start:end + 1]

    return json.loads(text)


# ==========================================================
# VALIDATION
# ==========================================================

def validate_plan(plan):
    """
    Validate the structure returned by a model.
    """

    if not isinstance(plan, dict):

        raise ValueError(
            "Research plan is not a JSON object."
        )

    if "research_question" not in plan:

        raise ValueError(
            "Research plan is missing 'research_question'."
        )

    if "search_queries" not in plan:

        raise ValueError(
            "Research plan is missing 'search_queries'."
        )

    queries = plan["search_queries"]

    if not isinstance(queries, list):

        raise ValueError(
            "'search_queries' must be a list."
        )

    cleaned_queries = []

    for query in queries:

        if not isinstance(query, str):
            continue

        query = query.strip()

        if query:
            cleaned_queries.append(query)

    if not cleaned_queries:

        raise ValueError(
            "Research plan contains no usable search queries."
        )

    plan["search_queries"] = cleaned_queries

    return plan


# ==========================================================
# MODEL PLANNER
# ==========================================================

def generate_model_plan(
    router,
    question,
    provider
):
    """
    Ask one AI provider for an independent research plan.

    Failed providers are retried because temporary API/network
    failures should not immediately remove a model from the
    research process.
    """

    question_json = json.dumps(
        question,
        ensure_ascii=False
    )

    prompt = PLANNER_PROMPT.format(
        question=question,
        question_json=question_json
    )

    print()
    print("=" * 80)
    print(
        f"GENERATING PLAN WITH {provider.upper()}"
    )
    print("=" * 80)

    last_error = None

    for attempt in range(1, MAX_PLANNER_RETRIES + 1):

        try:

            response = router.ask(
                prompt,
                provider=provider
            )

            plan = parse_json_response(
                response
            )

            plan = validate_plan(
                plan
            )

            print(
                f"{provider.upper()} planner succeeded "
                f"on attempt {attempt}."
            )

            return plan

        except Exception as error:

            last_error = error

            print()
            print(
                f"{provider.upper()} attempt "
                f"{attempt}/{MAX_PLANNER_RETRIES} failed:"
            )

            print(error)

            if attempt < MAX_PLANNER_RETRIES:

                wait_time = 3 * attempt

                print(
                    f"Retrying {provider.upper()} "
                    f"in {wait_time} seconds..."
                )

                time.sleep(
                    wait_time
                )

    print()
    print(
        f"{provider.upper()} planner failed after "
        f"{MAX_PLANNER_RETRIES} attempts."
    )

    print(
        "The research pipeline will continue using "
        "the other available models."
    )

    print(
        f"Last error: {last_error}"
    )

    return None


# ==========================================================
# QUERY NORMALIZATION
# ==========================================================

def normalize_query(query):
    """
    Normalize a query only for duplicate detection.

    The original query remains unchanged.
    """

    query = query.lower().strip()

    query = re.sub(
        r"\s+",
        " ",
        query
    )

    query = query.strip(
        " .,!?:;\"'"
    )

    return query


# ==========================================================
# MERGE QUERIES
# ==========================================================

def merge_queries(model_plans):
    """
    Merge all successful model plans.

    Different models are NOT ranked against one another.

    Their queries are treated as independent search strategies.
    """

    merged = []

    seen = set()

    for provider, plan in model_plans.items():

        if not plan:
            continue

        for query in plan["search_queries"]:

            normalized = normalize_query(
                query
            )

            if not normalized:
                continue

            if normalized in seen:
                continue

            seen.add(
                normalized
            )

            merged.append(
                {
                    "provider": provider,
                    "query": query
                }
            )

    return merged


# ==========================================================
# PRINT RESULTS
# ==========================================================

def print_plan(
    question,
    model_plans,
    merged_queries
):

    print()
    print("=" * 80)
    print("BIOLOGY RESEARCH PLAN")
    print("=" * 80)

    print()
    print("RESEARCH QUESTION:")
    print("-" * 80)
    print(question)

    # ------------------------------------------------------
    # Individual plans
    # ------------------------------------------------------

    for provider, plan in model_plans.items():

        print()
        print("=" * 80)
        print(
            f"{provider.upper()} SEARCH STRATEGY"
        )
        print("=" * 80)

        if not plan:

            print(
                "No plan returned."
            )

            continue

        for number, query in enumerate(
            plan["search_queries"],
            start=1
        ):

            print(
                f"{number}. {query}"
            )

    # ------------------------------------------------------
    # Combined strategy
    # ------------------------------------------------------

    print()
    print("=" * 80)
    print("COMBINED SEARCH STRATEGY")
    print("=" * 80)

    if not merged_queries:

        print(
            "No search queries were generated."
        )

    else:

        for number, item in enumerate(
            merged_queries,
            start=1
        ):

            print()
            print(
                f"{number}. "
                f"[{item['provider'].upper()}]"
            )

            print(
                f"   {item['query']}"
            )

    print()
    print(
        f"TOTAL UNIQUE SEARCH QUERIES: "
        f"{len(merged_queries)}"
    )


# ==========================================================
# SAVE PLAN
# ==========================================================

def save_plan(
    question,
    model_plans,
    merged_queries,
    filename="research_plan.json"
):

    data = {
        "research_question": question,
        "model_plans": model_plans,
        "merged_queries": merged_queries
    }

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )

    print()
    print(
        f"Research plan saved to: {filename}"
    )


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    print("=" * 80)
    print("MULTI-MODEL BIOLOGY RESEARCH PLANNER")
    print("=" * 80)

    question = input(
        "\nEnter your biology research question:\n> "
    ).strip()

    if not question:

        print()
        print(
            "ERROR: Research question cannot be empty."
        )

        raise SystemExit(1)

    # ------------------------------------------------------
    # Create router
    # ------------------------------------------------------

    router = AIRouter()

    # ------------------------------------------------------
    # Detect providers
    # ------------------------------------------------------

    providers = []

    if router.gemini:
        providers.append("gemini")

    if router.groq:
        providers.append("groq")

    if router.nvidia:
        providers.append("nvidia")

    print()
    print(
        "Available AI providers:",
        ", ".join(
            provider.upper()
            for provider in providers
        )
    )

    if not providers:

        print()
        print(
            "ERROR: No AI providers are configured."
        )

        raise SystemExit(1)

    # ------------------------------------------------------
    # Generate independent plans
    # ------------------------------------------------------

    model_plans = {}

    for provider in providers:

        model_plans[provider] = (
            generate_model_plan(
                router,
                question,
                provider
            )
        )

    # ------------------------------------------------------
    # Merge queries
    # ------------------------------------------------------

    merged_queries = merge_queries(
        model_plans
    )

    # ------------------------------------------------------
    # Display
    # ------------------------------------------------------

    print_plan(
        question,
        model_plans,
        merged_queries
    )

    # ------------------------------------------------------
    # Save
    # ------------------------------------------------------

    save_plan(
        question,
        model_plans,
        merged_queries
    )

    # ------------------------------------------------------
    # Statistics
    # ------------------------------------------------------

    successful = sum(
        1
        for plan in model_plans.values()
        if plan is not None
    )

    total = len(
        model_plans
    )

    print()
    print("=" * 80)
    print("PLANNER COMPLETE")
    print("=" * 80)

    print(
        f"Successful model planners: "
        f"{successful}/{total}"
    )

    print(
        f"Unique search queries: "
        f"{len(merged_queries)}"
    )

    if successful < total:

        print()
        print(
            "WARNING: One or more AI providers failed."
        )

        print(
            "The successful providers were still used."
        )

    else:

        print()
        print(
            "All configured AI providers "
            "completed successfully."
        )
