"""PyInstaller entry point for the launcher.

Why a stub instead of `launcher/__main__.py`: PyInstaller runs its script as a top-level file, which breaks the
package's relative imports. This imports `launcher.__main__` the normal way.

It also:
  * puts the bundled ffmpeg (<bundle>/ffmpeg) on PATH so ispy/video.py finds it with shutil.which('ffmpeg');
  * sends stdout/stderr to <app data>/logs/launcher.log when the app is windowed (no console => they are None);
  * shows unexpected crashes in a message box instead of vanishing;
  * implements `--selftest`, used by packaging/build.py to prove the frozen app contains everything it needs.
"""
import os
import sys
import traceback


def _prepare_environment():
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        ff = os.path.join(bundle, "ffmpeg")
        if os.path.isdir(ff):
            os.environ["PATH"] = ff + os.pathsep + os.environ.get("PATH", "")
    sys.argv[:] = [a for a in sys.argv if not a.startswith("-psn_")]     # old macOS Finder launches add this


def _open_log():
    try:
        from launcher.config import Paths
        p = Paths()
        p.logs.mkdir(parents=True, exist_ok=True)
        return open(p.logs / "launcher.log", "a", encoding="utf-8", buffering=1)
    except Exception:
        return None


def _redirect_if_headless():
    if sys.stdout is None or sys.stderr is None:
        log = _open_log()
        if log is not None:
            if sys.stdout is None:
                sys.stdout = log
            if sys.stderr is None:
                sys.stderr = log


def _show_fatal(text):
    try:
        import tkinter
        from tkinter import messagebox
        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("I SPY launcher", "Something went wrong and the launcher has to close.\n\n" + text[-1500:])
        root.destroy()
    except Exception:
        pass


def _selftest():
    """Import everything the app needs. Exit code 0 = fine. Output also goes to the log file."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    problems = []

    def check(label, fn):
        try:
            detail = fn()
            print("ok    %-22s %s" % (label, detail or ""))
        except BaseException as e:                                  # noqa: BLE001
            problems.append(label)
            print("FAIL  %-22s %r" % (label, e))

    def _tk():
        import tkinter
        return "Tk %s" % tkinter.TkVersion

    def _pygame():
        import pygame
        pygame.font.init()
        pygame.font.Font(None, 12)                                  # the default font is a bundled data file
        return "pygame %s" % pygame.version.ver

    def _pycdlib():
        import pycdlib
        return "pycdlib %s" % getattr(pycdlib, "__version__", "")

    def _game_modules():
        from ispy import runtime, movie                             # noqa: F401
        from ispy import core, ui, game, screens, screens2, riddles, rooms, video, hunts  # noqa: F401
        from ispy import media, lingo, version_picker               # noqa: F401
        return "ispy modules import"

    def _launcher_modules():
        from launcher import config, disc, tools, ripper, convert, state, pipeline, ui, launch  # noqa: F401
        import dirtools.ripper  # noqa: F401
        return "launcher modules import"

    def _convert_scripts():
        import importlib.util
        from launcher.config import Paths
        p = Paths()
        for f in (p.convert_script, p.lingo_script):
            if not f.is_file():
                raise FileNotFoundError(str(f))
        spec = importlib.util.spec_from_file_location("selftest_convert", p.convert_script)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return "tools/convert_data.py loads"

    def _ffmpeg():
        import shutil
        exe = shutil.which("ffmpeg")
        if not exe and os.environ.get("ISPY_SELFTEST_FFMPEG") == "1":
            raise RuntimeError("ffmpeg should be bundled but wasn't found on PATH")
        return exe or "not bundled (videos fall back to stills)"

    check("tkinter", _tk)
    check("pygame", _pygame)
    check("pycdlib", _pycdlib)
    check("launcher modules", _launcher_modules)
    check("game modules", _game_modules)
    check("convert scripts", _convert_scripts)
    check("ffmpeg", _ffmpeg)
    print("SELFTEST " + ("FAILED: " + ", ".join(problems) if problems else "PASSED"))
    return 1 if problems else 0


def main():
    _prepare_environment()
    _redirect_if_headless()
    if "--selftest" in sys.argv:
        return _selftest()
    try:
        from launcher.__main__ import main as launcher_main
        return launcher_main()
    except SystemExit:
        raise
    except BaseException:                                           # noqa: BLE001
        text = traceback.format_exc()
        try:
            print(text, file=sys.stderr)
        except Exception:
            pass
        _show_fatal(text)
        return 1


if __name__ == "__main__":
    sys.exit(main())
