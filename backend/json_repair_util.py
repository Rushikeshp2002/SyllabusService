"""
JSON repair for truncated LLM responses.

When Gemini hits max_output_tokens it cuts off mid-JSON.
This module recovers the truncated output by closing all open structures.

Industry-standard approach used by OpenAI, Anthropic tooling, and LLM frameworks.
"""

import re
import json
import logging

logger = logging.getLogger(__name__)


def repair_truncated_json(raw: str) -> str:
    """
    Attempt to repair a truncated JSON string by closing all open structures.

    Strategy:
    1. Track the nesting stack (object/array)
    2. Track whether we're inside a string (and handle escape sequences)
    3. At EOF, close any unclosed string, then close all open structures
    4. Return repaired JSON

    This is a best-effort repair — it preserves ALL content up to the truncation
    point and adds the minimum closing tokens needed to make it valid JSON.
    """
    if not raw or not raw.strip():
        raise ValueError("Empty response from Gemini")

    raw = raw.strip()

    # If it already parses, no repair needed
    try:
        json.loads(raw)
        return raw
    except json.JSONDecodeError:
        pass

    # --- Walk the string character by character ---
    stack = []          # 'o' = object, 'a' = array
    in_string = False
    escaped = False
    last_good_pos = 0   # position of last 'complete' value

    i = 0
    while i < len(raw):
        ch = raw[i]

        if escaped:
            escaped = False
            i += 1
            continue

        if ch == '\\' and in_string:
            escaped = True
            i += 1
            continue

        if ch == '"':
            in_string = not in_string
            i += 1
            continue

        if in_string:
            i += 1
            continue

        # Not in a string
        if ch == '{':
            stack.append('o')
        elif ch == '[':
            stack.append('a')
        elif ch == '}':
            if stack and stack[-1] == 'o':
                stack.pop()
                last_good_pos = i + 1
            # mismatched: ignore
        elif ch == ']':
            if stack and stack[-1] == 'a':
                stack.pop()
                last_good_pos = i + 1
            # mismatched: ignore

        i += 1

    # --- Build the repaired suffix ---
    suffix_parts = []

    # If we're mid-string, close it (value will be incomplete but valid JSON)
    if in_string:
        # Remove any trailing incomplete escape
        suffix_parts.append('"')

    # Close all open structures in reverse order
    for frame in reversed(stack):
        if frame == 'o':
            # We need to close an object. If the last char before cut is a comma
            # or a colon (incomplete key-value), we need to handle it.
            # Easiest: just close the block. Pydantic optional fields handle None.
            suffix_parts.append('}')
        else:
            suffix_parts.append(']')

    suffix = ''.join(suffix_parts)

    if suffix:
        repaired = raw + suffix
        logger.warning(
            f"JSON was truncated. Repaired by appending: {repr(suffix[:80])} "
            f"(stack depth was {len(stack)})"
        )
    else:
        repaired = raw

    # Validate the repair
    try:
        json.loads(repaired)
        return repaired
    except json.JSONDecodeError as e:
        # The truncation happened in a complex place (e.g., mid-key).
        # Fall back to truncating at the last_good_pos and re-closing.
        logger.warning(f"First repair attempt failed ({e}), trying truncate-at-last-good approach")
        return _repair_at_last_good(raw, last_good_pos)


def _repair_at_last_good(raw: str, last_good_pos: int) -> str:
    """
    Fallback: truncate to the last fully-closed JSON boundary and re-close.
    """
    # Try progressively shorter truncations
    for end in range(len(raw), last_good_pos - 1, -1):
        candidate = raw[:end]
        # Build stack for this candidate
        stack, in_string, escaped = [], False, False

        for ch in candidate:
            if escaped:
                escaped = False
                continue
            if ch == '\\' and in_string:
                escaped = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                stack.append('o')
            elif ch == '[':
                stack.append('a')
            elif ch == '}' and stack and stack[-1] == 'o':
                stack.pop()
            elif ch == ']' and stack and stack[-1] == 'a':
                stack.pop()

        suffix = ('"}' if in_string else '') + ''.join(
            '}' if f == 'o' else ']' for f in reversed(stack)
        )
        try:
            result = candidate + suffix
            json.loads(result)
            logger.warning(
                f"Repaired by truncating to pos {end} of {len(raw)} "
                f"and appending: {repr(suffix[:80])}"
            )
            return result
        except json.JSONDecodeError:
            continue

    raise ValueError(
        f"Could not repair truncated JSON. Raw response length: {len(raw)} chars. "
        "The response may be too malformed to recover."
    )
