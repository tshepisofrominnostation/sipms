# wsgi.py — Production entry point for Gunicorn (Railway / Render)
#
# Gunicorn is the production WSGI server that handles concurrent requests
# via multiple worker processes. Flask's built-in app.run() is single-threaded
# and only suitable for local development.
#
# Railway auto-injects $PORT. The start command in nixpacks.toml is:
#   gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2

from app import app

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
