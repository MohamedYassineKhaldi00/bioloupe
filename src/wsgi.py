from . import create_app

# Expose the WSGI callable for servers to import
application = create_app()
