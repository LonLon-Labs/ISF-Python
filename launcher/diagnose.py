"""Find out why DirectorCastRipper.exe crashes when launched by the launcher.

    python -m launcher.diagnose            # casts: the original set of trials on SIGNIN.cxt
    python -m launcher.diagnose movie      # the MOVIE ISPYMAIN7.dxr (the current blocker), several variants
    python -m launcher.diagnose help       # just save `DirectorCastRipper.exe --help` to diag\\help.txt

Each trial changes one thing and prints the exit code (as hex), time, output file count and the last
console lines. Output goes to <app data>\\diag (safe to delete). Results are also appended to
diag\\results.txt so they can be pasted back.
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .config import Paths
from .ripper import NOWIN

ORIGINAL_DIR = Path(r"C:\Users\Wesley\Downloads\DirectorCastRipper_D10")
INSTALLED_DATA = ORIGINAL_DIR / "ispy_fantasy" / "DATA"

_results = []


def say(line=""):
    print(line)
    _results.append(line)


def hexcode(code):
    if isinstance(code, int):
        return "0x%X" % (code & 0xFFFFFFFF)
    return str(code)


def pick_input(paths):
    for base in (paths.work / "DATA" / "CASTS", INSTALLED_DATA / "CASTS"):
        for name in ("SIGNIN.cxt", "SIGNIN.CXT"):
            if (base / name).exists():
                return base / name
    base = paths.work / "DATA" / "CASTS"
    found = sorted(base.glob("*.cxt")) if base.exists() else []
    return found[0] if found else None


def trial(label, exe, cwd, args, out_dir, precreate, inp, kind="--casts", timeout=180, stdin_null=True,
          flags=NOWIN, capture=True):
    shutil.rmtree(out_dir, ignore_errors=True)
    if precreate:
        out_dir.mkdir(parents=True)
    cmd = [str(exe), "--cli"] + args + ["--output-folder", str(out_dir), kind, str(inp)]
    t0 = time.monotonic()
    try:
        kw = {"stdin": subprocess.DEVNULL} if stdin_null else {}
        if capture:
            p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, creationflags=flags, timeout=timeout, **kw)
            text = (p.stdout + p.stderr).decode("utf-8", "replace").strip()
        else:
            p = subprocess.run(cmd, cwd=str(cwd), creationflags=flags, timeout=timeout, **kw)
            text = ""
        code = p.returncode
    except subprocess.TimeoutExpired:
        code, text = "TIMEOUT", ""
    files = [f for f in out_dir.rglob("*") if f.is_file()] if out_dir.exists() else []
    say("%-52s exit=%-12s %6.1fs  files=%d" % (label, hexcode(code), time.monotonic() - t0, len(files)))
    if text:
        say("    " + "\n    ".join(text.splitlines()[-6:]))
    return code, len(files)


def save_results(paths):
    d = paths.root / "diag"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "results.txt", "a", encoding="utf-8") as f:
        f.write("\n".join(_results) + "\n\n")
    print("\n(results also appended to %s)" % (d / "results.txt"))


def run_help(paths):
    d = paths.root / "diag"
    d.mkdir(parents=True, exist_ok=True)
    try:
        p = subprocess.run([str(paths.ripper_exe), "--cli", "--help"], cwd=str(paths.ripper_dir), capture_output=True,
                           creationflags=NOWIN, timeout=60)
        text = (p.stdout + p.stderr).decode("utf-8", "replace")
        say("--help exit=%s" % hexcode(p.returncode))
    except subprocess.TimeoutExpired:
        text = "(timed out)"
    (d / "help.txt").write_text(text, encoding="utf-8")
    say("saved --help output (%d chars) to %s" % (len(text), d / "help.txt"))


def casts(paths):
    inp = pick_input(paths)
    if inp is None:
        say("Couldn't find SIGNIN.cxt or any other cast to test with.")
        return 1
    say("test input: %s" % inp)
    d = paths.root / "diag"
    app_exe = paths.ripper_exe
    orig_exe = ORIGINAL_DIR / "DirectorCastRipper.exe"

    trial("A app copy, no decompile", app_exe, paths.ripper_dir, ["--dismiss-dialogs"], d / "A", True, inp)
    trial("B app copy, no decompile, outdir not created", app_exe, paths.ripper_dir, ["--dismiss-dialogs"], d / "B", False, inp)
    trial("C app copy, WITH decompile", app_exe, paths.ripper_dir, ["--dismiss-dialogs", "--decompile"], d / "C", True, inp)
    trial("D app copy, no --dismiss-dialogs", app_exe, paths.ripper_dir, [], d / "D", True, inp)
    trial("E app copy, outdir named exports.partial", app_exe, paths.ripper_dir, ["--dismiss-dialogs"], d / "exports.partial", True, inp)
    if orig_exe.exists():
        trial("F ORIGINAL folder, no decompile", orig_exe, ORIGINAL_DIR, ["--dismiss-dialogs"], d / "F", True, inp)
        trial("G ORIGINAL folder, WITH decompile", orig_exe, ORIGINAL_DIR, ["--dismiss-dialogs", "--decompile"], d / "G", True, inp)
    return 0


def movie(paths):
    """Run the movie ISPYMAIN7.dxr several ways. Movies can take minutes, so each trial has a 10 minute cap."""
    d = paths.root / "diag"
    app_exe, app_dir = paths.ripper_exe, paths.ripper_dir
    orig_exe = ORIGINAL_DIR / "DirectorCastRipper.exe"
    work_dxr = paths.work / "DATA" / "ISPYMAIN7.dxr"
    inst_dxr = INSTALLED_DATA / "ISPYMAIN7.dxr"
    inst_dir = INSTALLED_DATA / "ISPYMAIN7.dir"
    dismiss = ["--dismiss-dialogs"]
    T = 600
    say("work copy      : %s (%s)" % (work_dxr, "exists" if work_dxr.exists() else "MISSING"))
    say("installed .dxr : %s (%s)" % (inst_dxr, "exists" if inst_dxr.exists() else "MISSING"))
    say("installed .dir : %s (%s)" % (inst_dir, "exists" if inst_dir.exists() else "MISSING"))
    say("")

    def mv(label, exe, cwd, args, name, inp):
        if not Path(inp).exists():
            say("%-52s skipped (input missing)" % label)
            return None
        return trial(label, exe, cwd, args, d / name, True, inp, kind="--movies", timeout=T)

    # 1. Baseline: what the launcher does.
    mv("M1 baseline: work copy, app copy of ripper", app_exe, app_dir, dismiss, "M1", work_dxr)
    # 2. The complete installed game, ripped in place (EXTERNAL.cxt, CASTS, Xtras all in their original spots).
    mv("M2 installed game .dxr, in place", app_exe, app_dir, dismiss, "M2", inst_dxr)
    # 3. Same, but working directory = the movie's own folder (Director resolves relative links against it).
    mv("M3 installed game .dxr, cwd = DATA folder", app_exe, INSTALLED_DATA, dismiss, "M3", inst_dxr)
    # 4. Without the auto-dismisser (maybe it is the dismisser that crashes on a dialog).
    mv("M4 installed game .dxr, no --dismiss-dialogs", app_exe, app_dir, [], "M4", inst_dxr)
    # 5. The unprotected source movie that ships in the installed game.
    mv("M5 installed game .dir (unprotected)", app_exe, app_dir, dismiss, "M5", inst_dir)
    # 6. Narrow the export; member type names are unverified, see diag\help.txt.
    mv("M6 installed .dxr, --member-types sound", app_exe, app_dir, dismiss + ["--member-types", "sound"], "M6", inst_dxr)
    mv("M7 installed .dxr, --member-types image", app_exe, app_dir, dismiss + ["--member-types", "image"], "M7", inst_dxr)
    # 8. The user's original Cast Ripper folder (what produced the first exports).
    if orig_exe.exists():
        mv("M8 ORIGINAL ripper folder, installed .dxr", orig_exe, ORIGINAL_DIR, dismiss, "M8", inst_dxr)
    return 0


def formats(paths):
    """The movie with explicit --formats / --member-types. Hypothesis: the crash happens when a member type is
    selected whose file format (wav for sounds, txt for fields) isn't in --formats (default is only png html)."""
    d = paths.root / "diag"
    exe, cwd = paths.ripper_exe, paths.ripper_dir
    inp = INSTALLED_DATA / "ISPYMAIN7.dxr"
    base = ["--dismiss-dialogs"]
    T = 900

    def mv(label, args, name):
        return trial(label, exe, cwd, base + args, d / name, True, inp, kind="--movies", timeout=T)

    mv("N1 --formats png wav html txt (all types)", ["--formats", "png", "wav", "html", "txt"], "N1")
    mv("N2 --member-types sound --formats wav", ["--member-types", "sound", "--formats", "wav"], "N2")
    mv("N3 --member-types field --formats txt", ["--member-types", "field", "--formats", "txt"], "N3")
    mv("N4 --member-types text --formats html", ["--member-types", "text", "--formats", "html"], "N4")
    mv("N5 --member-types image --formats png", ["--member-types", "image", "--formats", "png"], "N5")
    return 0


def probe(paths):
    """Is the crash deterministic, and does it depend on how we launch the process (pipes / no console window)?
    Each ripper run is repeated, since M7 succeeded once and N5 (nearly identical) crashed."""
    d = paths.root / "diag"
    exe, cwd = paths.ripper_exe, paths.ripper_dir
    inp = INSTALLED_DATA / "ISPYMAIN7.dxr"
    dismiss = ["--dismiss-dialogs"]
    T = 900
    n = [0]

    def mv(label, args, **kw):
        n[0] += 1
        return trial("P%d %s" % (n[0], label), exe, cwd, dismiss + args, d / ("P%d" % n[0]), True, inp,
                     kind="--movies", timeout=T, **kw)

    for i in (1, 2, 3):
        mv("image only, default formats (run %d of 3)" % i, ["--member-types", "image"])
    mv("image, --formats png html", ["--member-types", "image", "--formats", "png", "html"])
    mv("image, --formats png", ["--member-types", "image", "--formats", "png"])
    mv("sound, default formats", ["--member-types", "sound"])
    mv("text, default formats", ["--member-types", "text"])
    mv("all types, --formats png html", ["--formats", "png", "html"])
    mv("image, stdin=NUL", ["--member-types", "image"], stdin_null=True)
    mv("image, no CREATE_NO_WINDOW, output not captured", ["--member-types", "image"], flags=0, capture=False)
    mv("sound, stdin=NUL", ["--member-types", "sound"], stdin_null=True)
    mv("sound, no CREATE_NO_WINDOW, output not captured", ["--member-types", "sound"], flags=0, capture=False)
    mv("all types, no CREATE_NO_WINDOW, output not captured", [], flags=0, capture=False)
    return 0


def main():
    paths = Paths()
    mode = (sys.argv[1] if len(sys.argv) > 1 else "cast").lower()
    say("mode: %s   ripper: %s" % (mode, paths.ripper_exe))
    if mode == "help":
        run_help(paths)
    elif mode == "movie":
        run_help(paths)
        movie(paths)
    elif mode == "probe":
        probe(paths)
    elif mode == "formats":
        run_help(paths)
        formats(paths)
    else:
        casts(paths)
    say("\nOutput folders are in %s (safe to delete)." % (paths.root / "diag"))
    save_results(paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
