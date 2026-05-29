"""Conference discovery via Claude + live web search.

Given a profile describing the user's industry, niche, and what they're selling,
``find_conferences`` asks Claude to research real, upcoming conferences using the
server-side web search tool and return them as structured data tailored to the
user's needs.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date, timedelta

import anthropic

MODEL = "claude-opus-4-8"

# Stable system prompt — kept byte-identical across requests so it stays cached.
# Volatile content (the date window, the user's profile) goes in the user turn.
SYSTEM_PROMPT = """\
You are a meticulous conference scout for businesses. Given a description of a \
user's industry, niche, and what they sell, you find REAL, upcoming professional \
conferences, trade shows, summits, expos, and industry events that are genuinely \
relevant to them.

Rules:
- Use the web_search tool to find current, real events. Search several times with \
different queries (industry terms, the niche, the product category, "conference \
2026", "trade show", "summit", relevant regions).
- NEVER invent events, dates, sponsors, or URLs. Only include an event if you can \
corroborate it from search results, and use the real official event URL.
- Only include events whose start date falls within the requested date window.
- Prefer events where this user could exhibit, sell to buyers, network, speak, or \
learn something directly useful to their niche and offering.
- For each event, explain WHY it matters to THIS specific user (their niche and \
what they're selling) — not just generic industry relevance.
- Aim for 6-12 strong matches, sorted by start date (soonest first). Quality over \
quantity; drop weak or unverifiable matches.

When you are done researching, output your final answer as a single JSON object \
and nothing else (no prose before or after, no markdown fences). Use exactly this \
shape:

{
  "conferences": [
    {
      "name": "string",
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD",
      "location": "City, Country  (or 'Virtual')",
      "format": "in-person | virtual | hybrid",
      "url": "https://official-event-site",
      "topics": ["short", "tags"],
      "description": "one-sentence summary of the event",
      "relevance": "why this event matters for the user's niche and offering",
      "audience": "who attends (buyers, developers, executives, etc.)",
      "estimated_attendees": "rough size, e.g. '~5,000' or 'unknown'"
    }
  ]
}

If you genuinely cannot find suitable events, return {"conferences": []}.
"""

# Cap on how many times we re-send to let the server-side search loop continue.
_MAX_CONTINUATIONS = 6


@dataclass
class Profile:
    """The user's business context used to tailor results."""

    industry: str = ""
    niche: str = ""
    selling: str = ""

    def is_empty(self) -> bool:
        return not (self.industry.strip() or self.niche.strip() or self.selling.strip())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "Profile":
        data = data or {}
        return cls(
            industry=(data.get("industry") or "").strip(),
            niche=(data.get("niche") or "").strip(),
            selling=(data.get("selling") or "").strip(),
        )


class FinderError(Exception):
    """Raised when conference discovery fails for a reason worth showing the user."""


def _build_user_message(profile: Profile, months: int) -> str:
    today = date.today()
    end = today + timedelta(days=int(round(months * 30.4)))
    return (
        f"Today's date is {today.isoformat()}.\n"
        f"Find conferences whose start date is between {today.isoformat()} and "
        f"{end.isoformat()} (the next {months} months).\n\n"
        "Here is the user's business profile:\n"
        f"- Industry: {profile.industry or '(not specified)'}\n"
        f"- Niche / specialty: {profile.niche or '(not specified)'}\n"
        f"- What they're selling: {profile.selling or '(not specified)'}\n\n"
        "Research relevant events and return the JSON object described in your "
        "instructions."
    )


def _extract_text(content) -> str:
    return "".join(block.text for block in content if getattr(block, "type", None) == "text")


def _parse_conferences(text: str) -> list[dict]:
    """Pull the conferences list out of Claude's final text response."""
    candidates: list[str] = []

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        candidates.append(fenced.group(1))

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start : end + 1])

    candidates.append(text)

    for raw in candidates:
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, dict) and isinstance(data.get("conferences"), list):
            return [c for c in data["conferences"] if isinstance(c, dict)]
        if isinstance(data, list):
            return [c for c in data if isinstance(c, dict)]

    raise FinderError(
        "Couldn't parse the conference list from the model's response. Try refreshing again."
    )


def find_conferences(profile: Profile, months: int = 6) -> list[dict]:
    """Research and return conferences tailored to ``profile``.

    Raises ``FinderError`` for user-facing failures (missing key, parse errors).
    """
    if profile.is_empty():
        raise FinderError("Describe your industry, niche, or what you're selling first.")

    try:
        # Generous timeout: the server-side web search loop can take a while.
        client = anthropic.Anthropic(timeout=600.0)
    except anthropic.AnthropicError as exc:  # e.g. missing API key
        raise FinderError(
            "Anthropic client could not start. Set ANTHROPIC_API_KEY and try again."
        ) from exc

    messages = [{"role": "user", "content": _build_user_message(profile, months)}]

    try:
        response = None
        for _ in range(_MAX_CONTINUATIONS):
            response = client.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=messages,
                tools=[
                    {"type": "web_search_20260209", "name": "web_search", "max_uses": 10}
                ],
                thinking={"type": "adaptive"},
                output_config={"effort": "medium"},
            )
            if response.stop_reason == "pause_turn":
                # Server-side tool loop hit its iteration cap — resume it.
                messages.append({"role": "assistant", "content": response.content})
                continue
            break
    except anthropic.AuthenticationError as exc:
        raise FinderError("Invalid or missing ANTHROPIC_API_KEY.") from exc
    except anthropic.RateLimitError as exc:
        raise FinderError("Rate limited by the API. Wait a moment and refresh again.") from exc
    except anthropic.APIError as exc:
        raise FinderError(f"API error while searching: {exc}") from exc
    except TypeError as exc:
        # An unknown-keyword TypeError almost always means the installed SDK is
        # too old for the features this app uses (output_config, adaptive
        # thinking, the web_search tool).
        raise FinderError(
            f"Your Anthropic SDK looks outdated for this app ({exc}). "
            "Upgrade it with: pip install -U anthropic"
        ) from exc

    if response is None:
        raise FinderError("No response from the model. Try again.")

    conferences = _parse_conferences(_extract_text(response.content))
    conferences.sort(key=lambda c: str(c.get("start_date") or "9999"))
    return conferences
