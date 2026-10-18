import os
import sys
import traceback

# Ensure project root is in Python sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from main import app
except Exception as e:
    err_tb = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    app = FastAPI(title="Newton Vercel Diagnostic")

    @app.get("/{path:path}", response_class=HTMLResponse)
    async def diag_root(path: str = ""):
        return HTMLResponse(
            f"<html><body style='background:#0d1117;color:#c9d1d9;font-family:sans-serif;padding:32px;'>"
            f"<h2 style='color:#f85149;'>⚠️ Newton Platform Vercel Boot Exception</h2>"
            f"<p>The application encountered an error during startup on Vercel:</p>"
            f"<pre style='background:#161b22;padding:16px;border-radius:6px;overflow:auto;color:#ff7b72;border:1px solid #30363d;'>{err_tb}</pre>"
            f"</body></html>",
            status_code=500
        )
