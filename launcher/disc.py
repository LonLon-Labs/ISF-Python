"""Read the user's own disc: an .iso image, or an already-mounted / extracted folder (e.g. D:\\).

Both backends expose the same tiny interface so validation and extraction don't care which is used.
Paths are written 'DATA/CASTS/BHP.cxt'; lookups are case-insensitive and ignore ISO9660 ';1' suffixes.
"""
import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from .errors import Cancelled, LauncherError

CHUNK = 1024 * 1024


@dataclass
class Entry:
    name: str          # display name (version suffix stripped)
    is_dir: bool
    size: int
    raw_path: str      # path as stored on the medium, '/'-separated, no leading slash


def _strip_version(name):
    base, sep, ver = name.rpartition(";")
    return base if sep and ver.isdigit() else name


class Source:
    label = ""

    def listdir(self, raw_path):
        raise NotImplementedError

    def copy(self, entry, dest, on_bytes, cancel):
        raise NotImplementedError

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def find(self, path):
        """Case-insensitive lookup of 'A/B/c.ext'; returns Entry or None."""
        parts = [p for p in path.replace("\\", "/").split("/") if p]
        cur, found = "", None
        for i, part in enumerate(parts):
            found = None
            for e in self.listdir(cur):
                if e.name.lower() == part.lower():
                    found = e
                    break
            if found is None:
                return None
            if i < len(parts) - 1 and not found.is_dir:
                return None
            cur = found.raw_path
        return found

    def list_files(self, dir_path):
        d = self.find(dir_path)
        if d is None or not d.is_dir:
            return []
        return [e for e in self.listdir(d.raw_path) if not e.is_dir]


class FolderSource(Source):
    def __init__(self, root):
        self.root = Path(root)
        self.label = str(self.root)

    def listdir(self, raw_path):
        base = self.root / raw_path if raw_path else self.root
        out = []
        try:
            with os.scandir(base) as it:
                for de in it:
                    is_dir = de.is_dir()
                    size = 0 if is_dir else de.stat().st_size
                    out.append(Entry(de.name, is_dir, size, (raw_path + "/" if raw_path else "") + de.name))
        except OSError:
            pass
        return out

    def copy(self, entry, dest, on_bytes, cancel):
        with open(self.root / entry.raw_path, "rb") as src, open(dest, "wb") as dst:
            while True:
                if cancel.is_set():
                    raise Cancelled()
                buf = src.read(CHUNK)
                if not buf:
                    break
                dst.write(buf)
                on_bytes(len(buf))


class _Sink:
    """File-like object handed to pycdlib so we get byte counts and can cancel mid-file."""

    def __init__(self, fp, on_bytes, cancel):
        self.fp, self.on_bytes, self.cancel = fp, on_bytes, cancel

    def write(self, data):
        if self.cancel.is_set():
            raise Cancelled()
        self.fp.write(data)
        self.on_bytes(len(data))
        return len(data)

    def flush(self):
        self.fp.flush()


class IsoSource(Source):
    def __init__(self, path):
        try:
            import pycdlib
        except ImportError:
            raise LauncherError("Missing dependency: pycdlib",
                                hint="Install it with:  pip install pycdlib")
        self.label = str(path)
        self.iso = pycdlib.PyCdlib()
        try:
            self.iso.open(str(path))
        except Exception as e:
            raise LauncherError(
                "That file couldn't be read as a disc image.",
                detail=repr(e),
                hint="Choose a standard .iso file. For BIN/CUE or MDF images, convert them to ISO first, "
                     "or mount the image and choose the mounted drive instead.")
        self.joliet = bool(self.iso.has_joliet())

    def _kw(self, path):
        return {"joliet_path" if self.joliet else "iso_path": path}

    def listdir(self, raw_path):
        out = []
        iso_path = "/" + raw_path if raw_path else "/"
        for rec in self.iso.list_children(**self._kw(iso_path)):
            if rec.is_dot() or rec.is_dotdot():
                continue
            ident = rec.file_identifier()
            raw = ident.decode("utf-16-be" if self.joliet else "latin-1")
            is_dir = rec.is_dir()
            out.append(Entry(_strip_version(raw), is_dir, 0 if is_dir else rec.get_data_length(),
                             (raw_path + "/" if raw_path else "") + raw))
        return out

    def copy(self, entry, dest, on_bytes, cancel):
        with open(dest, "wb") as fp:
            self.iso.get_file_from_iso_fp(_Sink(fp, on_bytes, cancel), **self._kw("/" + entry.raw_path))

    def close(self):
        try:
            self.iso.close()
        except Exception:
            pass


def open_source(path):
    p = Path(path)
    if p.is_dir():
        return FolderSource(p)
    if p.is_file():
        return IsoSource(p)
    raise LauncherError("Couldn't find that disc image or folder.", detail=str(path))


# --------------------------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------------------------

@dataclass
class DiscReport:
    main_dxr: Optional[Entry] = None
    casts: List[Entry] = field(default_factory=list)
    aiff: List[Entry] = field(default_factory=list)
    bink: List[Entry] = field(default_factory=list)
    icon: Optional[Entry] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    fingerprint: str = ""

    @property
    def ok(self):
        return not self.errors

    @property
    def total_bytes(self):
        items = ([self.main_dxr] if self.main_dxr else []) + self.casts + self.aiff + self.bink
        return sum(e.size for e in items)

    def summary(self):
        return "%d casts, %d AIFF voice-overs, %d Bink videos" % (len(self.casts), len(self.aiff), len(self.bink))


MIN_CASTS_WARN = 25      # a full disc has 27 .cxt casts (BHP, EXTERNAL, SIGNIN and the B / D / S sets)
MAIN_MOVIE = "ISPYMAIN7.dxr"    # the main game movie; it sits in DATA/ (and is copied to the disc root too)


def collect(source):
    """Inspect the disc and report what's there. Never raises for 'wrong disc'; look at report.errors."""
    r = DiscReport()
    if source.find("DATA") is None:
        r.errors.append("There is no DATA folder on this disc. This doesn't look like I SPY Fantasy "
                        "(or you picked the wrong drive/image).")
        return r

    r.main_dxr = source.find("DATA/" + MAIN_MOVIE) or source.find(MAIN_MOVIE)
    if r.main_dxr is None:
        r.errors.append("DATA/%s is missing (the main game movie)." % MAIN_MOVIE)

    r.casts = [e for e in source.list_files("DATA/CASTS") if e.name.lower().endswith(".cxt")]
    if not any(e.name.lower() == "bhp.cxt" for e in r.casts):
        r.errors.append("DATA/CASTS/BHP.cxt is missing (the code cast the port is translated from).")
    elif len(r.casts) < MIN_CASTS_WARN:
        r.warnings.append("Only %d casts found in DATA/CASTS (expected about 27); some areas may be missing." % len(r.casts))

    r.aiff = source.list_files("DATA/AIFF")
    if not r.aiff:
        r.errors.append("DATA/AIFF is missing or empty (voice-overs).")

    r.bink = [e for e in source.list_files("DATA/BINK") if e.name.lower().endswith(".bik")]
    if not r.bink:
        r.warnings.append("No Bink videos found in DATA/BINK; the game will skip its video clips.")

    r.icon = source.find("Fantasy.ico")

    h = hashlib.sha256()
    items = ([r.main_dxr] if r.main_dxr else []) + sorted(r.casts, key=lambda e: e.name.lower())
    for e in items:
        h.update(("%s:%d\n" % (e.name.lower(), e.size)).encode())
    r.fingerprint = h.hexdigest()[:16]
    return r


# --------------------------------------------------------------------------------------------
# extraction
# --------------------------------------------------------------------------------------------

def extract(source, report, work_dir, game_dir, progress: Callable[[float, str], None], cancel):
    """Copy what the port needs out of the disc.

    work_dir/DATA/ISPYMAIN8.dxr, work_dir/DATA/CASTS/*.cxt   -> input for the ripper (deleted afterwards)
    game_dir/DATA/AIFF/*, game_dir/DATA/BINK/*.bik           -> read by the runtime directly
    Files already present with the right size are skipped, so an interrupted run resumes.
    """
    jobs = []
    if report.main_dxr:
        jobs.append((report.main_dxr, Path(work_dir) / "DATA" / report.main_dxr.name))
    for e in report.casts:
        jobs.append((e, Path(work_dir) / "DATA" / "CASTS" / e.name))
    for e in report.aiff:
        jobs.append((e, Path(game_dir) / "DATA" / "AIFF" / e.name))
    for e in report.bink:
        jobs.append((e, Path(game_dir) / "DATA" / "BINK" / e.name))
    if report.icon:
        jobs.append((report.icon, Path(game_dir) / report.icon.name))

    total = max(1, sum(e.size for e, _ in jobs))
    done = [0]

    def on_bytes(n):
        done[0] += n

    for i, (entry, dest) in enumerate(jobs):
        if cancel.is_set():
            raise Cancelled()
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.stat().st_size == entry.size:
            done[0] += entry.size
        else:
            part = dest.with_name(dest.name + ".part")
            try:
                source.copy(entry, part, on_bytes, cancel)
                os.replace(part, dest)
            except Cancelled:
                raise
            except OSError as e:
                raise LauncherError("Couldn't write %s" % dest.name, detail=str(e),
                                    hint="Check that there is enough free disk space and that the folder is writable.")
            finally:
                if part.exists():
                    try:
                        part.unlink()
                    except OSError:
                        pass
        progress(min(1.0, done[0] / total), "Copying %s (%d of %d)" % (entry.name, i + 1, len(jobs)))
