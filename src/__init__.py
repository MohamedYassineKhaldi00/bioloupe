"""Minimal WSGI application factory.

This module provides a tiny WSGI app with a factory function so it can be
imported by WSGI servers (e.g. `wsgi.py` or a production server).
"""

from typing import Callable


def create_app() -> Callable:
    """Return a WSGI application callable.

    The returned callable conforms to the WSGI spec: (environ, start_response) -> iterable
    """

    def application(environ, start_response):
        path = environ.get("PATH_INFO", "/")

        if path == "/":
            status = "200 OK"
            headers = [("Content-Type", "text/plain; charset=utf-8")]
            start_response(status, headers)
            return [b"Hello, world!\n"]

        if path == "/health":
            status = "200 OK"
            headers = [("Content-Type", "application/json; charset=utf-8")]
            start_response(status, headers)
            return [b'{"status": "ok"}\n']

        status = "404 Not Found"
        headers = [("Content-Type", "text/plain; charset=utf-8")]
        start_response(status, headers)
        return [b"Not Found\n"]

    application.__name__ = "minimal_wsgi_app"
    return application
