#!/usr/bin/env python3
"""
MeetingOS - Unified Service Runner (run_all.py)

Orchestrates and launches all MeetingOS services with a single command:
  1. Infrastructure (Docker Postgres + Redis, if Docker is available)
  2. Database migrations (Alembic) - the run stops if they fail
  3. FastAPI Backend API (uvicorn)
  4. React Web Frontend (Vite)
  5. Celery Background Worker (if Redis is available)

Usage:
  python run_all.py
  uv run python run_all.py
  ./run_all.ps1       (PowerShell)
  run_all.bat         (Command Prompt)

Options:
  --no-docker    Skip starting Docker containers
  --no-worker    Skip starting the Celery background worker
  --no-migrate   Skip running database migrations
  --no-web       Start backend only, skip web frontend
  --open         Open the web UI in default browser once ready
"""

import argparse
import atexit
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

# Configure utf-8 encoding safely on Windows consoles
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass

# ANSI colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Enable VT100 colors on Windows console
if sys.platform == "win32":
    os.system("")

ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "apps" / "web"
WORKER_QUEUES = "default,meetingos.asr,meetingos.sync"
MAX_RESTARTS = 3


class Service:
    def __init__(self, name: str, cmd: list[str], cwd: Path, color: str) -> None:
        self.name = name
        self.cmd = cmd
        self.cwd = cwd
        self.color = color
        self.proc: subprocess.Popen[str] | None = None
        self.restarts = 0
        self.gave_up = False


services: list[Service] = []
shutdown_initiated = False


def log(tag: str, msg: str, color: str = CYAN) -> None:
    print(f"{color}{BOLD}[{tag}]{RESET} {msg}", flush=True)


def check_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a TCP port is currently open and accepting connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


def wait_for_port(host: str, port: int, seconds: int) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if check_port_open(host, port, timeout=0.5):
            return True
        time.sleep(1)
    return False


def stream_output(prefix: str, color: str, pipe) -> None:
    """Stream stdout/stderr of a child process with a colored prefix."""
    try:
        for line in iter(pipe.readline, ""):
            if shutdown_initiated:
                break
            stripped = line.rstrip()
            if stripped:
                print(f"{color}[{prefix}]{RESET} {stripped}", flush=True)
    except (ValueError, OSError):
        pass
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def kill_process_tree(proc: subprocess.Popen[str]) -> None:
    """Force-terminate process and all its children across Windows/Linux."""
    if proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
    except Exception:
        pass


def cleanup_all() -> None:
    global shutdown_initiated
    if shutdown_initiated:
        return
    shutdown_initiated = True
    print("\n")
    log("SHUTDOWN", "Stopping all MeetingOS services...", YELLOW)
    for svc in reversed(services):
        if svc.proc is not None:
            log("SHUTDOWN", f"Stopping {svc.name} (PID: {svc.proc.pid})...", YELLOW)
            kill_process_tree(svc.proc)
    log("SHUTDOWN", "All services stopped.", GREEN)


def signal_handler(_signum, _frame) -> None:
    cleanup_all()
    sys.exit(0)


atexit.register(cleanup_all)


def python_cmd(*args: str) -> list[str]:
    uv_bin = shutil.which("uv")
    return [uv_bin, "run", *args] if uv_bin else [sys.executable, "-m", *args]


def start_docker_infra() -> bool:
    """Start the Docker Postgres and Redis containers and wait until they accept connections."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        log("DOCKER", "Docker CLI not found in PATH. Skipping docker compose.", YELLOW)
        return False

    res = subprocess.run(
        [docker_bin, "compose", "up", "-d"],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        log(
            "DOCKER",
            "Could not start containers (is Docker Desktop running?): "
            + (res.stderr.strip() or res.stdout.strip()),
            YELLOW,
        )
        return False

    if wait_for_port("localhost", 5432, 60) and wait_for_port("localhost", 6379, 30):
        log("DOCKER", "PostgreSQL and Redis are accepting connections.", GREEN)
        return True
    log("DOCKER", "Containers started but did not become reachable within 60s.", YELLOW)
    return False


def run_migrations() -> bool:
    """Bring the database schema to the latest Alembic revision."""
    log("DB", "Applying database migrations (alembic upgrade head)...", CYAN)
    res = subprocess.run(
        python_cmd("alembic", "upgrade", "head"),
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode == 0:
        log("DB", "Database schema is up to date.", GREEN)
        return True
    log("DB", "Migrations FAILED:", RED)
    print((res.stderr or res.stdout).strip()[-3000:], flush=True)
    return False


def spawn(svc: Service) -> None:
    """Start (or restart) a supervised subprocess with streamed output."""
    log(svc.name, f"Starting: {' '.join(svc.cmd)}", svc.color)
    svc.proc = subprocess.Popen(
        svc.cmd,
        cwd=str(svc.cwd),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    threading.Thread(
        target=stream_output, args=(svc.name, svc.color, svc.proc.stdout), daemon=True
    ).start()
    threading.Thread(
        target=stream_output, args=(svc.name, svc.color, svc.proc.stderr), daemon=True
    ).start()


def ensure_web_dependencies(npm_bin: str) -> bool:
    if (WEB_DIR / "node_modules").is_dir():
        return True
    log("WEB", "Installing frontend dependencies (npm install)...", GREEN)
    res = subprocess.run([npm_bin, "install"], cwd=str(WEB_DIR), check=False)
    return res.returncode == 0


def main() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(description="MeetingOS - Run all services")
    parser.add_argument("--no-docker", action="store_true", help="Skip docker compose up -d")
    parser.add_argument("--no-worker", action="store_true", help="Skip starting the Celery worker")
    parser.add_argument("--no-migrate", action="store_true", help="Skip running Alembic migrations")
    parser.add_argument("--no-web", action="store_true", help="Skip starting the web frontend")
    parser.add_argument("--open", action="store_true", help="Open the browser once ready")
    args = parser.parse_args()

    print(f"{CYAN}{BOLD}")
    print("==============================================================================")
    print("  MeetingOS - Unified Service Runner")
    print("==============================================================================")
    print(f"{RESET}")

    if not args.no_docker:
        start_docker_infra()

    # Starting the API against an out-of-date schema only produces confusing errors later
    if not args.no_migrate and not run_migrations():
        log(
            "DB", "Fix the migration error above (or rerun with --no-migrate), then try again.", RED
        )
        sys.exit(1)

    services.append(
        Service(
            "API",
            python_cmd(
                "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"
            ),
            ROOT_DIR,
            BLUE,
        )
    )

    if not args.no_worker:
        if check_port_open("localhost", 6379, timeout=0.5):
            worker_cmd = python_cmd(
                "celery",
                "-A",
                "workers.celery_app",
                "worker",
                "--loglevel=info",
                "-Q",
                WORKER_QUEUES,
            )
            if sys.platform == "win32":
                # Celery's default prefork pool does not work on Windows (crash-loops)
                worker_cmd += ["--pool=solo"]
            services.append(Service("CELERY", worker_cmd, ROOT_DIR, MAGENTA))
        else:
            log(
                "CELERY",
                "Redis is not reachable on localhost:6379 - worker skipped. Background uploads will run inside the API process.",
                YELLOW,
            )

    if not args.no_web:
        npm_bin = shutil.which("npm.cmd" if sys.platform == "win32" else "npm") or shutil.which(
            "npm"
        )
        if WEB_DIR.exists() and npm_bin and ensure_web_dependencies(npm_bin):
            services.append(Service("WEB", [npm_bin, "run", "dev"], WEB_DIR, GREEN))
        else:
            log(
                "WEB",
                "npm not found or dependencies failed to install - web frontend skipped.",
                YELLOW,
            )

    for svc in services:
        spawn(svc)

    print(f"\n{BOLD}MeetingOS services are running:{RESET}")
    print(f"  {GREEN}-> Web Frontend:  {BOLD}http://localhost:5173{RESET}")
    print(f"  {BLUE}-> API Server:    {BOLD}http://localhost:8000{RESET}")
    print(f"  {CYAN}-> Swagger Docs:  {BOLD}http://localhost:8000/api/v1/docs{RESET}")
    print(f"  {CYAN}-> Health Check:  {BOLD}http://localhost:8000/api/v1/health{RESET}")
    print(f"\n{YELLOW}Press Ctrl+C at any time to stop all services.{RESET}\n")

    if args.open:
        time.sleep(2)
        try:
            import webbrowser

            webbrowser.open("http://localhost:5173")
        except Exception:
            pass

    # Supervise: report each exit once and restart a few times before giving up
    try:
        while True:
            time.sleep(1)
            for svc in services:
                if svc.gave_up or svc.proc is None or svc.proc.poll() is None or shutdown_initiated:
                    continue
                code = svc.proc.returncode
                if svc.restarts < MAX_RESTARTS:
                    svc.restarts += 1
                    log(
                        svc.name,
                        f"Exited with code {code}; restarting ({svc.restarts}/{MAX_RESTARTS})...",
                        RED,
                    )
                    time.sleep(2)
                    spawn(svc)
                else:
                    svc.gave_up = True
                    log(
                        svc.name,
                        f"Exited with code {code} again; not restarting. Check the output above.",
                        RED,
                    )
    except KeyboardInterrupt:
        cleanup_all()
        sys.exit(0)


if __name__ == "__main__":
    main()
