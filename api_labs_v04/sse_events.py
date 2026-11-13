"""Parse a subset of Server-Sent Events from decoded line iterables.

Input lines must already be decoded with a consistent text encoding. This
parser preserves multi-line data fields and yields one dictionary per event.
"""
from __future__ import annotations
from collections.abc import Iterable, Iterator


def iter_sse_events(lines: Iterable[str]) -> Iterator[dict[str, str]]:
    event_type = "message"
    event_id = ""
    payload: list[str] = []
    seen_field = False

    def current() -> dict[str, str]:
        return {"event": event_type, "id": event_id, "data": "\n".join(payload)}

    for raw in lines:
        line = raw.rstrip("\r\n")
        if not line:
            if seen_field:
                yield current()
            event_type = "message"
            payload = []
            seen_field = False
            continue
        if line.startswith(":"):
            continue
        field, sep, value = line.partition(":")
        if sep and value.startswith(" "):
            value = value[1:]
        if field == "data":
            payload.append(value)
            seen_field = True
        elif field == "event":
            event_type = value
            seen_field = True
        elif field == "id" and "\x00" not in value:
            event_id = value
            seen_field = True
    if seen_field:
        yield current()


def is_stream_done(event: dict[str, str]) -> bool:
    return event["data"] == "[DONE]"
