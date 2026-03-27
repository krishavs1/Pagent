"""
Configuration loading helpers.

Planned responsibilities:
- Load global settings from `config/settings.yaml`
- Load a domain config (e.g., `config/politics.yaml`)
- Merge them into a single mapping used for dependency wiring
- Support lightweight overrides from CLI flags in `src/main.py`

This is intentionally minimal: it only loads YAML and performs a deep merge.
No validation or secret management is implemented here yet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping, Optional, Union

import yaml

JsonDict = Dict[str, Any]


def _deep_merge(base: MutableMapping[str, Any], override: Mapping[str, Any]) -> MutableMapping[str, Any]:
    """Recursively merge override into base (mutates base)."""
    for k, v in override.items():
        if isinstance(v, Mapping) and isinstance(base.get(k), Mapping):
            _deep_merge(base[k], v)  # type: ignore[index]
        else:
            base[k] = v
    return base


def load_yaml(path: Union[str, Path]) -> JsonDict:
    """Load a YAML file into a dict."""
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at root of {p}, got {type(data).__name__}")
    return data


def load_config(domain_config_path: Union[str, Path], settings_path: Union[str, Path] = "config/settings.yaml") -> JsonDict:
    """
    Load settings + domain YAML and return a merged dict.

    Domain config values override global settings when keys overlap.
    """
    settings = load_yaml(settings_path)
    domain = load_yaml(domain_config_path)
    return dict(_deep_merge(settings, domain))

