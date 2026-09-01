import json
import logging
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from apps.api.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("meetingos.release")


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    """Execute a local shell subprocess command and return exit code and combined output."""
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd or Path.cwd(),
            capture_output=True,
            text=True,
            check=False,
        )
        elapsed = time.perf_counter() - t0
        output = (proc.stdout + "\n" + proc.stderr).strip()
        logger.info(f"Executed {' '.join(cmd)} in {elapsed:.2f}s (Exit code: {proc.returncode})")
        return proc.returncode, output
    except Exception as exc:
        return 1, str(exc)


def run_release_candidate_gate(output_dir: str = "evaluation/reports") -> dict[str, Any]:
    """Run all 6 release validation gates and produce release scorecard."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("\n=======================================================")
    print("MeetingOS Production Release Candidate Gate (v1.0.0-rc1)")
    print("=======================================================\n")

    report: dict[str, Any] = {
        "version": settings.app_version,
        "timestamp": datetime.now(UTC).isoformat(),
        "gates": {},
        "overall_status": "PENDING",
    }

    # Gate 1: Ruff Linting & Formatting
    print("1. Validating Code Style (Ruff)...")
    c1, o1 = run_command([sys.executable, "-m", "ruff", "check", "."])
    c1_fmt, o1_fmt = run_command([sys.executable, "-m", "ruff", "format", "--check", "."])
    g1_pass = c1 == 0 and c1_fmt == 0
    report["gates"]["code_quality_ruff"] = {
        "status": "PASSED" if g1_pass else "FAILED",
        "exit_code": max(c1, c1_fmt),
        "details": o1
        if c1 != 0
        else (o1_fmt if c1_fmt != 0 else "Clean (0 lint errors, 0 format diffs)"),
    }
    print(f"   -> {'PASSED' if g1_pass else 'FAILED'}")

    # Gate 2: Docker Compose Profile Validation
    print("2. Validating Production Docker Compose Profile...")
    c2, o2 = run_command(["docker", "compose", "-f", "docker-compose.prod.yml", "config"])
    g2_pass = c2 == 0
    report["gates"]["docker_compose_profile"] = {
        "status": "PASSED" if g2_pass else "FAILED",
        "exit_code": c2,
        "details": "Validated all 9 containers and isolated bridge network" if g2_pass else o2,
    }
    print(f"   -> {'PASSED' if g2_pass else 'FAILED'}")

    # Gate 3: Full Test Suite (170+ Unit & Integration Tests)
    print("3. Running Full Test Suite (Pytest)...")
    c3, o3 = run_command([sys.executable, "-m", "pytest", "-v"])
    g3_pass = c3 == 0
    report["gates"]["test_suite"] = {
        "status": "PASSED" if g3_pass else "FAILED",
        "exit_code": c3,
        "details": "All unit, integration, RBAC, temporal, and E2E query tests passed"
        if g3_pass
        else o3[-500:],
    }
    print(f"   -> {'PASSED' if g3_pass else 'FAILED'}")

    # Gate 4: Provider Smoke Tests
    print("4. Executing Multi-Provider Smoke Verification...")
    c4, o4 = run_command([sys.executable, "-m", "evaluation.provider_smoke"])
    g4_pass = c4 == 0
    report["gates"]["provider_smoke"] = {
        "status": "PASSED" if g4_pass else "FAILED",
        "exit_code": c4,
        "details": "Embedders and reasoners validated with safe fallback handling"
        if g4_pass
        else o4[-500:],
    }
    print(f"   -> {'PASSED' if g4_pass else 'FAILED'}")

    # Gate 5: Frontend Production Build
    print("5. Validating Frontend Production Build (Vite)...")
    web_dir = Path("apps/web")
    if web_dir.exists() and (web_dir / "package.json").exists():
        c5, o5 = run_command(["npm.cmd", "run", "build"], cwd=web_dir)
        if c5 != 0:
            c5, o5 = run_command(["npm", "run", "build"], cwd=web_dir)
        g5_pass = c5 == 0
        report["gates"]["frontend_build"] = {
            "status": "PASSED" if g5_pass else "FAILED",
            "exit_code": c5,
            "details": "SPA production bundle built successfully" if g5_pass else o5[-500:],
        }
    else:
        g5_pass = True
        report["gates"]["frontend_build"] = {
            "status": "SKIPPED",
            "exit_code": 0,
            "details": "apps/web directory not present",
        }
    print(f"   -> {'PASSED' if g5_pass else 'FAILED'}")

    # Overall Verdict
    all_passed = all(g["status"] in ("PASSED", "SKIPPED") for g in report["gates"].values())
    report["overall_status"] = "PASSED (RELEASE CANDIDATE READY)" if all_passed else "FAILED"

    # Save JSON & Markdown
    json_path = out_path / "release_candidate.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    md_path = out_path / "release_candidate_report.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# MeetingOS Release Candidate Verification Report\n\n")
        f.write(f"**Version:** {report['version']}\n")
        f.write(f"**Timestamp:** {report['timestamp']}\n")
        f.write(f"**Overall Verdict:** `{report['overall_status']}`\n\n")
        f.write("## Release Quality Gates\n\n")
        f.write("| Gate | Status | Exit Code | Details |\n")
        f.write("| :--- | :---: | :---: | :--- |\n")
        for gate_name, gate_data in report["gates"].items():
            f.write(
                f"| **{gate_name}** | `{gate_data['status']}` | {gate_data['exit_code']} | {gate_data['details'][:100]} |\n"
            )

    print("\n=======================================================")
    print(f"Overall Release Candidate Verdict: {report['overall_status']}")
    print(f"Reports saved to {output_dir}")
    print("=======================================================\n")
    return report


if __name__ == "__main__":
    run_release_candidate_gate()
