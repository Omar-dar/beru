"""CORS for beru-ui: browser dev, Netlify, Capacitor, Electron."""

from flask_cors import CORS

from src.api_contract import cors_origins


def init_cors(app):
    origins = cors_origins()
    if '*' in origins:
        CORS(
            app,
            resources={r'/*': {'origins': '*'}},
            allow_headers=['Content-Type', 'X-Beru-Session-Id', 'Authorization'],
            methods=['GET', 'POST', 'OPTIONS'],
            supports_credentials=False,
        )
        return
    CORS(
        app,
        resources={r'/*': {'origins': origins}},
        allow_headers=['Content-Type', 'X-Beru-Session-Id', 'Authorization'],
        methods=['GET', 'POST', 'OPTIONS'],
        supports_credentials=False,
    )
