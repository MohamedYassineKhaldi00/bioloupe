"""Development runner using Uvicorn.

Run with:
    python run.py
"""

from src.wsgi import application

if __name__ == "__main__":
    try:
        import uvicorn
    except Exception:
        raise SystemExit("Please install dependencies: pip install -r requirements.txt")

    uvicorn.run(application, host="127.0.0.1", port=8000)
