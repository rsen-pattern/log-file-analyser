"""AI-powered crawl insights via Pattern Bifrost."""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI


def _client() -> OpenAI | None:
    api_key = os.getenv("BIFROST_API_KEY", "").strip()
    if not api_key:
        return None
    return OpenAI(
        base_url="https://bifrost.pattern.com/openai",
        api_key=api_key,
    )


def generate_insights(summary: dict[str, Any], page: str = "overview") -> str:
    client = _client()
    if client is None:
        return "BIFROST_API_KEY is not configured. Add it to your .env file to enable AI insights."

    if not summary.get("loaded"):
        return "Load log data first, then request AI insights."

    prompt = f"""You are a senior technical SEO analyst reviewing Googlebot crawl logs.

Page context: {page}
Summary metrics (JSON):
{json.dumps(summary, indent=2)}

Provide a concise analysis with:
1. Top 3 issues or risks found in the data
2. Likely root causes
3. Prioritized action items (specific, actionable)
4. Anything that looks healthy or worth monitoring

Keep it practical for an internal SEO/engineering audience. Use bullet points. Under 400 words."""

    try:
        response = client.chat.completions.create(
            model="gpt-5.4-nano",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You analyze server log crawl data for technical SEO issues: "
                        "crawl budget waste, orphan pages, stale URLs, bot spoofing, "
                        "parameter traps, and performance bottlenecks."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
        )
        content = response.choices[0].message.content
        return content.strip() if content else "No insights returned from the model."
    except Exception as exc:  # noqa: BLE001
        return f"Could not generate insights: {exc}"
