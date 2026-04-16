# templates.py
# Pre-built task prompts that guide the Architect toward a known structure.

TEMPLATES = {
    "fastapi": {
        "name": "FastAPI REST API",
        "description": "Python REST API with FastAPI, Pydantic models, SQLite via SQLAlchemy, and pytest tests.",
        "prompt": """Create a production-ready FastAPI REST API project with:
- App entry point at src/main.py
- Pydantic schemas in src/schemas.py
- SQLAlchemy models in src/models.py
- Database session handling in src/database.py
- Route handlers separated by resource in src/routers/
- pytest tests in tests/
- requirements.txt with fastapi, uvicorn, sqlalchemy, pydantic, pytest, httpx
- README.md with setup and usage instructions
- .env.example for configuration
Task: {user_task}""",
    },

    "express": {
        "name": "Express.js REST API",
        "description": "Node.js REST API with Express, middleware, and Jest tests.",
        "prompt": """Create a production-ready Express.js REST API project with:
- Entry point at src/index.js
- Routes in src/routes/
- Middleware in src/middleware/
- Controllers in src/controllers/
- Jest tests in tests/
- package.json with express, dotenv, jest, supertest
- README.md with setup and usage instructions
- .env.example for configuration
Task: {user_task}""",
    },

    "react": {
        "name": "React Frontend App",
        "description": "React app with components, hooks, and basic styling.",
        "prompt": """Create a React frontend application with:
- Entry point at src/index.jsx
- App component at src/App.jsx
- Reusable components in src/components/
- Custom hooks in src/hooks/
- CSS modules in src/styles/
- package.json with react, react-dom, vite
- vite.config.js
- index.html
- README.md with setup and usage instructions
Task: {user_task}""",
    },

    "python-cli": {
        "name": "Python CLI Tool",
        "description": "Command-line tool with argparse, modular structure, and pytest tests.",
        "prompt": """Create a Python CLI tool project with:
- Entry point at src/main.py using argparse
- Core logic modules in src/
- Utility helpers in src/utils.py
- pytest tests in tests/
- requirements.txt
- setup.py or pyproject.toml for installability
- README.md with usage examples
Task: {user_task}""",
    },

    "discord-bot": {
        "name": "Discord Bot",
        "description": "Python Discord bot with commands, events, and a config system.",
        "prompt": """Create a Discord bot project with:
- Entry point at bot/main.py
- Slash commands in bot/commands/
- Event handlers in bot/events/
- Config loader in bot/config.py using .env
- requirements.txt with discord.py, python-dotenv
- .env.example
- README.md with setup instructions and how to invite the bot
Task: {user_task}""",
    },

    "python-scraper": {
        "name": "Python Web Scraper",
        "description": "Web scraper with requests/BeautifulSoup, data export, and error handling.",
        "prompt": """Create a Python web scraper project with:
- Entry point at src/main.py
- Scraper logic in src/scraper.py
- Data parser in src/parser.py
- CSV/JSON exporter in src/exporter.py
- requirements.txt with requests, beautifulsoup4, lxml
- pytest tests in tests/
- README.md
Task: {user_task}""",
    },

    "custom": {
        "name": "Custom",
        "description": "No template — describe your project freely.",
        "prompt": "{user_task}",
    },
}


def list_templates():
    print("\n📐  Available Templates:\n")
    for key, t in TEMPLATES.items():
        print(f"  [{key}]  {t['name']}")
        print(f"          {t['description']}\n")


def apply_template(template_key: str, user_task: str) -> str:
    t = TEMPLATES.get(template_key, TEMPLATES["custom"])
    return t["prompt"].replace("{user_task}", user_task)
