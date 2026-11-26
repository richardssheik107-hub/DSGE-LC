"""Persistence and integrity checks for Phase 2 posterior production draws."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from .parameter_transform import PARAMETER_ORDER


REQUIRED_ARRAYS = ("theta", "z", "components", "accepted")


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def metadata_path(path: str | Path) -> Path:
    path = Path(path)
    return path.with_suffix(".metadata.json")


def _stack(results, key):
    return np.stack([np.asarray(result[key]) for result in results])


def save_posterior_artifact(path, results, *, specification, rho_n, battery_sd,
                            seed, parameter_order=PARAMETER_ORDER, force=False):
    """Save production-only chain arrays and an auditable JSON sidecar."""
    path = Path(path)
    sidecar = metadata_path(path)
    if (path.exists() or sidecar.exists()) and not force:
        raise FileExistsError(f"posterior artifact already exists: {path}")
    arrays = {key: _stack(results, key) for key in REQUIRED_ARRAYS}
    theta = arrays["theta"]
    if theta.ndim != 3 or theta.shape[2] != len(parameter_order):
        raise ValueError("posterior theta shape does not match parameter order")
    metadata = {
        "artifact_schema": "phase2_posterior_v1",
        "specification": str(specification),
        "rho_n": float(rho_n),
        "battery_sd": float(battery_sd),
        "production_draws_per_chain": int(theta.shape[1]),
        "chains": int(theta.shape[0]),
        "seed": int(seed),
        "parameter_order": list(parameter_order),
        "production_only": True,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays, parameter_order=np.asarray(parameter_order),
                        specification=np.asarray(str(specification)),
                        rho_n=np.asarray(float(rho_n)), battery_sd=np.asarray(float(battery_sd)),
                        production_draws_per_chain=np.asarray(int(theta.shape[1])),
                        chains=np.asarray(int(theta.shape[0])), seed=np.asarray(int(seed)))
    metadata["artifact_sha256"] = file_sha256(path)
    sidecar.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return metadata


def load_posterior_artifact(path, *, expected_specification=None, expected_rho_n=None,
                            expected_battery_sd=None, bounds=None, require_sidecar=True):
    """Load and validate chain shape, metadata, support, finiteness and stability."""
    path = Path(path)
    sidecar = metadata_path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if require_sidecar and not sidecar.exists():
        raise FileNotFoundError(sidecar)
    metadata = json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.exists() else {}
    if metadata and metadata.get("artifact_sha256") != file_sha256(path):
        raise ValueError("posterior artifact SHA256 mismatch")
    with np.load(path, allow_pickle=False) as raw:
        missing = [key for key in REQUIRED_ARRAYS if key not in raw]
        if missing:
            raise ValueError(f"missing posterior arrays: {missing}")
        arrays = {key: np.asarray(raw[key]) for key in REQUIRED_ARRAYS}
        embedded_order = tuple(str(x) for x in raw["parameter_order"].tolist()) if "parameter_order" in raw else ()
    theta, z, components, accepted = (arrays[key] for key in REQUIRED_ARRAYS)
    if theta.ndim != 3 or theta.shape[0] != 4 or theta.shape[2] != len(PARAMETER_ORDER):
        raise ValueError("posterior theta must have shape (4, production, 14)")
    if z.shape != theta.shape or components.shape != theta.shape[:2] + (5,) or accepted.shape != theta.shape[:2]:
        raise ValueError("posterior array shapes are inconsistent")
    if not all(np.isfinite(arrays[key]).all() for key in ("theta", "z", "components")):
        raise ValueError("posterior artifact contains non-finite values")
    order = tuple(metadata.get("parameter_order", embedded_order))
    if order != PARAMETER_ORDER or (embedded_order and embedded_order != PARAMETER_ORDER):
        raise ValueError("posterior parameter order mismatch")
    if metadata.get("production_only") is not True:
        raise ValueError("posterior artifact is not marked production-only")
    checks = {
        "specification": expected_specification,
        "rho_n": expected_rho_n,
        "battery_sd": expected_battery_sd,
    }
    for key, expected in checks.items():
        if expected is not None and metadata.get(key) != expected:
            raise ValueError(f"posterior metadata mismatch: {key}")
    if metadata.get("chains") != 4 or metadata.get("production_draws_per_chain") != theta.shape[1]:
        raise ValueError("posterior chain metadata mismatch")
    if bounds is not None:
        for j, name in enumerate(PARAMETER_ORDER):
            lo, hi = bounds[name]
            if np.any((theta[:, :, j] < lo) | (theta[:, :, j] > hi)):
                raise ValueError(f"posterior support failure: {name}")
    radii = components[:, :, 4]
    if not np.isfinite(radii).all() or np.any(radii >= 1):
        raise ValueError("posterior artifact contains unstable draw")
    return arrays, metadata
