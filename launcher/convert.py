"""Run the existing tools/convert_data.py against the ripped Exports (no edits to that script)."""
import contextlib
import importlib.util
import io
import os
import shutil
import sys

from .errors import LauncherError

REQUIRED_OUTPUT = ("handlers.json", "script_ids.json", "members_main.json")


def convert(paths, log):
    script = paths.convert_script
    if not script.exists():
        raise LauncherError("tools/convert_data.py is missing.", detail=str(script))

    shutil.rmtree(paths.data_partial, ignore_errors=True)
    spec = importlib.util.spec_from_file_location("ispy_convert_data", script)
    mod = importlib.util.module_from_spec(spec)

    buf = io.StringIO()
    old_argv = sys.argv
    sys.argv = [str(script), "--exports", str(paths.exports), "--out", str(paths.data_partial)]
    try:
        with contextlib.redirect_stdout(buf):
            spec.loader.exec_module(mod)       # convert_data adds its own folder to sys.path for lingo_data
            mod.main()
    except SystemExit as e:
        if e.code not in (0, None):
            raise LauncherError("convert_data.py exited with an error.", detail=buf.getvalue())
    except Exception as e:
        raise LauncherError("Converting the game data failed.", detail=buf.getvalue() + "\n" + repr(e),
                            hint="This usually means the ripped scripts aren't what the converter expects.")
    finally:
        sys.argv = old_argv

    out = buf.getvalue()
    for line in out.splitlines():
        log(line)
    missing = [f for f in REQUIRED_OUTPUT if not (paths.data_partial / f).exists()]
    if missing:
        raise LauncherError("Conversion didn't produce: " + ", ".join(missing), detail=out)

    old = paths.data.with_name("data.old")
    shutil.rmtree(old, ignore_errors=True)
    if paths.data.exists():
        os.replace(paths.data, old)
    os.replace(paths.data_partial, paths.data)
    shutil.rmtree(old, ignore_errors=True)
    return [l for l in out.splitlines() if l.startswith("FAILED")]
