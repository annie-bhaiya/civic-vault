import socket
import threading
import uvicorn
import webview
from app.main import app

def get_free_port():
    """Finds an available, unused port on the user's machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def run_server(port):
    """Runs the FastAPI backend silently."""
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="critical")

if __name__ == '__main__':
    # 1. Grab a free port
    port = get_free_port()
    
    # 2. Start the backend server on a separate thread
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()
    
    # 3. Open the native OS window pointing to our local server
    webview.create_window(
        title='Civic Vault', 
        url=f'http://127.0.0.1:{port}', 
        width=1280, 
        height=800,
        min_size=(1024, 768)
    )
    
    # 4. Start the native UI loop
    webview.start()