"""First-run window (tkinter): pick the disc, watch progress, see clear errors."""
import queue
import threading
import tkinter as tk
from tkinter import filedialog, ttk

from . import pipeline
from .errors import Cancelled, LauncherError, NeedDisc


class SetupWindow:
    def __init__(self, paths, need_disc, ripper_dir=None, initial_disc=None):
        self.paths = paths
        self.ripper_dir = ripper_dir
        self.q = queue.Queue()
        self.cancel = threading.Event()
        self.worker = None
        self.result = False                     # True -> caller should launch the game
        self.log_lines = []
        self.last_error = None

        self.root = tk.Tk()
        self.root.title("I SPY Spooky Mansion Deluxe - First-time setup")
        self.root.geometry("640x520")
        self.root.minsize(560, 460)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        pad = {"padx": 12, "pady": 4}
        ttk.Label(self.root, text="First-time setup", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=12, pady=(12, 0))
        self.intro = ttk.Label(
            self.root, wraplength=600, justify="left",
            text="This port doesn't include any game files. Choose your own I SPY Spooky Mansion Deluxe disc "
                 "image (.iso) or the disc's drive, and the launcher will extract and convert what it needs. "
                 "This only happens once.")
        self.intro.pack(anchor="w", **pad)

        row = ttk.Frame(self.root)
        row.pack(fill="x", **pad)
        self.disc_var = tk.StringVar(value=initial_disc or "")
        self.entry = ttk.Entry(row, textvariable=self.disc_var)
        self.entry.pack(side="left", fill="x", expand=True)
        self.b_iso = ttk.Button(row, text="Choose ISO...", command=self._pick_iso)
        self.b_iso.pack(side="left", padx=(6, 0))
        self.b_dir = ttk.Button(row, text="Choose drive/folder...", command=self._pick_dir)
        self.b_dir.pack(side="left", padx=(6, 0))

        self.stage_var = tk.StringVar(value="")
        self.msg_var = tk.StringVar(value="")
        ttk.Label(self.root, textvariable=self.stage_var, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 0))
        self.bar = ttk.Progressbar(self.root, maximum=1000)
        self.bar.pack(fill="x", padx=12, pady=2)
        ttk.Label(self.root, textvariable=self.msg_var, foreground="#555").pack(anchor="w", padx=12)

        self.err_var = tk.StringVar(value="")
        self.err_label = ttk.Label(self.root, textvariable=self.err_var, wraplength=600, justify="left", foreground="#b00020")
        self.err_label.pack(anchor="w", padx=12, pady=(6, 0))

        frame = ttk.Frame(self.root)
        frame.pack(fill="both", expand=True, padx=12, pady=6)
        self.text = tk.Text(frame, height=8, state="disabled", wrap="word", font=("Consolas", 9))
        sb = ttk.Scrollbar(frame, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        self.text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        btns = ttk.Frame(self.root)
        btns.pack(fill="x", padx=12, pady=(0, 12))
        self.b_start = ttk.Button(btns, text="Start", command=self._start)
        self.b_start.pack(side="right")
        self.b_cancel = ttk.Button(btns, text="Cancel", command=self._on_cancel, state="disabled")
        self.b_cancel.pack(side="right", padx=6)
        self.b_copy = ttk.Button(btns, text="Copy error details", command=self._copy_error)
        self.b_copy.pack(side="left")
        self.b_copy.state(["disabled"])

        self.root.after(100, self._poll)
        if not need_disc:
            self.intro.config(text="Updating generated game data from your earlier setup. No disc is needed.")
            for w in (self.entry, self.b_iso, self.b_dir):
                w.state(["disabled"])
            self.root.after(300, self._start)

    # ---- actions ----
    def _pick_iso(self):
        p = filedialog.askopenfilename(title="Choose your disc image",
                                       filetypes=[("Disc images", "*.iso"), ("All files", "*.*")])
        if p:
            self.disc_var.set(p)

    def _pick_dir(self):
        p = filedialog.askdirectory(title="Choose the disc drive or an extracted copy of the disc")
        if p:
            self.disc_var.set(p)

    def _set_busy(self, busy):
        st = ["disabled"] if busy else ["!disabled"]
        for w in (self.b_start, self.b_iso, self.b_dir):
            w.state(st)
        self.b_cancel.state(["!disabled"] if busy else ["disabled"])

    def _start(self):
        if self.worker and self.worker.is_alive():
            return
        disc_path = self.disc_var.get().strip().strip('"') or None
        if disc_path is None and pipeline.needs_disc(self.paths):
            self.err_var.set("Please choose your disc image or drive first.")
            return
        self.err_var.set("")
        self.last_error = None
        self.b_copy.state(["disabled"])
        self.cancel.clear()
        self._set_busy(True)
        rep = pipeline.Reporter(lambda f, s, m: self.q.put(("progress", f, s, m)))
        self.worker = threading.Thread(target=self._work, args=(disc_path, rep), daemon=True)
        self.worker.start()

    def _work(self, disc_path, rep):
        try:
            pipeline.run_setup(self.paths, disc_path, rep, self.cancel, ripper_dir=self.ripper_dir,
                               log=lambda s: self.q.put(("log", s)))
            self.q.put(("done",))
        except Cancelled:
            self.q.put(("cancelled",))
        except NeedDisc:
            self.q.put(("error", LauncherError("Please choose your disc image or drive first.")))
        except LauncherError as e:
            self.q.put(("error", e))
        except Exception as e:                               # never leave the user with a silent crash
            import traceback
            self.q.put(("error", LauncherError("Something unexpected went wrong.", detail=traceback.format_exc())))

    def _on_cancel(self):
        self.cancel.set()
        self.msg_var.set("Cancelling...")

    def _on_close(self):
        if self.worker and self.worker.is_alive():
            self.cancel.set()
        self.root.destroy()

    def _copy_error(self):
        if self.last_error:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.last_error.full_text() + "\n\nLog:\n" + "\n".join(self.log_lines[-200:]))

    # ---- event pump ----
    def _log(self, s):
        self.log_lines.append(s)
        self.text.config(state="normal")
        self.text.insert("end", s + "\n")
        self.text.see("end")
        self.text.config(state="disabled")

    def _poll(self):
        try:
            while True:
                ev = self.q.get_nowait()
                kind = ev[0]
                if kind == "progress":
                    _, frac, stage, msg = ev
                    self.bar["value"] = int(frac * 1000)
                    self.stage_var.set(stage)
                    self.msg_var.set(msg)
                elif kind == "log":
                    self._log(ev[1])
                elif kind == "done":
                    self.bar["value"] = 1000
                    self.stage_var.set("Ready to play")
                    self.result = True
                    self.root.after(600, self.root.destroy)
                elif kind == "cancelled":
                    self.msg_var.set("Cancelled. Progress so far is kept; press Start to resume.")
                    self._set_busy(False)
                elif kind == "error":
                    err = ev[1]
                    self.last_error = err
                    self.err_var.set(err.title + ("\n" + err.hint if err.hint else ""))
                    if err.detail:
                        self._log(err.detail)
                    self.msg_var.set("")
                    self.b_copy.state(["!disabled"])
                    self._set_busy(False)
                    for w in (self.entry, self.b_iso, self.b_dir):
                        w.state(["!disabled"])
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def run(self):
        self.root.mainloop()
        return self.result
