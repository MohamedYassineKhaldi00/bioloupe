"""Development runner using `waitress` (a simple WSGI server).

Run with:
    python run.py

It will listen on 127.0.0.1:8000 by default.
"""

from src.wsgi import application

if __name__ == "__main__":
    try:
        from waitress import serve
    except Exception:
        raise SystemExit("Please install dependencies: pip install -r requirements.txt")

    serve(application, host="127.0.0.1", port=8000)
