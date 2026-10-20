"""
Local dashboard for your DAIC jobs. Runs on your Mac, polls SLURM over SSH every 20 seconds,
and serves a page at http://localhost:8765 (bound to this machine only).

DAIC access (shared SSH connection, password from .env) lives in tools/daic.py.

Usage (from the repo root, with Python 3.9+ and sshpass installed):
    python3 tools/job_dashboard.py
"""
import json
import os
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from daic import fetch_jobs, job_log  # noqa: E402

PORT = int(os.environ.get("DASHBOARD_PORT", "8765"))
POLL_SECONDS = 20

state = {"jobs": [], "updated": None, "error": None}
state_lock = threading.Lock()
refresh_event = threading.Event()


def poller():
    while True:
        try:
            jobs = fetch_jobs()
            with state_lock:
                state.update(jobs=jobs, updated=datetime.now().isoformat(timespec="seconds"), error=None)
        except Exception as e:  # keep the last good data and show the error
            with state_lock:
                state["error"] = str(e)
        refresh_event.wait(POLL_SECONDS)
        refresh_event.clear()


class Handler(BaseHTTPRequestHandler):
    def send(self, body, content_type="application/json", status=200):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            self.send(PAGE, "text/html")
        elif url.path == "/api/jobs":
            with state_lock:
                self.send(json.dumps(state))
        elif url.path == "/api/log":
            try:
                self.send(json.dumps({"log": job_log(parse_qs(url.query).get("id", [""])[0])}))
            except Exception as e:
                self.send(json.dumps({"log": f"Could not read the log: {e}"}))
        else:
            self.send("not found", "text/plain", 404)

    def do_POST(self):
        if urlparse(self.path).path == "/api/refresh":
            refresh_event.set()
            self.send("{}")
        else:
            self.send("not found", "text/plain", 404)

    def log_message(self, *args):
        pass


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DAIC Jobs</title>
<style>
:root {
  --bg: #f3f5f7; --surface: #fff; --fg: #18202a; --muted: #5d6874; --line: #dbe1e6;
  --run: #1f6fd1; --wait: #8a6a00; --ok: #2e7d32; --bad: #c62828; --off: #7a838c;
  --mono: ui-monospace, "SF Mono", Menlo, monospace; --sans: -apple-system, "Segoe UI", system-ui, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #11161b; --surface: #19212a; --fg: #e3e8ed; --muted: #95a1ad; --line: #2a343e;
          --run: #6aa8f2; --wait: #e0b53c; --ok: #6cc97a; --bad: #f2837b; --off: #8c96a0; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 14px/1.45 var(--sans); }
header { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 20px; padding: 20px 24px 12px; }
h1 { margin: 0; font-size: 20px; }
.meta { color: var(--muted); font-size: 13px; }
.error { color: var(--bad); }
button { font: inherit; padding: 5px 12px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: var(--fg); cursor: pointer; }
button:hover { border-color: var(--muted); }
.counts { display: flex; flex-wrap: wrap; gap: 10px; padding: 0 24px 16px; }
.count { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 8px 14px; min-width: 110px; }
.count b { display: block; font-size: 22px; font-variant-numeric: tabular-nums; }
.count span { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .05em; }
main { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 42%); gap: 16px; padding: 0 24px 24px; }
@media (max-width: 1000px) { main { grid-template-columns: minmax(0, 1fr); } }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; overflow: auto; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line); white-space: nowrap; }
th { position: sticky; top: 0; background: var(--surface); color: var(--muted); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
tbody tr { cursor: pointer; }
tbody tr:hover, tbody tr.sel { background: color-mix(in srgb, var(--run) 10%, transparent); }
td.name { font-family: var(--mono); font-size: 13px; }
.pill { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; border: 1px solid currentColor; }
.RUNNING { color: var(--run); } .PENDING { color: var(--wait); } .COMPLETED { color: var(--ok); }
.FAILED, .TIMEOUT, .OUT_OF_MEMORY, .NODE_FAIL { color: var(--bad); } .CANCELLED { color: var(--off); }
.muted { color: var(--muted); }
.group td { background: var(--bg); color: var(--muted); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; cursor: default; }
#log { margin: 0; padding: 14px; font: 12px/1.5 var(--mono); white-space: pre-wrap; word-break: break-word; min-height: 200px; }
.loghead { padding: 10px 14px; border-bottom: 1px solid var(--line); font-weight: 600; }
</style>
</head>
<body>
<header>
  <h1>DAIC jobs</h1>
  <span class="meta" id="updated">Loading…</span>
  <span class="meta error" id="error"></span>
  <button id="refresh">Refresh now</button>
</header>
<div class="counts" id="counts"></div>
<main>
  <div class="panel"><table>
    <thead><tr><th>Job</th><th>ID</th><th>State</th><th>Time</th><th>Limit</th><th>Waiting on / reason</th><th>Start</th><th>Exit</th></tr></thead>
    <tbody id="rows"><tr><td colspan="8" class="muted">Fetching jobs from DAIC…</td></tr></tbody>
  </table></div>
  <div class="panel">
    <div class="loghead" id="loghead">Log</div>
    <pre id="log" class="muted">Click a job to see the end of its log.</pre>
  </div>
</main>
<script>
const ORDER = ["RUNNING", "PENDING", "FAILED", "TIMEOUT", "OUT_OF_MEMORY", "NODE_FAIL", "CANCELLED", "COMPLETED"];
const GROUP = s => s === "RUNNING" ? "Running" : s === "PENDING" ? "Waiting" :
  s === "COMPLETED" ? "Completed" : s === "CANCELLED" ? "Cancelled" : "Failed";
let selected = null;
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));

async function load() {
  const data = await (await fetch("/api/jobs")).json();
  document.getElementById("updated").textContent = data.updated ? "Updated " + data.updated.replace("T", " ") : "Fetching…";
  document.getElementById("error").textContent = data.error ? "Last refresh failed: " + data.error : "";
  const jobs = data.jobs;
  const groups = {};
  for (const j of jobs) (groups[GROUP(j.state)] ||= []).push(j);
  const counts = ["Running", "Waiting", "Failed", "Completed"].map(g =>
    `<div class="count"><b>${(groups[g] || []).length}</b><span>${g}</span></div>`).join("");
  document.getElementById("counts").innerHTML = counts;
  let html = "";
  for (const g of ["Running", "Waiting", "Failed", "Cancelled", "Completed"]) {
    if (!groups[g]) continue;
    html += `<tr class="group"><td colspan="8">${g} (${groups[g].length})</td></tr>`;
    for (const j of groups[g]) {
      const why = j.state === "PENDING" ? (j.reason === "Dependency" && j.depends ? "after " + j.depends : j.reason) : "";
      html += `<tr data-id="${esc(j.id)}" class="${j.id === selected ? "sel" : ""}">
        <td class="name">${esc(j.name)}${j.gpu ? ' <span class="muted">GPU</span>' : ""}</td>
        <td class="muted">${esc(j.id)}</td>
        <td><span class="pill ${esc(j.state)}">${esc(j.state.toLowerCase().replace(/_/g, " "))}</span></td>
        <td>${esc(j.elapsed)}</td><td class="muted">${esc(j.limit)}</td>
        <td class="muted">${esc(why)}</td><td class="muted">${esc((j.start || "").replace("T", " "))}</td>
        <td class="muted">${esc(j.exit && j.exit !== "0:0" ? j.exit : "")}</td></tr>`;
    }
  }
  document.getElementById("rows").innerHTML = html || '<tr><td colspan="8" class="muted">No jobs in the last 2 days.</td></tr>';
}

async function showLog(id) {
  selected = id;
  document.querySelectorAll("tbody tr").forEach(r => r.classList.toggle("sel", r.dataset.id === id));
  document.getElementById("loghead").textContent = "Log of job " + id;
  document.getElementById("log").textContent = "Loading…";
  const data = await (await fetch("/api/log?id=" + encodeURIComponent(id))).json();
  document.getElementById("log").textContent = data.log;
}

document.getElementById("rows").addEventListener("click", e => {
  const row = e.target.closest("tr[data-id]");
  if (row) showLog(row.dataset.id);
});
document.getElementById("refresh").addEventListener("click", async () => {
  await fetch("/api/refresh", {method: "POST"});
  setTimeout(load, 4000);
});
load();
setInterval(load, 15000);
</script>
</body>
</html>
"""


def main():
    threading.Thread(target=poller, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"DAIC job dashboard on http://localhost:{PORT} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
