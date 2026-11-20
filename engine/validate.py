"""Input validation shared by all three projects.

Real business automation fails on dirty data, not on the happy path, so every
project validates its input through this module before writing anything.
"""

from __future__ import annotations

import re
from typing import Any

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

# Field kinds a project may ask for.
KINDS = {"text", "email", "int", "money", "choice"}


def validate(record: dict, spec: dict) -> list[tuple[str, str]]:
    """Validate ``record`` against ``spec`` and return [(field, message)].

    ``spec`` maps a field name to a dict with:
        required  bool, default False
        kind      text | email | int | money | choice
        min       numeric or length minimum
        max       numeric or length maximum
        choices   allowed values for kind="choice"
    """
    problems: list[tuple[str, str]] = []

    for field, rules in spec.items():
        value = record.get(field)
        kind = rules.get("kind", "text")
        required = rules.get("required", False)
        blank = value is None or (isinstance(value, str) and not value.strip())

        if blank:
            if required:
                problems.append((field, "is required"))
            continue

        if kind == "email":
            if not EMAIL_RE.match(str(value).strip()):
                problems.append((field, "is not a valid email address"))
            continue

        if kind in {"int", "money"}:
            try:
                number = float(value)
            except (TypeError, ValueError):
                problems.append((field, "must be a number"))
                continue
            if kind == "int" and number != int(number):
                problems.append((field, "must be a whole number"))
                continue
            if "min" in rules and number < rules["min"]:
                problems.append((field, f"must be at least {rules['min']}"))
            if "max" in rules and number > rules["max"]:
                problems.append((field, f"must be at most {rules['max']}"))
            continue

        if kind == "choice":
            allowed = rules.get("choices", [])
            if str(value) not in allowed:
                problems.append((field, f"must be one of {', '.join(map(str, allowed))}"))
            continue

        # text
        text = str(value).strip()
        if "min" in rules and len(text) < rules["min"]:
            problems.append((field, f"must be at least {rules['min']} characters"))
        if "max" in rules and len(text) > rules["max"]:
            problems.append((field, f"must be at most {rules['max']} characters"))

    return problems


def coerce(value: Any, kind: str) -> Any:
    """Convert a CSV/JSON value to the type the database expects."""
    if value is None:
        return None
    if kind in {"int", "money"}:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return str(value).strip()
