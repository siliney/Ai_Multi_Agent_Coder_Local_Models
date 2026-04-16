# pipeline.py

import os
import json as _json
import ollama
from agents import AGENTS
from file_writer import write_project, extract_json
from chunker import estimate_file_count, build_chunk_prompts, CHUNK_THRESHOLD
from runner import auto_run, format_run_results


def _normrel(path: str, base: str) -> str:
    """Normalised relative path — case-folded, separator-agnostic."""
    return os.path.normcase(os.path.normpath(os.path.relpath(path, base)))


def _force_write(fixer_output: str, project_name: str, output_dir: str):
    """
    Parse fixer JSON, force the correct project_name, then write.
    Prevents project-name drift creating a parallel output directory.
    """
    data = extract_json(fixer_output)
    data["project_name"] = project_name          # always use the original name
    return write_project(_json.dumps(data), base_dir=output_dir)


# ── Helpers ────────────────────────────────────────────────

def ask_approval(stage: str, content: str) -> bool:
    """In interactive mode, show output and ask for approval."""
    print(f"\n{'─'*60}")
    print(f"  🎛️   REVIEW OUTPUT FROM: {stage.upper()}")
    print(f"{'─'*60}")
    print(content[:3000])
    if len(content) > 3000:
        print(f"\n  ... [{len(content) - 3000} more characters — see full output above] ...")
    print(f"\n{'─'*60}")
    while True:
        choice = input("  Approve and continue? [y]es / [r]etry / [q]uit: ").strip().lower()
        if choice in ("y", "yes"):
            return True
        if choice in ("r", "retry"):
            return False
        if choice in ("q", "quit"):
            raise SystemExit("Pipeline cancelled by user.")


def read_project_files(file_paths: list, base_path: str,
                        max_per_file: int = 1200, max_total: int = 14000) -> str:
    """Read actual file contents for the reviewer, with per-file and total size caps."""
    parts = []
    total = 0
    for f in file_paths[:30]:
        rel = os.path.relpath(f, base_path)
        try:
            with open(f, encoding="utf-8") as fh:
                raw = fh.read()
            snippet = raw[:max_per_file]
            if len(raw) > max_per_file:
                snippet += f"\n... [{len(raw) - max_per_file} chars not shown]"
            entry = f"### {rel}\n```\n{snippet}\n```"
        except OSError:
            entry = f"### {rel}\n(could not read)"
        if total + len(entry) > max_total:
            parts.append(f"### {rel}\n(omitted — total size limit reached)")
            # keep going so reviewer at least sees the filename
        else:
            parts.append(entry)
            total += len(entry)
    return "\n\n".join(parts)


def run_agent(role: str, prompt: str, verbose: bool = True) -> str:
    """Call an agent and stream its response so the user sees live progress."""
    agent = AGENTS[role]
    if verbose:
        print(f"\n{'='*60}")
        print(f"  🤖  {role.upper()} ({agent['model']})")
        print(f"{'='*60}")

    stream = ollama.chat(
        model=agent["model"],
        messages=[
            {"role": "system", "content": agent["system"]},
            {"role": "user",   "content": prompt},
        ],
        options=agent.get("options", {}),
        stream=True,
    )

    result = ""
    show_output = verbose and role not in ("coder", "fixer")
    if verbose and not show_output:
        print("  ⏳  Generating code", end="", flush=True)

    for chunk in stream:
        token = chunk["message"]["content"]
        result += token
        if show_output:
            print(token, end="", flush=True)
        elif verbose:
            # Print a dot every ~50 tokens so user knows it's alive
            if len(result) % 200 < len(token):
                print(".", end="", flush=True)

    if verbose:
        print()   # newline after streamed output

    return result


# ── Main Pipeline ───────────────────────────────────────────

HARD_CAP = 10   # absolute max fix iterations regardless of --max-fixes setting


def needs_revision(review: str) -> bool:
    """Return True if the reviewer's verdict requires fixes."""
    return "NEEDS REVISION" in review.upper()


def extract_issues(review: str) -> str:
    """Pull out just the Issues Found section from a review."""
    section, in_section = [], False
    for line in review.splitlines():
        if "Issues Found" in line:
            in_section = True
        elif line.startswith("## ") and in_section:
            break
        elif in_section:
            section.append(line)
    return " ".join(section).strip().lower()


def is_converged(prev_review: str, curr_review: str, threshold: float = 0.75) -> bool:
    """True if two consecutive reviews flag substantially the same issues — fixer isn't making progress."""
    a = set(extract_issues(prev_review).split())
    b = set(extract_issues(curr_review).split())
    if not a or not b:
        return False
    overlap = len(a & b) / max(len(a), len(b))
    return overlap >= threshold


def run_pipeline(
    task: str,
    output_dir: str = "output",
    interactive: bool = False,
    auto_run_enabled: bool = True,
    max_fix_iterations: int = 3,
) -> dict:

    print(f"\n{'#'*60}")
    print(f"  TASK: {task}")
    print(f"{'#'*60}")

    all_written_files = []
    project_path = None

    # ── Stage 1: Architect ──────────────────────────────────
    while True:
        architecture = run_agent(
            "architect",
            f"Design an implementation plan and file structure for:\n\n{task}",
        )
        if not interactive or ask_approval("architect", architecture):
            break
        print("  🔄  Retrying Architect...")

    # ── Stage 2: Coder (with chunking) ─────────────────────
    file_estimate = estimate_file_count(architecture)
    use_chunks = file_estimate >= CHUNK_THRESHOLD

    if use_chunks:
        print(f"\n  🧩  Large project detected (~{file_estimate} files) — using chunked output.")
        chunk_prompts = build_chunk_prompts(task, architecture)
    else:
        chunk_prompts = [
            f"Implement the full project.\n\nTASK:\n{task}\n\nPLAN:\n{architecture}"
        ]

    chunk_context = ""   # grows with each written chunk so later chunks don't re-implement files

    for i, prompt in enumerate(chunk_prompts):
        if use_chunks:
            print(f"\n  🧩  Chunk {i+1} of {len(chunk_prompts)}")

        # Inject inter-chunk context so the coder knows what was already built
        if chunk_context:
            prompt = prompt + (
                f"\n\nFILES ALREADY IMPLEMENTED IN PREVIOUS CHUNKS (do NOT re-implement these):\n"
                f"{chunk_context}"
            )

        while True:
            coder_output = run_agent("coder", prompt)
            if not interactive or ask_approval(f"coder (chunk {i+1})", coder_output):
                break
            print(f"  🔄  Retrying Coder chunk {i+1}...")

        print(f"\n{'='*60}")
        print(f"  💾  FILE WRITER — Chunk {i+1}")
        print(f"{'='*60}")
        try:
            project_path, written = write_project(coder_output, base_dir=output_dir)
            all_written_files.extend(written)
            # Record what this chunk produced for subsequent chunks
            if project_path:
                new_files = "\n".join(
                    os.path.relpath(f, project_path) for f in written
                )
                chunk_context += new_files + "\n"
        except ValueError as e:
            print(f"  ❌  File writing failed: {e}")

    print(f"\n  ✅  {len(all_written_files)} file(s) written to: {project_path}")

    # ── Stage 3: Auto-Run & Test ────────────────────────────
    run_results = []
    if auto_run_enabled and project_path:
        run_results = auto_run(project_path)

    # ── Stage 4: Review → Fix loop ──────────────────────────
    original_project_path = project_path
    all_written_files, review, run_results = _fix_loop(
        task=task,
        all_written_files=all_written_files,
        original_project_path=original_project_path,
        output_dir=output_dir,
        run_results=run_results,
        interactive=interactive,
        auto_run_enabled=auto_run_enabled,
        max_fix_iterations=max_fix_iterations,
    )

    # ── Stage 5: Save REVIEW.md ─────────────────────────────
    _save_review(original_project_path, task, review, run_results)

    return {
        "task":          task,
        "architecture":  architecture,
        "project_path":  original_project_path,
        "written_files": all_written_files,
        "review":        review,
        "run_results":   run_results,
    }


# ── Shared fix loop ─────────────────────────────────────────

def _fix_loop(
    task: str,
    all_written_files: list,
    original_project_path: str,
    output_dir: str,
    run_results: list,
    interactive: bool,
    auto_run_enabled: bool,
    max_fix_iterations: int,
    seed_review: str = None,   # pass last review when resuming
) -> tuple:
    """
    Runs the Reviewer → Fixer loop until PASS, convergence, or cap.
    Returns (all_written_files, final_review, run_results).
    """
    review = None
    fix_history = [seed_review] if seed_review else []
    fix_iter = 0
    unlimited = (max_fix_iterations == 0)

    while True:
        file_listing = read_project_files(all_written_files, original_project_path)
        round_label = "reviewer" if fix_iter == 0 else f"reviewer (fix round {fix_iter})"

        while True:
            review = run_agent(
                "reviewer",
                f"Review this project.\n\nTASK: {task}\n\nFILES:\n{file_listing}",
            )
            if not interactive or ask_approval(round_label, review):
                break
            print(f"  🔄  Retrying Reviewer (round {fix_iter})...")

        # ── Exit conditions ──────────────────────────────────

        if not needs_revision(review):
            verdict = "PASS WITH NOTES" if "PASS WITH" in review.upper() else "PASS"
            print(f"\n  ✅  [{verdict}] Reviewer satisfied after {fix_iter} fix iteration(s).")
            break

        if fix_iter >= HARD_CAP:
            print(f"\n  ⚠️  Reached hard cap of {HARD_CAP} fix iterations. Stopping.")
            print(f"       Run with --resume {os.path.basename(original_project_path)} to continue later.")
            break

        if not unlimited and fix_iter >= max_fix_iterations:
            print(f"\n  ⚠️  Reached --max-fixes limit ({max_fix_iterations}). Stopping.")
            print(f"       Resume with: python main.py --resume {os.path.basename(original_project_path)}")
            print(f"       Or rerun with: --max-fixes 0  to loop until satisfied.")
            break

        if fix_history and is_converged(fix_history[-1], review):
            print(f"\n  ⚠️  Review issues unchanged — fixer is not making progress. Stopping.")
            print(f"       Resume with: python main.py --resume {os.path.basename(original_project_path)}")
            break

        # ── Fixer ───────────────────────────────────────────
        fix_iter += 1
        cap_label = "unlimited" if unlimited else str(max_fix_iterations)
        print(f"\n  🔧  NEEDS REVISION — running Fixer (iteration {fix_iter}/{cap_label})...")

        MAX_FILE_CHARS = 1500
        current_files_content = []
        for f in all_written_files[:20]:
            # Always use forward slashes — LLMs are trained on Unix paths
            rel = os.path.relpath(f, original_project_path).replace(os.sep, "/")
            try:
                with open(f, encoding="utf-8") as fh:
                    raw = fh.read()
                snippet = raw[:MAX_FILE_CHARS]
                if len(raw) > MAX_FILE_CHARS:
                    snippet += f"\n... [{len(raw) - MAX_FILE_CHARS} chars truncated]"
                current_files_content.append(f"### {rel}\n```\n{snippet}\n```")
            except OSError:
                current_files_content.append(f"### {rel}\n(could not read file)")

        project_name = os.path.basename(original_project_path)

        history_block = ""
        if fix_history:
            history_block = "\n\nPREVIOUS FIX ATTEMPTS THAT DID NOT SATISFY THE REVIEWER:\n"
            for idx, prev_review in enumerate(fix_history[-2:], 1):
                section, in_section = "", False
                for line in prev_review.splitlines():
                    if "Issues Found" in line:
                        in_section = True
                    elif line.startswith("## ") and in_section:
                        break
                    elif in_section:
                        section += line + "\n"
                history_block += f"\nAttempt {idx} issues:\n{section.strip()[:600]}\n"
            history_block += "\nDo NOT repeat these same mistakes.\n"

        fixer_prompt = (
            f"Fix the issues identified in this code review.\n\n"
            f"You MUST use project_name: \"{project_name}\" in your JSON response.\n\n"
            f"ORIGINAL TASK:\n{task}\n\n"
            f"CODE REVIEW:\n{review}"
            f"{history_block}\n\n"
            f"CURRENT FILES:\n" + "\n\n".join(current_files_content)
        )

        while True:
            fixer_output = run_agent("fixer", fixer_prompt)
            if not interactive or ask_approval(f"fixer (round {fix_iter})", fixer_output):
                break
            print(f"  🔄  Retrying Fixer (round {fix_iter})...")

        print(f"\n{'='*60}")
        print(f"  💾  FILE WRITER — Fix round {fix_iter}")
        print(f"{'='*60}")

        write_ok = False
        for attempt in range(2):
            try:
                # _force_write patches project_name before writing — prevents new dir creation
                _, written = _force_write(fixer_output, project_name, output_dir)
                # Normalised comparison handles / vs \ and case differences on Windows
                written_rels = {_normrel(f, original_project_path) for f in written}
                all_written_files = [
                    f for f in all_written_files
                    if _normrel(f, original_project_path) not in written_rels
                ] + written
                write_ok = True
                break
            except ValueError as e:
                print(f"  ❌  File writing failed (attempt {attempt + 1}): {e}")
                if attempt == 0:
                    print("  🔄  Retrying fixer call...")
                    fixer_output = run_agent("fixer", fixer_prompt, verbose=False)

        if not write_ok:
            print("  ⚠️  Skipping this fix iteration — moving to next review.")

        fix_history.append(review)

        if auto_run_enabled and original_project_path:
            run_results = auto_run(original_project_path)

    return all_written_files, review, run_results


def _save_review(project_path: str, task: str, review: str, run_results: list):
    """Write REVIEW.md to the project folder."""
    if not project_path or not review:
        return
    run_section = format_run_results(run_results) if run_results else ""
    content = f"# Code Review\n\n**Task:** {task}\n\n---\n\n{review}"
    if run_section:
        content += f"\n\n---\n\n{run_section}"
    with open(os.path.join(project_path, "REVIEW.md"), "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n  📝  Review saved to: {project_path}/REVIEW.md")


# ── Resume pipeline ─────────────────────────────────────────

def resume_pipeline(
    project_name: str,
    output_dir: str = "output",
    interactive: bool = False,
    auto_run_enabled: bool = True,
    max_fix_iterations: int = 3,
    force: bool = False,
) -> dict:
    """
    Resume a stopped pipeline by reading the last REVIEW.md from an existing
    project and re-entering the fix loop without re-running Architect or Coder.
    """
    project_path = os.path.join(output_dir, project_name)
    review_path  = os.path.join(project_path, "REVIEW.md")

    if not os.path.isdir(project_path):
        raise FileNotFoundError(f"Project folder not found: {project_path}")
    if not os.path.exists(review_path):
        raise FileNotFoundError(f"No REVIEW.md found in {project_path} — run the full pipeline first.")

    # ── Parse REVIEW.md ──────────────────────────────────────
    with open(review_path, encoding="utf-8") as f:
        raw = f.read()

    # Extract task from "**Task:** ..." line
    task = ""
    for line in raw.splitlines():
        if line.startswith("**Task:**"):
            task = line[len("**Task:**"):].strip()
            break

    # Extract the review body (between first and second "---" separators)
    parts = raw.split("\n\n---\n\n")
    last_review = parts[1].strip() if len(parts) >= 2 else raw

    # ── Collect project files ────────────────────────────────
    all_written_files = []
    for root, _, files in os.walk(project_path):
        for fname in sorted(files):
            if fname == "REVIEW.md":
                continue
            all_written_files.append(os.path.join(root, fname))

    print(f"\n{'#'*60}")
    print(f"  🔄  RESUME: {project_path}")
    print(f"  TASK: {task or '(unknown — check REVIEW.md)'}")
    print(f"  FILES: {len(all_written_files)} found on disk")
    print(f"{'#'*60}")

    if not needs_revision(last_review):
        if not force:
            print("\n  ✅  Last review already PASSED — nothing left to fix.")
            print(f"  Use --force to re-review and fix anyway.")
            print(f"  Check {review_path} for the full report.")
            return {
                "task": task, "project_path": project_path,
                "written_files": all_written_files, "review": last_review,
            }
        print("\n  💪  --force set — re-reviewing even though last run PASSED...")
    else:
        print("\n  📋  Last review says NEEDS REVISION — re-entering fix loop...")
    print(f"  The last review is seeded as the first fix-history entry so the")
    print(f"  fixer knows what was already tried.\n")

    # Re-run tests so run_results are fresh
    run_results = auto_run(project_path) if auto_run_enabled else []

    # Re-enter the fix loop, seeding with the last review
    all_written_files, review, run_results = _fix_loop(
        task=task,
        all_written_files=all_written_files,
        original_project_path=project_path,
        output_dir=output_dir,
        run_results=run_results,
        interactive=interactive,
        auto_run_enabled=auto_run_enabled,
        max_fix_iterations=max_fix_iterations,
        seed_review=last_review,
    )

    _save_review(project_path, task, review, run_results)

    return {
        "task":          task,
        "project_path":  project_path,
        "written_files": all_written_files,
        "review":        review,
        "run_results":   run_results,
    }
