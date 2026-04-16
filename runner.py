# runner.py
# Detects the project type and runs it automatically after generation.

import os
import subprocess
import shutil


def detect_project_type(project_path: str) -> str:
    """Detect what kind of project was generated."""
    files = []
    for root, _, filenames in os.walk(project_path):
        for f in filenames:
            files.append(f)

    if "package.json" in files:
        return "node"
    if "requirements.txt" in files or any(f.endswith(".py") for f in files):
        return "python"
    if "go.mod" in files:
        return "go"
    if any(f.endswith(".sh") for f in files):
        return "shell"
    return "unknown"


def run_command(cmd: list[str], cwd: str, label: str, timeout: int = 60) -> dict:
    """Run a shell command and return result."""
    print(f"\n  ▶️   {label}")
    print(f"      $ {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        success = result.returncode == 0
        output = (result.stdout + result.stderr).strip()
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"      {status}")
        if output:
            # Print last 20 lines to avoid flooding the terminal
            lines = output.split("\n")
            preview = "\n".join(lines[-20:])
            print(f"\n{preview}\n")
        return {"label": label, "success": success, "output": output}
    except subprocess.TimeoutExpired:
        print("      ⏱️  TIMED OUT")
        return {"label": label, "success": False, "output": "Command timed out."}
    except FileNotFoundError as e:
        print(f"      ⚠️  SKIPPED — {e}")
        return {"label": label, "success": None, "output": str(e)}


def auto_run(project_path: str) -> list[dict]:
    """
    Install dependencies and run tests for the generated project.
    Returns a list of result dicts.
    """
    project_type = detect_project_type(project_path)
    results = []

    print(f"\n{'='*60}")
    print(f"  ▶️   RUNNER  (detected: {project_type})")
    print(f"{'='*60}")

    if project_type == "python":
        # Install dependencies
        req = os.path.join(project_path, "requirements.txt")
        if os.path.exists(req):
            results.append(run_command(
                ["pip", "install", "-r", "requirements.txt", "--quiet"],
                cwd=project_path,
                label="Install Python dependencies",
            ))

        # Run pytest if tests exist
        test_dirs = ["tests", "test"]
        has_tests = any(
            os.path.isdir(os.path.join(project_path, d)) for d in test_dirs
        )
        if has_tests and shutil.which("pytest"):
            results.append(run_command(
                ["pytest", "--tb=short", "-q"],
                cwd=project_path,
                label="Run pytest",
                timeout=120,
            ))
        else:
            # Try running main.py with --help as a smoke test
            main_candidates = ["src/main.py", "main.py", "app.py"]
            for candidate in main_candidates:
                full = os.path.join(project_path, candidate)
                if os.path.exists(full):
                    results.append(run_command(
                        ["python", candidate, "--help"],
                        cwd=project_path,
                        label=f"Smoke test: python {candidate} --help",
                        timeout=15,
                    ))
                    break

    elif project_type == "node":
        # Install npm packages
        results.append(run_command(
            ["npm", "install", "--silent"],
            cwd=project_path,
            label="npm install",
            timeout=120,
        ))

        # Run tests if test script exists
        pkg_path = os.path.join(project_path, "package.json")
        if os.path.exists(pkg_path):
            import json
            with open(pkg_path) as f:
                pkg = json.load(f)
            if "test" in pkg.get("scripts", {}):
                results.append(run_command(
                    ["npm", "test", "--", "--passWithNoTests"],
                    cwd=project_path,
                    label="npm test",
                    timeout=120,
                ))

    elif project_type == "go":
        results.append(run_command(
            ["go", "build", "./..."],
            cwd=project_path,
            label="go build",
        ))
        results.append(run_command(
            ["go", "test", "./..."],
            cwd=project_path,
            label="go test",
            timeout=120,
        ))

    elif project_type == "shell":
        for f in os.listdir(project_path):
            if f.endswith(".sh"):
                results.append(run_command(
                    ["bash", "-n", f],   # syntax check only
                    cwd=project_path,
                    label=f"Syntax check: {f}",
                ))
                break

    else:
        print("  ⚠️  Unknown project type — skipping auto-run.")

    return results


def format_run_results(results: list[dict]) -> str:
    """Format run results for inclusion in the review file."""
    if not results:
        return "No tests were run."
    lines = ["## ▶️ Auto-Run Results\n"]
    for r in results:
        status = "✅ PASSED" if r["success"] else ("❌ FAILED" if r["success"] is False else "⚠️ SKIPPED")
        lines.append(f"### {r['label']} — {status}")
        if r["output"]:
            lines.append(f"```\n{r['output'][:1000]}\n```")
        lines.append("")
    return "\n".join(lines)
