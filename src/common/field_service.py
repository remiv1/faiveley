"""Socle Flask des applications terrain traitant des demandes liées aux postes."""

import os
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Callable, NoReturn, ParamSpec, Sequence

from flask import (
    Blueprint,
    Flask,
    Response,
    abort,
    current_app,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask.typing import ResponseReturnValue
from flask_wtf.csrf import CSRFError, CSRFProtect  # type: ignore[import-untyped]
from sqlalchemy import create_engine, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, selectinload, sessionmaker
from werkzeug import Response as WerkzeugResponse
from werkzeug.security import check_password_hash

from common.models.employees import Employees
from common.models.production import PostRequest, RequestStatus
from common.models.users import Users, UsersPasswords, UserSession

P = ParamSpec("P")
LOGIN_TEMPLATE = "field_login.html"


@dataclass(frozen=True)
class FieldServiceConfig:
    """Configuration immuable d'une application terrain."""

    name: str
    title: str
    permission: str
    request_model: type[PostRequest]


def create_field_service_app(
    config: FieldServiceConfig,
    main_database_url: str | None = None,
    auth_database_url: str | None = None,
) -> Flask:
    """Crée une application terrain traitant un type de demande donné."""
    flask_app = Flask(__name__, template_folder="templates", static_folder="static")
    flask_app.config["SESSION_COOKIE_NAME"] = f"{config.name}_session"
    _configure_application(flask_app, main_database_url, auth_database_url)
    _register_error_handlers(flask_app)
    _register_routes(flask_app, config)
    _register_service_root(flask_app, config)
    return flask_app


def _configure_application(
    flask_app: Flask,
    main_database_url: str | None,
    auth_database_url: str | None,
) -> None:
    flask_app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "")
    if not flask_app.config["SECRET_KEY"]:
        raise RuntimeError("La variable d'environnement FLASK_SECRET_KEY est requise.")
    flask_app.extensions["main_session_factory"] = sessionmaker(
        bind=create_engine(
            _database_url("POSTGRES_DB_MAIN", main_database_url),
            pool_pre_ping=True,
        )
    )
    flask_app.extensions["auth_session_factory"] = sessionmaker(
        bind=create_engine(
            _database_url("POSTGRES_DB_USERS", auth_database_url),
            pool_pre_ping=True,
        )
    )
    CSRFProtect(flask_app)


def _register_service_root(flask_app: Flask, config: FieldServiceConfig) -> None:
    @flask_app.get("/")
    def service_root() -> WerkzeugResponse:
        return redirect(url_for(f"{config.name}.home"))


def _register_routes(flask_app: Flask, config: FieldServiceConfig) -> None:
    blueprint = Blueprint(config.name, __name__, url_prefix=f"/{config.name}")

    @blueprint.route("/connexion", methods=("GET", "POST"))
    def login() -> ResponseReturnValue:
        if request.method == "GET":
            return render_template(LOGIN_TEMPLATE, service=config)
        return _process_login(config)

    @blueprint.post("/deconnexion")
    def logout() -> WerkzeugResponse:
        session.clear()
        return redirect(url_for(f"{config.name}.login"))

    @blueprint.get("/")
    @_require_employee(config)
    def home() -> str:
        return render_template("field_home.html", employee=g.employee, service=config)

    @blueprint.get("/demandes")
    @_require_employee(config)
    def request_list() -> str:
        return _requests_fragment(config)

    @blueprint.post("/demandes/<int:request_id>/prendre-en-charge")
    @_require_employee(config)
    def take_in_charge(request_id: int) -> tuple[str, int]:
        domain_request = _request_to_handle(config, request_id)
        if domain_request.status is not RequestStatus.OPEN:
            return _requests_fragment(config, "Cette demande n'est plus disponible."), 409
        domain_request.status = RequestStatus.IN_PROGRESS
        domain_request.id_handler_employee = g.employee.id
        domain_request.taken_in_charge_at = datetime.now(timezone.utc)
        _database_session("main").commit()
        return _requests_fragment(config, "Demande prise en charge."), 200

    @blueprint.post("/demandes/<int:request_id>/resoudre")
    @_require_employee(config)
    def resolve(request_id: int) -> tuple[str, int]:
        domain_request = _request_to_handle(config, request_id)
        if (
            domain_request.status is not RequestStatus.IN_PROGRESS
            or domain_request.id_handler_employee != g.employee.id
        ):
            return _requests_fragment(
                config,
                "Seul le responsable peut résoudre cette demande.",
            ), 403
        domain_request.status = RequestStatus.RESOLVED
        domain_request.resolved_at = datetime.now(timezone.utc)
        _database_session("main").commit()
        return _requests_fragment(config, "Demande résolue."), 200

    flask_app.register_blueprint(blueprint)


def _process_login(config: FieldServiceConfig) -> ResponseReturnValue:
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not username or not password:
        return render_template(
            LOGIN_TEMPLATE,
            service=config,
            error="L'identifiant et le mot de passe sont requis.",
        ), 400
    auth_session = _database_session("auth")
    user = auth_session.scalar(select(Users).where(Users.username == username))
    if user is None or user.is_locked or not user.is_active:
        return _login_failure(config, user)
    now = datetime.now(timezone.utc)
    password_record = auth_session.scalar(
        select(UsersPasswords)
        .where(
            UsersPasswords.user_id == user.id,
            UsersPasswords.from_date <= now,
            (UsersPasswords.to_date.is_(None) | (UsersPasswords.to_date > now)),
        )
        .order_by(UsersPasswords.from_date.desc())
    )
    if password_record is None or not check_password_hash(
        password_record.password_hash, password
    ):
        return _login_failure(config, user)
    if config.permission not in user.permissions:
        return render_template(
            LOGIN_TEMPLATE,
            service=config,
            error="Accès non autorisé pour ce service.",
        ), 403
    employee = _database_session("main").scalar(
        select(Employees).where(
            Employees.auth_user_id == user.id,
            Employees.quit_date.is_(None),
        )
    )
    if employee is None:
        return render_template(
            LOGIN_TEMPLATE,
            service=config,
            error="Aucun profil employé actif n'est associé à ce compte.",
        ), 403
    user.nb_failed_logins = 0
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    auth_session.add(
        UserSession(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=now + timedelta(hours=8),
        )
    )
    auth_session.commit()
    session.clear()
    session["token_hash"] = token_hash
    return redirect(url_for(f"{config.name}.home"))


def _database_session(name: str) -> Session:
    session_key = f"{name}_database_session"
    if session_key not in g:
        setattr(g, session_key, current_app.extensions[f"{name}_session_factory"]())
    return getattr(g, session_key)


def _current_employee(config: FieldServiceConfig) -> Employees | None:
    token_hash = session.get("token_hash")
    if not isinstance(token_hash, str):
        return None
    authenticated_session = _database_session("auth").scalar(
        select(UserSession)
        .options(selectinload(UserSession.user))
        .where(
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.now(timezone.utc),
        )
    )
    if authenticated_session is None:
        session.clear()
        return None
    user = authenticated_session.user
    if not user.is_active or user.is_locked or config.permission not in user.permissions:
        return None
    return _database_session("main").scalar(
        select(Employees).where(
            Employees.auth_user_id == user.id,
            Employees.quit_date.is_(None),
        )
    )


def _login_failure(
    config: FieldServiceConfig, user: Users | None
) -> ResponseReturnValue:
    if user is not None:
        user.nb_failed_logins += 1
        if user.nb_failed_logins >= 5:
            user.is_locked = True
        _database_session("auth").commit()
    message = (
        "Compte verrouillé après cinq erreurs."
        if user is not None and user.is_locked
        else "Identifiant ou mot de passe invalide."
    )
    return render_template(LOGIN_TEMPLATE, service=config, error=message), 401


def _require_employee(
    config: FieldServiceConfig,
) -> Callable[[Callable[P, ResponseReturnValue]], Callable[P, ResponseReturnValue]]:
    def decorator(
        view: Callable[P, ResponseReturnValue],
    ) -> Callable[P, ResponseReturnValue]:
        @wraps(view)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> ResponseReturnValue:
            employee = _current_employee(config)
            if employee is None:
                return _unauthenticated_response(config)
            g.employee = employee
            return view(*args, **kwargs)

        return wrapped

    return decorator


def _unauthenticated_response(config: FieldServiceConfig) -> ResponseReturnValue:
    session.clear()
    if request.accept_mimetypes.accept_html:
        return redirect(url_for(f"{config.name}.login"))
    _abort_message("Authentification terrain requise.", 401)


def _active_requests(config: FieldServiceConfig) -> Sequence[PostRequest]:
    return _database_session("main").scalars(
        select(config.request_model)
        .options(selectinload(config.request_model.post))
        .where(config.request_model.status.in_((RequestStatus.OPEN, RequestStatus.IN_PROGRESS)))
        .order_by(config.request_model.created_at)
    ).all()


def _requests_fragment(config: FieldServiceConfig, message: str | None = None) -> str:
    return render_template(
        "fragments/field_requests.html",
        active_requests=_active_requests(config),
        employee=g.employee,
        service=config,
        message=message,
    )


def _request_to_handle(config: FieldServiceConfig, request_id: int) -> PostRequest:
    domain_request = _database_session("main").scalar(
        select(config.request_model)
        .where(config.request_model.id == request_id)
        .with_for_update()
    )
    if domain_request is None:
        _abort_message("Demande introuvable.", 404)
    return domain_request


def _abort_message(message: str, status: int) -> NoReturn:
    abort(Response(render_template("fragments/message.html", message=message), status))


def _register_error_handlers(flask_app: Flask) -> None:

    @flask_app.errorhandler(CSRFError)
    def handle_csrf_error(error: CSRFError) -> tuple[str, int]:
        return render_template("fragments/message.html", message=error.description), 400

    @flask_app.teardown_appcontext
    def close_database_sessions(_: BaseException | None) -> None:
        for name in ("main", "auth"):
            database_session_value = g.pop(f"{name}_database_session", None)
            if database_session_value is not None:
                database_session_value.close()


def _database_url(database_name: str, configured_url: str | None) -> str | URL:
    if configured_url:
        return configured_url
    required_settings = ("POSTGRES_USER_APP", "POSTGRES_PASSWORD_APP", database_name)
    missing_settings = [key for key in required_settings if not os.environ.get(key)]
    if missing_settings:
        raise RuntimeError(
            f"Variables d'environnement manquantes : {', '.join(missing_settings)}."
        )
    return URL.create(
        "postgresql+psycopg2",
        username=os.environ["POSTGRES_USER_APP"],
        password=os.environ["POSTGRES_PASSWORD_APP"],
        host=os.environ.get("POSTGRES_HOST", "db-main"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ[database_name],
    )
