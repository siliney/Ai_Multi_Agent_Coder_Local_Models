# chunker.py
# Splits large projects into multiple Coder passes to avoid context window limits.

import ollama
from agents import AGENTS


def estimate_file_count(architecture: str) -> int:
    """Rough estimate of file count from the architect's output."""
    lines = architecture.lower().split("\n")
    extensions = [
        ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rb",
        ".html", ".css", ".json", ".yaml", ".yml", ".toml",
        ".sh", ".md", ".sql", ".env",
    ]
    count = sum(
        1 for line in lines
        if any(ext in line for ext in extensions)
    )
    return max(count, 1)


def build_chunk_prompts(task: str, architecture: str, files_per_chunk: int = 6) -> list[str]:
    """
    Ask the Architect to divide the file list into chunks,
    then return one prompt per chunk for the Coder.
    """
    agent = AGENTS["architect"]
    division_prompt = f"""Given this implementation plan:

{architecture}

Divide the files into groups of at most {files_per_chunk} files per group.
List each group as:
CHUNK 1: file1.py, file2.py, ...
CHUNK 2: file3.py, file4.py, ...
Only list filenames. No explanations."""

    print("  🧩  Dividing project into chunks...")
    try:
        response = ollama.chat(
            model=agent["model"],
            messages=[
                {"role": "system", "content": agent["system"]},
                {"role": "user",   "content": division_prompt},
            ],
            options=agent.get("options", {}),   # must match architect options — no stray defaults
        )
        division = response["message"]["content"]
    except Exception as e:
        print(f"  ⚠️  Chunk division failed ({e}) — falling back to single chunk.")
        return [f"Implement the full project.\n\nTASK:\n{task}\n\nPLAN:\n{architecture}"]

    # Parse chunks from the architect's response
    chunks = []
    for line in division.split("\n"):
        line = line.strip()
        if line.upper().startswith("CHUNK"):
            files_part = line.split(":", 1)[-1].strip()
            chunks.append(files_part)

    if not chunks:
        # Fallback: treat everything as one chunk
        return [f"Implement the full project.\n\nTASK:\n{task}\n\nPLAN:\n{architecture}"]

    prompts = []
    total = len(chunks)
    for i, chunk_files in enumerate(chunks):
        prompt = (
            f"Implement CHUNK {i+1} of {total} for this project.\n\n"
            f"FILES TO IMPLEMENT IN THIS CHUNK:\n{chunk_files}\n\n"
            f"ORIGINAL TASK:\n{task}\n\n"
            f"FULL ARCHITECTURAL PLAN:\n{architecture}\n\n"
            f"Set chunk_index to {i} and total_chunks to {total} in your JSON response.\n"
            f"{'Include README.md in this chunk.' if i == 0 else 'Do NOT repeat README.md.'}"
        )
        prompts.append(prompt)

    return prompts


CHUNK_THRESHOLD = 8   # files — use chunking above this estimate
FILES_PER_CHUNK = 6   # max files per Coder pass
