"""Serve the installable notes PWA at /app."""
import os

from flask import Blueprint, current_app, make_response, render_template, send_from_directory, jsonify

from app.main_page_module.other import Randoms

pwa_module = Blueprint('pwa_module', __name__, url_prefix='/app')

_PWA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'static', 'pwa')
PWA_DIR = os.path.normpath(_PWA_DIR)
_STATIC_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'static'))

# HTML revalidates when online, but can be reused if the server is unreachable.
_SHELL_CACHE = 'public, max-age=600, stale-while-revalidate=86400, stale-if-error=604800'
_ASSET_CACHE = 'public, max-age=86400, stale-while-revalidate=604800, stale-if-error=604800'


def _with_cache(response, value):
    response.headers['Cache-Control'] = value
    return response


@pwa_module.route('/sw.js')
def service_worker():
    response = send_from_directory(PWA_DIR, 'sw.js')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Service-Worker-Allowed'] = '/app/'
    return response


@pwa_module.route('/icon.ico')
def icon():
    """Serve the same instance favicon the webapp uses (ICON_COLOR)."""
    return _with_cache(
        send_from_directory(_STATIC_DIR, Randoms.icon_name(current_app.config)),
        _ASSET_CACHE
    )


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
        "id": "/app/",
        "icons": [
            {
                "src": "/app/icon.ico",
                "sizes": "any",
                "type": "image/x-icon",
                "purpose": "any"
            }
        ]
    })
    resp.mimetype = 'application/manifest+json'
    return _with_cache(resp, _SHELL_CACHE)


@pwa_module.route('/assets/<path:filename>')
def assets(filename):
    return _with_cache(send_from_directory(PWA_DIR, filename), _ASSET_CACHE)


@pwa_module.route('/')
@pwa_module.route('/<path:path>')
def spa(path=None):
    return _with_cache(make_response(render_template('pwa/index.html')), _SHELL_CACHE)
