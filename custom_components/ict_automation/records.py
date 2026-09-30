"""Helpers for Protege record configuration and stable entity naming."""

from __future__ import annotations

from copy import deepcopy


RECORD_PREFIXES = {
    "doors": "Door",
    "areas": "Area",
    "inputs": "Input",
    "outputs": "Output",
}


def normalize_records(raw, prefix: str, discovered_names: dict[int, str] | None = None):
    """Normalize legacy string records and current metadata records.

    Legacy records were stored as {"1": "Door name"}. Current records are
    stored as {"1": {"programmed_name": ..., "custom_name": ...}}.
    """
    discovered_names = discovered_names or {}
    if not isinstance(raw, dict):
        return {}

    normalized = {}
    for raw_id, raw_value in raw.items():
        try:
            record_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if record_id < 0:
            continue

        programmed = discovered_names.get(record_id)
        custom = None

        if isinstance(raw_value, dict):
            programmed = raw_value.get("programmed_name") or programmed
            custom = raw_value.get("custom_name")
        else:
            legacy_name = str(raw_value)
            generic = f"{prefix} {record_id}"
            # If the old saved name exactly matches the current WX programmed
            # name, treat it as controller-managed rather than a custom name.
            if programmed and legacy_name == programmed:
                custom = None
            elif legacy_name and legacy_name != generic:
                custom = legacy_name

        normalized[str(record_id)] = {
            "programmed_name": programmed,
            "custom_name": custom,
        }

    return normalized


def effective_name(prefix: str, record_id: int, record) -> str:
    """Return the Home Assistant display name for a record."""
    if isinstance(record, dict):
        return (
            record.get("custom_name")
            or record.get("programmed_name")
            or f"{prefix} {record_id}"
        )
    if record:
        return str(record)
    return f"{prefix} {record_id}"


def build_selected_records(
    prefix: str,
    old_records,
    selected_ids,
    discovered_names: dict[int, str] | None = None,
):
    """Build a new selected-record dictionary preserving custom names."""
    discovered_names = discovered_names or {}
    old = normalize_records(old_records, prefix, discovered_names)
    new = {}

    for record_id in sorted({int(value) for value in selected_ids}):
        if record_id < 0:
            raise ValueError("Record IDs must be non-negative")

        key = str(record_id)
        if key in old:
            record = deepcopy(old[key])
            if record_id in discovered_names:
                record["programmed_name"] = discovered_names[record_id]
                # A legacy custom value identical to the programmed name is not
                # really a custom override; release it back to WX management.
                if record.get("custom_name") == discovered_names[record_id]:
                    record["custom_name"] = None
        else:
            record = {
                "programmed_name": discovered_names.get(record_id),
                "custom_name": None,
            }
        new[key] = record

    return new


def selected_ids(raw_records) -> set[int]:
    """Return the selected database IDs from a record dictionary."""
    if not isinstance(raw_records, dict):
        return set()
    result = set()
    for value in raw_records.keys():
        try:
            record_id = int(value)
        except (TypeError, ValueError):
            continue
        if record_id >= 0:
            result.add(record_id)
    return result


def diff_record_sets(old_records, new_records):
    """Return added, removed and kept record IDs."""
    old_ids = selected_ids(old_records)
    new_ids = selected_ids(new_records)
    return {
        "added": new_ids - old_ids,
        "removed": old_ids - new_ids,
        "kept": old_ids & new_ids,
    }


def unique_ids_for_record(storage_key: str, record_id: int) -> set[str]:
    """Return entity unique IDs created by one Protege database record."""
    if storage_key == "doors":
        return {f"ict_door_{record_id}", f"ict_door_contact_{record_id}"}
    if storage_key == "areas":
        return {f"ict_area_{record_id}"}
    if storage_key == "inputs":
        return {
            f"ict_input_{record_id}",
            f"ict_trouble_{record_id}",
            f"ict_input_bypass_{record_id}",
        }
    if storage_key == "outputs":
        return {f"ict_output_{record_id}"}
    return set()
