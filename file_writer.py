# file_writer.py

import os
import json
import re


def extract_json(text: str) -> dict:
    """Robustly extract a JSON object from the model's response."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text.strip(), flags=re.MULTILINE)
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in model response.")
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parse error: {e}")


def write_project(coder_output: str, base_dir: str = "output") -> tuple[str, list[str]]:
    """Parse coder JSON and write files to disk. Returns (project_path, written_files)."""
    data = extract_json(coder_output)
    project_name = data.get("project_name", "project").strip().replace(" ", "-")
    files = data.get("files", [])

    if not files:
        raise ValueError("Coder returned no files.")

    project_path = os.path.join(base_dir, project_name)
    written_files = []

    for entry in files:
        relative_path = entry.get("path", "").strip()
        content = entry.get("content", "")
        if not relative_path:
            continue
        full_path = os.path.join(project_path, relative_path)
        os.makedirs(os.path.dirname(full_path) or project_path, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        written_files.append(full_path)
        print(f"  📄  {full_path}")

    return project_path, written_files
