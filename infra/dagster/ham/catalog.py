"""Read pinned HAM schema data without invoking the SDK's client or parser."""

import json
from importlib.resources import files


def load_catalog(name: str) -> dict:
    if name not in ("readings", "models"):
        raise ValueError(f"Unknown HAM catalog: {name}")
    catalog = json.loads(
        files("hamapi").joinpath(f"{name}.json").read_text(encoding="utf-8")
    )
    if not isinstance(catalog, dict) or not catalog:
        raise ValueError(f"{name}.json must be a nonempty object")
    return catalog
