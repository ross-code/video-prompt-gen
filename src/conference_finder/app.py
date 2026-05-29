"""Flask web app for the Conference Finder."""

from __future__ import annotations

import os

from flask import Flask, jsonify, render_template, request

from .finder import FinderError, Profile, find_conferences
from .storage import load_state, save_state


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        state = load_state()
        return render_template(
            "index.html",
            profile=state["profile"],
            conferences=state["conferences"],
            last_updated=state["last_updated"],
        )

    @app.get("/api/conferences")
    def api_conferences():
        state = load_state()
        return jsonify(
            conferences=state["conferences"],
            last_updated=state["last_updated"],
            profile=state["profile"],
        )

    @app.post("/api/refresh")
    def api_refresh():
        payload = request.get_json(silent=True) or {}
        profile = Profile.from_dict(payload)
        try:
            months = int(payload.get("months", 6))
        except (TypeError, ValueError):
            months = 6
        months = max(1, min(months, 12))

        try:
            conferences = find_conferences(profile, months=months)
            last_updated = save_state(profile.to_dict(), conferences)
        except FinderError as exc:
            return jsonify(error=str(exc)), 400
        except Exception as exc:  # never return an HTML 500 page to a JSON client
            app.logger.exception("Unexpected error during /api/refresh")
            return jsonify(error=f"Unexpected error: {exc}"), 500

        return jsonify(conferences=conferences, last_updated=last_updated, months=months)

    return app


def main() -> None:
    app = create_app()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    print(f"Conference Finder running at http://{host}:{port}")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("  Warning: ANTHROPIC_API_KEY is not set — refresh will fail until you set it.")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
