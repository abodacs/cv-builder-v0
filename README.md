# 🚀 AI-Powered CV Builder

A modern, real-time CV builder that leverages LangGraph and FastAPI to create professional CVs through an intuitive chat interface.

## 📖 Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Contributing](#contributing)
- [License](#license)

## ✨ Features

- 🤖 Interactive chatbot interface for CV creation  
- 📝 Step-by-step guided process  
- 🔄 Real-time state management with Redis  
- 📊 LangGraph-powered conversation flow  
- 📄 PDF generation with ReportLab  
- 🌐 WebSocket-based real-time communication  

## 🏗️ Architecture

- **Frontend:** Pure JavaScript with WebSocket communication  
- **Backend:** FastAPI + WebSockets  
- **State Management:** Redis  
- **PDF Generation:** ReportLab  
- **Conversation Flow:** LangGraph  
- **Language Model:** OpenAI GPT-4  

## 🚀 Quick Start

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd cv-builder-v0
   ```
2. **Install dependencies:**  
   (Using uv – Ultra-fast Python package installer)
   ```bash
   uv sync
   pre-commit install
   ```
3. **Setup Code Quality Tools:**
   ```bash
   # Ruff and pre-commit hooks will run automatically on commits
   # Manual run
   pre-commit run --all-files
   ```
4. **Start Redis server:**
   ```bash
   ./redis.sh
   ```
5. **Set your OpenAI API key:**
   ```bash
   echo "OPENAI_API_KEY=your-key-here" > .env
   ```
6. **Run the application:**
   ```bash
   uv run fastapi dev
   ```

## 📁 Project Structure

```
.
├── app/
│   ├── core/                          # Core application components
│   │   ├── config.py                  # Environment and app configuration
│   │   ├── constants.py               # Global constants and enums
│   │   └── state.py                   # CV state management
│   ├── handlers/                      # CV section handlers
│   │   ├── education.py               # Education section logic
│   │   ├── experience.py              # Work experience handler
│   │   ├── finalize.py                # CV finalization and export
│   │   ├── personal_info.py           # Personal details handler
│   │   └── skills.py                  # Skills section processor
│   ├── services/                      # External services integration
│   │   ├── pdf.py                     # PDF generation service
│   │   ├── redis_store.py             # Redis state management
│   │   └── workflow.py                # LangGraph workflow engine
│   ├── utils/                         # Utility functions
│   │   └── text.py                    # Text processing helpers
│   ├── web/                           # Web interface components
│   │   ├── app.py                     # FastAPI application
│   │   ├── templates.py               # HTML templates
│   │   └── websocket.py               # WebSocket handlers
│   └── main.py                        # Application entry point
├── static/
│   └── fonts/                         # PDF generation fonts
├── Dockerfile                         # Container configuration
├── pyproject.toml                     # Project dependencies
├── redis.sh                           # Redis startup script
├── ruff.toml                          # Ruff linter config
├── uv.lock                            # UV dependency lock
└── README.md                          # Project documentation
```

## 🛠️ Tech Stack

- Python 3.12
- FastAPI
- LangGraph
- OpenAI GPT-4
- Redis
- ReportLab
- WebSockets
- Docker

## 🤝 Contributing

Contributions are welcome! Please submit issues and pull requests.

## 📝 License

This project is MIT licensed.