"""Tool setup. The extraction tools are now the pure-Python `dirtools` package that ships with the port, so
there is nothing to locate or download any more. The names below are kept so pipeline.py and __main__.py don't
need to know that.

Licensing note: dirtools/container.py and dirtools/lingo_*.py are ports of ProjectorRays (MPL-2.0); see
dirtools/LICENSE-MPL.txt. The bitmap/sound logic follows Director Cast Ripper's Lingo (MIT).
"""
import hashlib
from pathlib import Path

from .errors import LauncherError


def _dirtools_dir():
    import dirtools
    return Path(dirtools.__file__).resolve().parent


def tools_signature(paths=None):
    """Hash of the dirtools sources, so a changed decoder invalidates previously extracted exports."""
    try:
        h = hashlib.sha256()
        files = sorted(_dirtools_dir().glob("*.py"))
        for f in files:
            h.update(f.name.encode())
            h.update(f.read_bytes())
        if files:
            return "dirtools=" + h.hexdigest()[:16]
    except Exception:
        pass
    return "dirtools=bundled"            # frozen build: sources aren't on disk, STAMP_VERSION covers changes


def check_platform(paths=None):
    """Nothing is Windows-only any more."""
    return


def ensure_tools(paths, progress, cancel, local_ripper_dir=None):
    """Verify the bundled extraction package imports (there is nothing to download)."""
    try:
        import dirtools.ripper  # noqa: F401
    except Exception as e:
        raise LauncherError("The bundled extraction tools couldn't be loaded.", detail=repr(e))
    progress(1.0, "Tools ready")
