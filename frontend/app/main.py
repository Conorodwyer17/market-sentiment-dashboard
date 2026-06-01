import os

import dash
import dash_bootstrap_components as dbc

from app.layout import make_layout
import app.callbacks  # noqa: F401 — registers all callbacks

# Resolve assets relative to this file so CSS is found whether we run
# via `python -m app.main` (CWD=/app) or directly (CWD=/app/app).
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

server_app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    title="Market Sentiment Dashboard",
    suppress_callback_exceptions=True,
    assets_folder=_ASSETS_DIR,
)

server_app.layout = make_layout()

# Expose WSGI server for gunicorn / production use
server = server_app.server

if __name__ == "__main__":
    server_app.run(host="0.0.0.0", port=8050, debug=False)
