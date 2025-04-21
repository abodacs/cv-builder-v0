import uvicorn
from fastapi.staticfiles import StaticFiles
from app.web.app import create_app
from app.core.config import Config
import os

# Create static directory if it doesn't exist
if not os.path.exists(Config.STATIC_DIR):
    os.makedirs(Config.STATIC_DIR)

# Create and configure the application
app = create_app()
app.mount("/static", StaticFiles(directory=Config.STATIC_DIR), name="static")

def find_available_port(start_port: int = 8000, max_port: int = 9000) -> int:
    """Find an available port between start_port and max_port."""
    import socket
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No available ports found between {start_port} and {max_port}")

if __name__ == "__main__":
    try:
        port = find_available_port()
        print(f"Starting server on port {port}")
        uvicorn.run(app, host="127.0.0.1", port=port)
    except Exception as e:
        print(f"Failed to start server: {e}")
        exit(1)