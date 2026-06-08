"""Load and validate config.yaml."""

from pathlib import Path
import yaml


def load_config(config_path: Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    if not cfg or "urls" not in cfg:
        raise ValueError(f"Config must contain a 'urls' list: {config_path}")

    for entry in cfg["urls"]:
        if "url" not in entry:
            raise ValueError(f"Each URL entry must have a 'url' field: {entry}")
        entry.setdefault("label", entry["url"])

    cfg.setdefault("filters", {})
    cfg["filters"].setdefault("min_change_chars", 10)
    cfg["filters"].setdefault("ignore_whitespace_only", True)
    cfg["filters"].setdefault("ignore_timestamp_patterns", True)

    # Redis store configuration (optional)
    cfg.setdefault("redis", {})
    cfg["redis"].setdefault("enabled", False)
    cfg["redis"].setdefault("host", "localhost")
    cfg["redis"].setdefault("port", 6379)
    cfg["redis"].setdefault("db", 0)
    cfg["redis"].setdefault("snapshot_ttl_seconds", 7 * 24 * 3600)  # 7 days
    cfg["redis"].setdefault("max_history", 100)

    return cfg
