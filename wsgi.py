# WSGI entrypoint for Gunicorn/production servers
""" WSGI application factory """
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app import app, socketio

# For Gunicorn
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
