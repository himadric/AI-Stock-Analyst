import traceback
try:
    from main import app
except Exception:
    # Fallback to display import errors
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse
    app = FastAPI()
    
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    def catch_all(path: str):
        error_msg = traceback.format_exc()
        return PlainTextResponse(f"Backend Import Error:\n{error_msg}", status_code=500)
