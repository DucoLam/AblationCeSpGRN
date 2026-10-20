"""
DAIC access shared by the job tools: one shared SSH connection (ControlMaster in ~/.ssh/config,
Host daic), opened with the password from the repo's .env (pass=...) only when it is closed.
"""
import os
import re
import subprocess
from datetime import datetime, timedelta

HOST = os.environ.get("DAIC_HOST", "daic")
REPO = os.environ.get("DAIC_REPO", "/tudelft.net/staff-umbrella/ScReNI/AblationCeSpGRN")
HISTORY_DAYS = 2
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")


def read_password():
    with open(ENV_FILE) as f:
        for line in f:
            key, _, value = line.strip().partition("=")
            if key.replace("export ", "").strip() == "pass":
                return value.strip().strip("'\"")
    raise RuntimeError("no pass= line in .env")


def ensure_connection():
    if subprocess.run(["ssh", "-O", "check", HOST], capture_output=True).returncode == 0:
        return
    env = dict(os.environ, SSHPASS=read_password())
    result = subprocess.run(["sshpass", "-e", "ssh", "-o", "ConnectTimeout=15", HOST, "true"],
                            env=env, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError("login to DAIC failed (VPN on? password in .env still valid?)")


def remote(command, timeout=60):
    ensure_connection()
    result = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, command],
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        err = result.stderr.strip().splitlines()
        raise RuntimeError(err[-1] if err else "ssh failed")
    return result.stdout


def fetch_jobs():
    """Your jobs from the last HISTORY_DAYS days, newest first."""
    since = (datetime.now() - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%dT%H:%M:%S")
    out = remote(
        "squeue -u $USER -h -o '%i|%j|%T|%M|%l|%R|%E|%S'; echo '---'; "
        f"sacct -u $USER -X -n -P -S {since} -o JobID,JobName,State,Elapsed,Timelimit,Start,End,ExitCode,ReqTRES"
    )
    active_part, _, history_part = out.partition("---")
    jobs = {}
    for line in history_part.strip().splitlines():
        f = line.split("|")
        if len(f) < 9:
            continue
        jobs[f[0]] = {"id": f[0], "name": f[1], "state": f[2].split()[0], "elapsed": f[3], "limit": f[4],
                      "start": f[5], "end": f[6], "exit": f[7], "gpu": "gpu" in f[8], "reason": "", "depends": ""}
    for line in active_part.strip().splitlines():
        f = line.split("|")
        if len(f) < 8:
            continue
        job = jobs.setdefault(f[0], {"id": f[0], "name": f[1], "start": "", "end": "", "exit": "", "gpu": False})
        job.update({"state": f[2], "elapsed": f[3], "limit": f[4], "reason": f[5].strip("()"),
                    "depends": "" if f[6] == "(null)" else f[6]})
        if f[2] == "PENDING" and f[7] not in ("N/A", ""):
            job["start"] = f"est. {f[7]}"
    return sorted(jobs.values(), key=lambda j: int(re.sub(r"\D", "", j["id"]) or 0), reverse=True)


def log_path(job_id):
    if not job_id.isdigit():
        raise ValueError("bad job id")
    return remote(f"cd {REPO} && ls -t slurm/logs/*/*_{job_id}.log slurm/logs/*_{job_id}.log 2>/dev/null | head -1").strip()


def job_log(job_id, lines=80):
    path = log_path(job_id)
    if not path:
        return "No log file for this job yet."
    return f"== {path}\n" + remote(f"cd {REPO} && tail -n {int(lines)} '{path}'")


def cancel(job_id):
    if not job_id.isdigit():
        raise ValueError("bad job id")
    remote(f"scancel {job_id}")
