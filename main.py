# main.py

import sys
import json
import argparse
from datetime import datetime
from pipeline import run_pipeline, resume_pipeline
from templates import TEMPLATES, list_templates, apply_template


def parse_args():
    parser = argparse.ArgumentParser(
        description="Local AI Multi-Agent Coder Team",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "Build a TODO REST API"
  python main.py --template fastapi "Build a TODO REST API with user auth"
  python main.py --interactive "Build a file converter CLI"
  python main.py --no-run "Generate a React dashboard"
  python main.py --max-fixes 0 "Build a FastAPI CRUD API"
  python main.py --resume my-project-name
  python main.py --resume my-project-name --max-fixes 0
  python main.py --list-templates
        """,
    )
    parser.add_argument("task", nargs="?", help="Coding task description")
    parser.add_argument("--template", "-t", choices=list(TEMPLATES.keys()),
                        default="custom", help="Project template to use")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Pause and ask for approval after each agent")
    parser.add_argument("--no-run", action="store_true",
                        help="Skip auto-run and test step")
    parser.add_argument("--output-dir", "-o", default="output",
                        help="Directory to write generated projects (default: output)")
    parser.add_argument("--list-templates", action="store_true",
                        help="Show available templates and exit")
    parser.add_argument("--max-fixes", type=int, default=3, metavar="N",
                        help="Max fix iterations (default: 3 | 0 = loop until reviewer is satisfied, hard cap 10)")
    parser.add_argument("--resume", metavar="PROJECT",
                        help="Resume fixing an existing project by folder name (reads last REVIEW.md)")
    parser.add_argument("--force", action="store_true",
                        help="With --resume: re-review and fix even if the last review already PASSED")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.list_templates:
        list_templates()
        sys.exit(0)

    print("\n🚀  Local AI Multi-Agent Coder Team  (v3)")
    print("    Powered by Ollama · Qwen3:8b · Qwen2.5-Coder:14b")

    # ── Resume mode ──────────────────────────────────────────
    if args.resume:
        try:
            result = resume_pipeline(
                project_name=args.resume,
                output_dir=args.output_dir,
                interactive=args.interactive,
                auto_run_enabled=not args.no_run,
                max_fix_iterations=args.max_fixes,
                force=args.force,
            )
        except FileNotFoundError as e:
            print(f"\n  ❌  {e}")
            print(f"\n  Available projects in {args.output_dir}/:")
            import os
            try:
                projects = [d for d in os.listdir(args.output_dir)
                            if os.path.isdir(os.path.join(args.output_dir, d))]
                for p in projects:
                    has_review = os.path.exists(os.path.join(args.output_dir, p, "REVIEW.md"))
                    marker = "📋" if has_review else "  "
                    print(f"    {marker}  {p}")
            except FileNotFoundError:
                print(f"    (output dir not found)")
            sys.exit(1)

        _save_summary(result)
        return

    # ── Normal mode ──────────────────────────────────────────
    task = args.task
    if not task:
        if args.template != "custom":
            t = TEMPLATES[args.template]
            print(f"\n📐  Template: {t['name']}")
        task = input("\nEnter your coding task: ").strip()
        if not task:
            print("No task provided. Exiting.")
            sys.exit(1)

    full_prompt = apply_template(args.template, task)

    if args.interactive:
        print("\n🎛️   Interactive mode ON — you will approve each agent's output.")
    if args.no_run:
        print("⏭️   Auto-run disabled.")

    result = run_pipeline(
        task=full_prompt,
        output_dir=args.output_dir,
        interactive=args.interactive,
        auto_run_enabled=not args.no_run,
        max_fix_iterations=args.max_fixes,
    )

    _save_summary(result)


def _save_summary(result: dict):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = f"run_summary_{timestamp}.json"
    with open(summary_file, "w") as f:
        json.dump({
            "task":          result.get("task"),
            "project_path":  result.get("project_path"),
            "files_written": result.get("written_files", []),
            "run_results":   [
                {"label": r["label"], "success": r["success"]}
                for r in result.get("run_results", [])
            ],
        }, f, indent=2)

    print(f"\n{'#'*60}")
    print(f"  ✅  PIPELINE COMPLETE")
    print(f"  📁  Project:  {result.get('project_path')}")
    print(f"  💾  Summary:  {summary_file}")
    print(f"{'#'*60}\n")


if __name__ == "__main__":
    main()
