# 🤖 Local AI Multi-Agent Coder Team

A fully local, offline multi-agent pipeline that takes a plain-English coding task and delivers a working project — no API keys, no cloud, everything runs on your own hardware.

```
Your Task
   ↓
🏛️  Architect   (qwen3:8b)        — designs the plan & file structure
   ↓
💻  Coder       (qwen2.5-coder:14b) — writes all the code as structured JSON
   ↓
▶️  Runner                         — installs deps & runs tests automatically
   ↓
🔍  Reviewer    (qwen2.5-coder:14b) — audits the code for bugs & issues
   ↓ (NEEDS REVISION)
🔧  Fixer       (qwen2.5-coder:14b) — patches only the files that need changes
   ↓ (loops until PASS or cap reached)
📁  output/<project>/              — your finished project lands here
```

---

## Features

| Feature | Description |
|---|---|
| 🏛️ Architect agent | Produces a structured plan, file tree, and implementation steps |
| 💻 Coder agent | Writes complete files as JSON — no truncation |
| 🧩 Chunked output | Large projects split across multiple Coder passes |
| ▶️ Auto-run & test | Generated code is installed and tested automatically |
| 🔍 Reviewer agent | Reads actual file contents — not just filenames |
| 🔧 Fix loop | Reviewer → Fixer loops until PASS or cap reached |
| 📋 Resume | Pick up any stopped pipeline from its last `REVIEW.md` |
| 🎛️ Interactive mode | Approve or reject each agent's output manually |
| 📐 Project templates | FastAPI, Express, React, Python CLI, Discord bot, and more |

---

## Requirements

- Python 3.9+
- [Ollama](https://ollama.com) installed and running
- The two models pulled (see Step 1)
- At least 16 GB RAM (the 14B model needs ~9 GB on its own)

---

## Step 1 — Install Ollama & Pull Models

### Windows
Download and install from: https://ollama.com/download/windows

### macOS
```bash
brew install ollama
```

### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Pull the models
Run these in a terminal. Ollama must be running first.

```bash
# Make sure Ollama is running (Windows: it starts automatically as a service)
# macOS/Linux: run `ollama serve` in a separate terminal

ollama pull qwen3:8b
ollama pull qwen2.5-coder:14b
```

> **Note:** `qwen3:8b` is ~5 GB, `qwen2.5-coder:14b` is ~9 GB. Make sure you have enough disk space.

---

## Step 2 — Clone & Install

```bash
git clone https://github.com/siliney/Ai_Multi_Agent_Coder_Local_Models.git
cd Ai_Multi_Agent_Coder_Local_Models

pip install ollama
```

That's the only Python dependency.

---

## Step 3 — Run

Make sure Ollama is running, then:

```bash
python main.py "Build a URL shortener with a SQLite backend"
```

Generated projects appear in the `output/` folder.

---

## Usage

### Basic
```bash
python main.py "Build a TODO REST API"
```

### Use a project template
```bash
# See all templates
python main.py --list-templates

# FastAPI backend
python main.py --template fastapi "Build a task manager API with user authentication"

# Express.js backend
python main.py --template express "Build a blog API with posts and comments"

# React frontend
python main.py --template react "Build a weather dashboard with a 5-day forecast"

# Python CLI tool
python main.py --template python-cli "Build a CSV data cleaner"

# Discord bot
python main.py --template discord-bot "Build a trivia quiz bot"

# Python web scraper
python main.py --template python-scraper "Scrape product prices from a site"
```

### Control the fix loop
```bash
# Default — up to 3 Reviewer → Fixer rounds
python main.py "Build a FastAPI CRUD API"

# Keep looping until the Reviewer says PASS (hard cap: 10)
python main.py --max-fixes 0 "Build a FastAPI CRUD API"

# Custom cap
python main.py --max-fixes 6 "Build a FastAPI CRUD API"
```

### Resume a stopped pipeline
When a run stops early (hit the cap or convergence), the terminal prints:
```
⚠️  Reached --max-fixes limit (3). Stopping.
     Resume with: python main.py --resume my-project-name
```

```bash
# Resume — continues the fix loop from the last REVIEW.md
python main.py --resume my-project-name

# Resume with unlimited fix rounds
python main.py --resume my-project-name --max-fixes 0

# Force re-review even if last run already passed
python main.py --resume my-project-name --force

# List available projects (shows 📋 next to ones with a REVIEW.md)
python main.py --resume ???
```

### Other flags
```bash
# Skip auto-install and test step
python main.py --no-run "Generate a React dashboard"

# Write project to a custom folder
python main.py --output-dir ~/projects "Build a Telegram bot"

# Interactive mode — approve each agent's output before it continues
python main.py --interactive "Build a file converter CLI"
```

### Combine flags
```bash
python main.py --template fastapi --max-fixes 0 --output-dir ~/dev "Build a file upload API"
python main.py --resume my-project --force --max-fixes 0 --no-run
```

---

## All Flags

| Flag | Default | Description |
|---|---|---|
| `task` | — | Plain-English description of what to build |
| `--template` / `-t` | `custom` | Project template: `fastapi` `express` `react` `python-cli` `discord-bot` `python-scraper` |
| `--max-fixes N` | `3` | Max Reviewer → Fixer iterations. `0` = loop until PASS (hard cap 10) |
| `--resume PROJECT` | — | Resume from the last `REVIEW.md` of an existing project |
| `--force` | off | With `--resume`: re-review even if the last run already PASSED |
| `--no-run` | off | Skip auto-install and test step |
| `--output-dir` / `-o` | `output` | Where generated projects are written |
| `--interactive` / `-i` | off | Pause and approve after each agent |
| `--list-templates` | — | Print available templates and exit |

---

## Output Structure

```
output/
└── my-project/
    ├── src/
    │   ├── main.py
    │   └── ...
    ├── tests/
    │   └── test_main.py
    ├── requirements.txt
    ├── README.md
    └── REVIEW.md        ← reviewer feedback + auto-run results
```

`REVIEW.md` contains:
- ✅ What the reviewer liked
- ⚠️ Issues found with file and line references
- 🔧 Suggested improvements
- 🏁 Overall verdict: `PASS` / `PASS WITH NOTES` / `NEEDS REVISION`
- ▶️ Auto-run results (install output + test results)

---

## Project Structure

```
Ai_Multi_Agent_Coder_Local_Models/
├── agents.py        — Model assignments, system prompts, and options for each agent
├── templates.py     — Built-in project templates and prompt helpers
├── chunker.py       — Splits large projects into multiple Coder passes
├── runner.py        — Auto-detects project type, installs deps, runs tests
├── file_writer.py   — Parses JSON from Coder/Fixer and writes files to disk
├── pipeline.py      — Orchestrator: ties all agents together, fix loop, resume logic
└── main.py          — CLI entry point
```

---

## Agent Configuration

All agents are configured in `agents.py`. You can swap models or tune settings there:

```python
AGENTS = {
    "architect": { "model": "qwen3:8b",           ... },  # planner
    "coder":     { "model": "qwen2.5-coder:14b",  ... },  # code writer
    "reviewer":  { "model": "qwen2.5-coder:14b",  ... },  # code auditor
    "fixer":     { "model": "qwen2.5-coder:14b",  ... },  # bug fixer
}
```

Each agent has an `options` block for Ollama settings:

| Option | Purpose |
|---|---|
| `temperature` | Low (0.2) for code agents = reliable JSON; higher (0.6) for planner = creativity |
| `num_ctx` | Context window size. Keep conservative — large values stall on low RAM |
| `num_predict` | Max tokens to generate. Set high for Coder/Fixer so files aren't truncated |
| `repeat_penalty` | Discourages copy-paste repetition in generated code |

---

## Troubleshooting

**Architect stage hangs / never finishes**
- Ollama may be loading the model for the first time — wait up to 60 seconds
- Check `num_ctx` in `agents.py` — values above 8192 can stall on machines with < 24 GB RAM
- Run `ollama ps` in another terminal to confirm the model is loaded

**`Connection refused` error**
- Ollama is not running. On Windows it usually starts automatically; check the system tray
- macOS/Linux: run `ollama serve` in a separate terminal

**JSON parse errors from Coder or Fixer**
- Re-run the task — model outputs are non-deterministic
- Use `--interactive` to catch bad outputs and retry them on the spot
- Add to your task: *"Respond with ONLY the raw JSON object. No extra text."*

**Model swap pause between Architect and Coder**
- Normal — Ollama unloads `qwen3:8b` and loads `qwen2.5-coder:14b`. Takes 10–30 seconds depending on RAM

**Tests fail in auto-run**
- Expected occasionally. Check `REVIEW.md` for the reviewer's analysis
- Use `--resume <project> --max-fixes 0` to keep fixing until tests pass

**Very large projects still get truncated**
- Lower `FILES_PER_CHUNK` in `chunker.py` from `6` to `4`
- Or break the task into smaller independent features and run the pipeline multiple times

---

## Tips for Best Results

- **Be specific** — *"Build a FastAPI CRUD API for a book library with title, author, ISBN fields and SQLite storage"* works much better than *"Build an API"*
- **Use templates** — they steer the Architect toward a consistent, well-structured layout
- **Use `--max-fixes 0`** for important projects so the loop runs until the reviewer is satisfied
- **Use `--resume --force`** to get a second opinion on code that already passed
- **Use `--no-run`** for frontend-only or non-executable projects (React, config files, docs)
- **Chain runs** — generate a backend first, then run again for the frontend, pointing both to the same `--output-dir`

---

## License

MIT — do whatever you want with it.
