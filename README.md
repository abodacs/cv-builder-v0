# 🚀 AI-Powered CV Builder

A modern, real-time CV builder that leverages LangGraph and FastAPI to create professional CVs through an intuitive chat interface.

## 📖 Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Code Highlights](#code-highlights)
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

## 💡 Code Highlights

### Conversation Flow with LangGraph
```py
workflow = StateGraph(CVState)
workflow.add_node("process_input", process_input)
workflow.add_node("generate_prompt", generate_prompt)
workflow.set_entry_point("process_input")
```
*Manages the conversation flow covering sections such as Personal Information, Education, Work Experience, Skills, and Review & Generation.*

### Real-time State Management (Redis)
```py
def save_state(session_id: str, state: CVState):
    redis_client.setex(f"cv_session:{session_id}", 3600, json.dumps(state.dict()))
```

### WebSocket Communication
```py
@app.websocket("/ws/cv_builder")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Real-time message handling
```

## 📁 Project Structure

```
.
├── app/
│   ├── __init__.py
│   └── main.py          // Main application logic
├── static/              // Generated PDFs
├── Dockerfile
├── pyproject.toml       // Dependencies
├── redis.sh            // Redis startup script
└── README.md
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