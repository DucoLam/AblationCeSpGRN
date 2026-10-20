"""
Terminal UI for your DAIC jobs, in the spirit of lazydocker. Refreshes every 20 seconds.

    python3 tools/lazyjobs.py

Keys: up/down or j/k move · enter opens the full log in less · r refreshes now
      a shows or hides finished jobs · c cancels the selected job (asks first) · q quits
"""
import curses
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import daic  # noqa: E402

POLL_SECONDS = 20
GROUPS = ["Running", "Waiting", "Failed", "Cancelled", "Completed"]
FINISHED = {"Completed", "Cancelled"}


def group_of(state):
    if state == "RUNNING":
        return "Running"
    if state == "PENDING":
        return "Waiting"
    if state == "COMPLETED":
        return "Completed"
    if state.startswith("CANCELLED"):
        return "Cancelled"
    return "Failed"


class App:
    def __init__(self):
        self.jobs = []
        self.updated = None
        self.error = None
        self.selected = None
        self.show_finished = True
        self.log_text = "Select a job to see its log."
        self.log_for = None
        self.status = ""
        self.lock = threading.Lock()
        self.refresh_event = threading.Event()
        self.log_event = threading.Event()

    # background work
    def poll_jobs(self):
        while True:
            try:
                jobs = daic.fetch_jobs()
                with self.lock:
                    self.jobs, self.error = jobs, None
                    self.updated = datetime.now().strftime("%H:%M:%S")
                self.log_event.set()  # refresh the visible log too
            except Exception as e:
                with self.lock:
                    self.error = str(e)
            self.refresh_event.wait(POLL_SECONDS)
            self.refresh_event.clear()

    def poll_log(self):
        while True:
            self.log_event.wait()
            self.log_event.clear()
            job_id = self.selected
            if not job_id:
                continue
            try:
                text = daic.job_log(job_id, lines=200)
            except Exception as e:
                text = f"Could not read the log: {e}"
            with self.lock:
                if self.selected == job_id:
                    self.log_text, self.log_for = text, job_id

    # data shown in the list: group headers and job rows
    def rows(self):
        with self.lock:
            jobs = list(self.jobs)
        by_group = {}
        for j in jobs:
            by_group.setdefault(group_of(j["state"]), []).append(j)
        rows = []
        for g in GROUPS:
            if g not in by_group or (g in FINISHED and not self.show_finished):
                continue
            rows.append(("header", f"{g} ({len(by_group[g])})", g))
            rows.extend(("job", j, g) for j in by_group[g])
        return rows

    def move(self, rows, step):
        ids = [r[1]["id"] for r in rows if r[0] == "job"]
        if not ids:
            return
        i = ids.index(self.selected) if self.selected in ids else -1
        new = ids[max(0, min(len(ids) - 1, i + step))] if i >= 0 else ids[0]
        if new != self.selected:
            self.selected = new
            with self.lock:
                self.log_text = "Loading log…"
            self.log_event.set()


def init_colors():
    curses.start_color()
    curses.use_default_colors()
    for i, color in enumerate([curses.COLOR_BLUE, curses.COLOR_YELLOW, curses.COLOR_RED,
                               curses.COLOR_WHITE, curses.COLOR_GREEN, curses.COLOR_CYAN], start=1):
        curses.init_pair(i, color, -1)
    return {"Running": 1, "Waiting": 2, "Failed": 3, "Cancelled": 4, "Completed": 5, "accent": 6}


def addstr(win, y, x, text, attr=0):
    h, w = win.getmaxyx()
    if 0 <= y < h and x < w:
        try:
            win.addnstr(y, x, text, max(0, w - x - 1), attr)
        except curses.error:
            pass


def draw(stdscr, app, colors):
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    rows = app.rows()
    if app.selected is None or app.selected not in [r[1]["id"] for r in rows if r[0] == "job"]:
        app.move(rows, 0)

    with app.lock:
        updated, error, log_text, status = app.updated, app.error, app.log_text, app.status
    head = f" DAIC jobs · updated {updated or '…'} · every {POLL_SECONDS}s"
    addstr(stdscr, 0, 0, head.ljust(w), curses.A_REVERSE | curses.A_BOLD)
    if error:
        addstr(stdscr, 0, len(head) + 2, f"refresh failed: {error}", curses.color_pair(colors["Failed"]) | curses.A_REVERSE)

    list_w = max(40, int(w * 0.55)) if w >= 100 else w
    body_h = h - 2
    # keep the selected row visible
    sel_index = next((i for i, r in enumerate(rows) if r[0] == "job" and r[1]["id"] == app.selected), 0)
    top = max(0, sel_index - body_h + 2)
    for line, row in enumerate(rows[top:top + body_h - 1]):
        y = line + 1
        kind, item, g = row
        if kind == "header":
            addstr(stdscr, y, 1, item.upper(), curses.color_pair(colors[g]) | curses.A_BOLD)
            continue
        j = item
        reason = ""
        if j["state"] == "PENDING":
            if j["reason"] == "Dependency" and j["depends"]:
                n = j["depends"].count("afterok:")
                reason = f"waits on {n} job{'s' if n != 1 else ''}"
            else:
                reason = j["reason"]
        elif j["exit"] and j["exit"] != "0:0" and g == "Failed":
            reason = f"exit {j['exit']}"
        text = f" {j['name'][:34]:<34} {j['id']:>9}  {j['elapsed']:>10}  {reason}"
        attr = curses.color_pair(colors[g])
        if j["id"] == app.selected:
            attr = curses.A_REVERSE | curses.color_pair(colors[g])
        addstr(stdscr, y, 1, text.ljust(list_w - 2)[: list_w - 2], attr)

    if w >= 100:
        x = list_w + 1
        for y in range(1, h - 1):
            addstr(stdscr, y, list_w, "│", curses.A_DIM)
        lines = log_text.splitlines()
        addstr(stdscr, 1, x, f"Log · job {app.selected or ''}", curses.color_pair(colors["accent"]) | curses.A_BOLD)
        for i, text in enumerate(lines[-(h - 4):]):
            addstr(stdscr, i + 2, x, text)

    keys = " ↑↓/jk move · enter full log · r refresh · a finished jobs · c cancel job · q quit"
    addstr(stdscr, h - 1, 0, (status or keys).ljust(w), curses.A_REVERSE)
    stdscr.refresh()
    return rows


def open_full_log(stdscr, job_id):
    curses.endwin()
    try:
        path = daic.log_path(job_id)
        if path:
            subprocess.run(f"ssh -o BatchMode=yes {daic.HOST} \"cat '{daic.REPO}/{path}'\" | less +G", shell=True)
    finally:
        stdscr.refresh()


def confirm(stdscr, question):
    h, w = stdscr.getmaxyx()
    addstr(stdscr, h - 1, 0, f" {question} (y/N) ".ljust(w), curses.A_REVERSE | curses.A_BOLD)
    stdscr.timeout(-1)
    key = stdscr.getch()
    stdscr.timeout(500)
    return key in (ord("y"), ord("Y"))


def main(stdscr):
    curses.curs_set(0)
    stdscr.timeout(500)
    colors = init_colors()
    app = App()
    threading.Thread(target=app.poll_jobs, daemon=True).start()
    threading.Thread(target=app.poll_log, daemon=True).start()

    status_until = 0
    while True:
        if app.status and time.time() > status_until:
            app.status = ""
        rows = draw(stdscr, app, colors)
        key = stdscr.getch()
        if key in (ord("q"), 27):
            break
        elif key in (curses.KEY_DOWN, ord("j")):
            app.move(rows, 1)
        elif key in (curses.KEY_UP, ord("k")):
            app.move(rows, -1)
        elif key == ord("r"):
            app.refresh_event.set()
            app.status, status_until = " Refreshing…", time.time() + 3
        elif key == ord("a"):
            app.show_finished = not app.show_finished
        elif key in (curses.KEY_ENTER, 10, 13) and app.selected:
            open_full_log(stdscr, app.selected)
        elif key == ord("c") and app.selected:
            job = next((r[1] for r in rows if r[0] == "job" and r[1]["id"] == app.selected), None)
            if job and confirm(stdscr, f"Cancel job {job['id']} ({job['name']})?"):
                try:
                    daic.cancel(job["id"])
                    app.status = f" Cancelled job {job['id']}"
                except Exception as e:
                    app.status = f" Cancel failed: {e}"
                status_until = time.time() + 5
                app.refresh_event.set()


if __name__ == "__main__":
    curses.wrapper(main)
