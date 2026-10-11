"""Version stamp / per-stage signatures.

Each stage records a signature of everything it depends on. A stage is skipped when its recorded
signature equals the current one, so later launches do no work, and changing (say) convert_data.py
re-runs only the convert stage.
"""
import hashlib
import json
import os

from .config import STAMP_VERSION


def load(paths):
    try:
        with open(paths.state_file, "r", encoding="utf-8") as f:
            st = json.load(f)
        if isinstance(st, dict):
            return st
    except (OSError, ValueError):
        pass
    return {}


def save(paths, st):
    paths.root.mkdir(parents=True, exist_ok=True)
    tmp = paths.state_file.with_name("state.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1, sort_keys=True)
    os.replace(tmp, paths.state_file)


def sig_of(*parts):
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


def file_hash(*files):
    h = hashlib.sha256()
    for f in files:
        try:
            with open(f, "rb") as fp:
                h.update(fp.read())
        except OSError:
            h.update(b"<missing>")
    return h.hexdigest()[:16]


def stage_sig(st, key):
    return (st.get("stages") or {}).get(key)


def mark(st, key, signature):
    st.setdefault("stages", {})[key] = signature


def clear_from(st, keys):
    for k in keys:
        (st.get("stages") or {}).pop(k, None)


def stamp_ok(st):
    return st.get("stamp_version") == STAMP_VERSION
