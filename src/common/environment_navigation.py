"""Navigation entre applications et suppression des sessions locales."""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from flask import Blueprint, Flask, abort, redirect, render_template, request, session, url_for
from flask.typing import ResponseReturnValue
from jinja2 import ChoiceLoader, FileSystemLoader
from sqlalchemy import update
from sqlalchemy.orm import Session
from werkzeug import Response
from werkzeug.middleware.proxy_fix import ProxyFix

from common.models.users import UserSession


@dataclass(frozen=True)
class Environment:
    """Destination autorisée du répartiteur."""

    name: str
    title: str
    prefix: str
    arrival_endpoint: str


ENVIRONMENTS = (
    Environment("dashboard", "Gestion", "/gestion", "dashboard.login"),
    Environment("production", "Production", "/production", "production.select_press"),
    Environment("manutention", "Manutention", "/manutention", "manutention.login"),
    Environment("qualite", "Qualité", "/qualite", "qualite.login"),
    Environment("techniciens", "Techniciens", "/techniciens", "techniciens.login"),
)


def clear_environment_session(
    auth_session_factory: Callable[[], Session] | None = None,
) -> None:
    """Révoque le jeton courant avant de supprimer la session Flask.

    Args:
        auth_session_factory: Fabrique de sessions de la base d'authentification,
            si l'environnement utilise des jetons révocables.
    """
    token_hash = session.get("token_hash")
    if auth_session_factory is not None and isinstance(token_hash, str):
        with auth_session_factory() as database_session:
            database_session.execute(
                update(UserSession)
                .where(
                    UserSession.token_hash == token_hash,
                    UserSession.revoked_at.is_(None),
                )
                .values(revoked_at=datetime.now(timezone.utc))
            )
            database_session.commit()
    session.clear()


def register_environment_navigation(flask_app: Flask, environment_name: str) -> None:
    """Installe la navigation, les cookies isolés et le parcours de déconnexion.

    Args:
        flask_app: Application dont les bases et la protection CSRF sont configurées.
        environment_name: Identifiant d'un environnement du registre fermé.
    """
    environment = next(item for item in ENVIRONMENTS if item.name == environment_name)
    common_directory = Path(__file__).resolve().parent
    common_loader = FileSystemLoader(str(common_directory / "templates"))
    local_loader = flask_app.jinja_loader
    flask_app.jinja_loader = (
        ChoiceLoader([local_loader, common_loader]) if local_loader else common_loader
    )
    flask_app.config.update(
        SESSION_COOKIE_NAME=f"{environment.name}_session",
        SESSION_COOKIE_PATH=environment.prefix,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
    )
    if os.environ.get("TRUST_PROXY_HEADERS", "0") == "1":
        flask_app.wsgi_app = ProxyFix(flask_app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    blueprint = Blueprint(
        "environment_navigation",
        __name__,
        url_prefix=environment.prefix,
        static_folder="static",
        static_url_path="/navigation-assets",
    )

    @blueprint.post("/changer-environnement")
    def change_environment() -> Response:
        target_name = request.form.get("environment", "")
        target = next((item for item in ENVIRONMENTS if item.name == target_name), None)
        if target is None or target.name == environment.name:
            abort(400, description="Environnement de destination invalide.")
        clear_environment_session(flask_app.extensions.get("auth_session_factory"))
        return redirect(f"{target.prefix}/entree", code=303)

    @blueprint.route("/entree", methods=("GET", "POST"))
    def enter_environment() -> ResponseReturnValue:
        if request.method == "GET":
            return render_template("environment_entry.html")
        clear_environment_session(flask_app.extensions.get("auth_session_factory"))
        return redirect(url_for(environment.arrival_endpoint), code=303)

    @flask_app.context_processor
    def navigation_context() -> dict[str, object]:
        return {"current_environment": environment, "environments": ENVIRONMENTS}

    @flask_app.after_request
    def protect_navigation_response(response: Response) -> Response:
        if not (request.endpoint or "").endswith("static"):
            response.headers["Cache-Control"] = "no-store"
        cookie_name = flask_app.config["SESSION_COOKIE_NAME"]
        if cookie_name in request.cookies:
            session.modified = True
            response.delete_cookie(cookie_name, path="/")
        if "session" in request.cookies:
            response.delete_cookie("session", path="/")
        return response

    flask_app.register_blueprint(blueprint)
