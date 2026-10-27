import os
import sys
from pathlib import Path
from waitress import serve
from app import create_app

app = create_app(os.getenv("FLASK_ENV", "production"))

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    threads = int(os.getenv("WAITRESS_THREADS", 6))

    print("=" * 64)
    print("  PLAYLISTPILOT — Production Server (Powered by Waitress WSGI)")
    print(f"  Bound to: http://{host}:{port}")
    print(f"  Worker Threads: {threads}")
    print("  Status: Active & Serving Requests")
    print("=" * 64)

    serve(app, host=host, port=port, threads=threads)
