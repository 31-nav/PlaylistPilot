import os
import sys

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure Node.js is always in PATH
if r"C:\Program Files" not in os.environ.get("PATH", ""):
    os.environ["PATH"] = r"C:\Program Files;" + os.environ.get("PATH", "")

from app import create_app

app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    print("=" * 64)
    print("  PLAYLISTPILOT — Smart Playlist & Batch Job Manager")
    print("  Status: Operational (Local First)")
    print("  Web Server: http://127.0.0.1:5000")
    print("  Demonstration Mode: Ready (105-item educational playlist)")
    print("=" * 64)
    app.run(host="127.0.0.1", port=5000, debug=False)
