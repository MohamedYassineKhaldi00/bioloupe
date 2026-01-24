"""Minimal tests for the WSGI app (uses stdlib only).

Run with pytest or any test runner that discovers tests under `tests/`.
"""

import io
from app import create_app


def make_environ(path="/"):
    return {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "SERVER_NAME": "test",
        "SERVER_PORT": "80",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(b""),
        "wsgi.errors": io.StringIO(),
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }


def start_response_collector(collected):
    def start_response(status, headers):
        collected["status"] = status
        collected["headers"] = headers
    return start_response


def test_root_response():
    app = create_app()
    collected = {}
    start = start_response_collector(collected)

    body = b"".join(app(make_environ('/'), start))

    assert collected["status"].startswith("200")
    assert b"Hello" in body


def test_not_found():
    app = create_app()
    collected = {}
    start = start_response_collector(collected)

    _ = b"".join(app(make_environ('/nope'), start))

    assert collected["status"].startswith("404")
