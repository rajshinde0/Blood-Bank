"""
WSGI entry point for production servers.

Flask-SocketIO wraps app.wsgi_app when the extension is initialised, so
handing `app` to gunicorn is enough - provided gunicorn runs a
WebSocket-capable worker:

    gunicorn --worker-class eventlet --workers 1 wsgi:app
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, socketio  # noqa: E402  (path must be set first)

__all__ = ['app', 'socketio']

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
