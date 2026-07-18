"""Strict timestamp parsing shared by exported-data and prediction contracts."""

from datetime import datetime


def parse_timestamp(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} is required")
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from error
    if timestamp.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return timestamp
