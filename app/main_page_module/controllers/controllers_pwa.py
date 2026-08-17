"""Serve the installable notes PWA at /app."""
import os

from flask import Blueprint, current_app, render_template, send_from_directory, jsonify

pwa_module = Blueprint('pwa_module', __name__, url_prefix='/app')

_PWA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'static', 'pwa')
PWA_DIR = os.path.normpath(_PWA_DIR)


@pwa_module.route('/sw.js')
def service_worker():
    response = send_from_directory(PWA_DIR, 'sw.js')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Service-Worker-Allowed'] = '/app/'
    return response


@pwa_module.route('/manifest.webmanifest')
def manifest():
    name = current_app.config.get('APP_NAME', 'Razor Notes')
    resp = jsonify({
        "name": name,
        "short_name": name,
        "description": "Offline-capable notes for this Razor Notes server.",
        "start_url": "/app/",
        "scope": "/app/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#fff8d6",
        "theme_color": "#212529",
        "icons": [
            {
                "src": "/app/assets/icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/app/assets/icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/app/assets/icons/icon.svg",
                "sizes": "any",
                "type": "image/svg+xml",
                "purpose": "any"
            }
        ]
    })
    resp.mimetype = 'application/manifest+json'
    return resp


@pwa_module.route('/assets/<path:filename>')
def assets(filename):
    return send_from_directory(PWA_DIR, filename)


@pwa_module.route('/')
@pwa_module.route('/<path:path>')
def spa(path=None):
    return render_template('pwa/index.html')
