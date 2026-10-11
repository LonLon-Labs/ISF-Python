"""Entry point.

    python -m launcher                       # play (runs first-time setup in a window if needed)
    python -m launcher --setup               # force the setup window even if already set up
    python -m launcher --iso D:\\spooky.iso   # headless setup (console progress), then play
    python -m launcher --iso X --no-launch   # headless setup only
    python -m launcher --paths               # show where generated files live

Run from the ispy_port folder.
"""
import argparse
import sys
import threading

from . import pipeline
from .config import Paths
from .errors import Cancelled, LauncherError, NeedDisc


def _console_setup(paths, iso, ripper_dir):
    last = [-1]

    def emit(frac, stage, msg):
        pct = int(frac * 100)
        if pct != last[0] or msg:
            last[0] = pct
            print("[%3d%%] %s %s" % (pct, stage, msg))

    try:
        pipeline.run_setup(paths, iso, pipeline.Reporter(emit), threading.Event(), ripper_dir=ripper_dir, log=print)
        return True
    except NeedDisc:
        print("A disc image is required: pass --iso <path>.")
    except Cancelled:
        print("Cancelled.")
    except LauncherError as e:
        print("\nERROR: " + e.full_text())
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(prog="launcher")
    ap.add_argument("--setup", action="store_true")
    ap.add_argument("--iso")
    ap.add_argument("--ripper-dir", help=argparse.SUPPRESS)      # obsolete, ignored
    ap.add_argument("--paths", action="store_true")
    ap.add_argument("--no-launch", action="store_true")
    a = ap.parse_args(argv)

    paths = Paths()

    if a.paths:
        for name in ("root", "tools", "game", "exports", "data", "logs", "state_file"):
            print("%-10s %s" % (name, getattr(paths, name)))
        return 0

    if a.iso:
        ok = _console_setup(paths, a.iso, a.ripper_dir)
    elif a.setup or not pipeline.is_ready(paths):
        from .ui import SetupWindow
        ok = SetupWindow(paths, need_disc=pipeline.needs_disc(paths), ripper_dir=a.ripper_dir).run()
    else:
        ok = True

    if not ok or a.no_launch:
        return 0 if ok else 1

    from .launch import launch_game
    return launch_game(paths)


if __name__ == "__main__":
    sys.exit(main())
