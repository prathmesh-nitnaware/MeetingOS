# ==============================================================================
# MeetingOS - Unified Startup Script for Windows PowerShell
# Launches Docker infra, migrations, FastAPI backend, React web, and Celery.
# ==============================================================================

if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv run python run_all.py $args
} else {
    python run_all.py $args
}
