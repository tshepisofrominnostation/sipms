# wsgi.py — entry point for Gunicorn on Render.com
#
# Gunicorn (Green Unicorn) is the production WSGI server.
# It handles multiple simultaneous requests by running
# multiple worker processes. Never use Flask's built-in
# server (app.run) in production — it can only handle
# one request at a time.
#
# Render.com looks for 'app' in this file via:
#   gunicorn wsgi:app

from app import app

if __name__ == '__main__':
    app.run()
