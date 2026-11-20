"""Production WSGI entry point. Set environment variables before importing."""

from counter.database import initialize
from counter.wsgi import application

initialize()
