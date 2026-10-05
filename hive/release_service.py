from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable


@dataclass(frozen=True)
class ReleaseBundle:
    version: str
    manifest_hash: str
    signature: str
    artifacts: tuple[str, ...]


def _hash_manifest(manifest: str) -> str:
    return sha256(manifest.encode("utf-8")).hexdigest()


def validate_release_bundle(bundle: ReleaseBundle, expected_manifest: str) -> tuple[bool, str]:
    if not bundle.version or not bundle.signature:
        return False, "missing version or signature"

    if not bundle.artifacts:
        return False, "missing artifacts"

    expected_hash = _hash_manifest(expected_manifest)
    if bundle.manifest_hash != expected_hash:
        return False, "manifest hash mismatch"

    if bundle.signature != f"sig:{expected_hash}":
        return False, "invalid signature"

    return True, "accepted"


def build_release_bundle(version: str, manifest: str, artifacts: Iterable[str]) -> ReleaseBundle:
    artifact_tuple = tuple(artifacts)
    manifest_hash = _hash_manifest(manifest)
    signature = f"sig:{manifest_hash}"
    return ReleaseBundle(version=version, manifest_hash=manifest_hash, signature=signature, artifacts=artifact_tuple)
