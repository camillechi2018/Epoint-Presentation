"""Shared JSON output and read-only raw-byte manifest verification."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

def write_json(path, data):
    Path(path).write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def safe_file(root, relative):
    return _file_under_root(Path(root).resolve(), relative)


def _file_under_root(root, relative):
    rel = PurePosixPath(relative)
    if not relative or '\\' in relative or ':' in relative or rel.is_absolute() or '..' in rel.parts:
        raise ValueError('manifest_invalid_path: ' + relative)
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('manifest_missing_or_unsafe_file: ' + relative)
    return path


def verify_manifest(root, manifest_name='knowledge-manifest.json', version=None):
    root = Path(root).resolve()
    manifest = json.loads(_file_under_root(root, manifest_name).read_text(encoding='utf-8'))
    if not isinstance(manifest, dict):
        raise ValueError('manifest_invalid_object')
    if version is not None and manifest.get('version') != version:
        raise ValueError('manifest_version_mismatch')
    files = manifest.get('files')
    if not isinstance(files, dict) or not files or 'catalog.json' not in files:
        raise ValueError('manifest_empty_or_missing_catalog')
    if manifest.get('file_count', len(files)) != len(files):
        raise ValueError('manifest_file_count_mismatch')
    for relative, expected in files.items():
        actual = hashlib.sha256(_file_under_root(root, relative).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError('manifest_hash_mismatch: ' + relative)
    return manifest
