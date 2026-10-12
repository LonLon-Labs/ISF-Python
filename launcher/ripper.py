"""Extract the game's assets and Lingo scripts from the copied disc files into the Exports folder.

This used to run DirectorCastRipper.exe and ProjectorRays.exe. It now calls the pure-Python `dirtools` package,
so it works the same on Windows, macOS and Linux (x86_64 and ARM) with nothing to download.

Output layout (what tools/convert_data.py and the game read):
    <exports>/<fileBaseName>/Members.csv, Casts.csv, <num>.png/.wav/.txt     (ISPYMAIN7, BHP, B, B_AC, D, S, ...)
    <exports>/BHP/casts/External/*.ls
"""
import os
import shutil
import subprocess
from pathlib import Path

import dirtools.ripper as dt

from .errors import Cancelled, LauncherError

# Kept only because launcher/diagnose.py (a legacy Windows-only tool for the old .exe) imports it.
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# What the port reads; used to decide whether ripping really worked.
REQUIRED_EXPORTS = [
    "ISPYMAIN7/Members.csv",
    "BHP/Members.csv",
]
REQUIRED_SCRIPT_DIR = "BHP/casts/External"      # MovieScript*.ls

# name -> required. Mirrors dirtools.ripper.SCRIPT_TARGETS.
RAYS_TARGETS = dt.SCRIPT_TARGETS


def cli_hash():
    """Kept for the state signature; the ripper has no command line any more."""
    return "dirtools"


def verify_exports(root):
    root = Path(root)
    missing = [r for r in REQUIRED_EXPORTS if not (root / r).exists()]
    scripts = root / REQUIRED_SCRIPT_DIR
    if not scripts.is_dir() or not any(scripts.glob("MovieScript*.ls")):
        missing.append(REQUIRED_SCRIPT_DIR + "/MovieScript*.ls")
    return missing


def rip_all(paths, progress, cancel, log):
    data_dir = paths.work / "DATA"
    if not data_dir.is_dir():
        raise LauncherError("Nothing to rip: the extracted disc files are missing.", detail=str(data_dir))

    shutil.rmtree(paths.exports_partial, ignore_errors=True)
    paths.exports_partial.mkdir(parents=True)

    try:
        totals = dt.rip_all(str(data_dir), str(paths.exports_partial), progress=lambda f, m: progress(min(f, 0.99), m),
                            cancel=cancel, log=log)
    except dt.RipCancelled:
        raise Cancelled()
    except dt.RipError as e:
        raise LauncherError(e.message, detail=e.detail)
    log("Extracted: " + ", ".join("%d %s" % (v, k) for k, v in sorted(totals.items()) if v))

    missing = verify_exports(paths.exports_partial)
    if missing:
        raise LauncherError("Extraction finished but expected output is missing.", detail="\n".join(missing))

    old = paths.exports.with_name("exports.old")
    shutil.rmtree(old, ignore_errors=True)
    if paths.exports.exists():
        os.replace(paths.exports, old)
    os.replace(paths.exports_partial, paths.exports)
    shutil.rmtree(old, ignore_errors=True)
    progress(1.0, "Extraction complete")
