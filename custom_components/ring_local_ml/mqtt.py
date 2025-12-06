"""MQTT helpers for Ring topic parsing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

SUPPORTED_RING_CATEGORIES = {"camera"}


@dataclass(frozen=True)
class RingTopic:
    """Structured view of a Ring MQTT topic."""

    raw: str
    location_id: str
    category: str
    device_id: str
    topic_suffix: str
    entity: str


def parse_ring_topic(topic: str) -> Optional[RingTopic]:
    """Break down a `ring/<location>/<category>/<device>/...` topic."""

    if not topic:
        return None

    parts = topic.split("/")
    if len(parts) < 4 or parts[0] != "ring":
        return None

    location_id, category, device_id = parts[1:4]
    suffix_parts = parts[4:]
    suffix = "/".join(suffix_parts) if suffix_parts else ""
    entity = suffix_parts[0] if suffix_parts else ""

    return RingTopic(
        raw=topic,
        location_id=location_id,
        category=category,
        device_id=device_id,
        topic_suffix=suffix,
        entity=entity,
    )
