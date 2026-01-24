# Minimal Python WSGI Backend 🔧

A bare-bones WSGI backend skeleton with a tiny app and a development runner.

Quickstart

1. Create a virtual environment and install deps:

```bash
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

2. Run the dev server:

```bash
python run.py
```

3. Test endpoints:

- http://127.0.0.1:8000/        -> "Hello, world!"
- http://127.0.0.1:8000/health  -> {"status": "ok"}

Testing

This project includes a minimal test that exercises the WSGI callable without external libs.
Run tests with pytest (install `pytest` if you want to use it).
