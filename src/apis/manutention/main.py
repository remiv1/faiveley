"""Point d'entrée de l'API Flask destinée aux manutentionnaires."""

import os
import hashlib
import secrets
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
from werkzeug import Response as WerkzeugResponse
from werkzeug.security import check_password_hash
from sqlalchemy import case, create_engine, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, selectinload, sessionmaker

from common.environment_navigation import clear_environment_session, register_environment_navigation
from common.models.employees import Employees
from common.models.production import (
    LogisticsSupportRequest,
    RequestStatus,
    SupplyPriority,
    SupplyRequest,
)
from common.models.users import MANUTENTION, Users, UsersPasswords, UserSession

LOGIN_PAGE = "login.html"

P = ParamSpec("P")
manutention_blueprint = Blueprint(
    "manutention",
    __name__,
    url_prefix="/manutention",
    static_folder="static",
)
csrf = CSRFProtect()


def _database_session(name: str) -> Session:
    session_key = f"{name}_database_session"
    if session_key not in g:
        setattr(g, session_key, current_app.extensions[f"{name}_session_factory"]())
    return getattr(g, session_key)


def _main_session() -> Session:
    return _database_session("main")


def _auth_session() -> Session:
    return _database_session("auth")


def _abort_message(message: str, status: int) -> NoReturn:
    abort(Response(render_template("fragments/message.html", message=message), status))


def _current_employee() -> Employees | None:
    token_hash = session.get("token_hash")
    if not isinstance(token_hash, str):
        return None
    authenticated_session = _auth_session().scalar(
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
    if not user.is_active or user.is_locked or MANUTENTION not in user.permissions:
        return None
    return _main_session().scalar(
        select(Employees).where(
            Employees.auth_user_id == user.id,
            Employees.quit_date.is_(None),
        )
    )


def _require_employee(
    view: Callable[P, ResponseReturnValue],
) -> Callable[P, ResponseReturnValue]:
    @wraps(view)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> ResponseReturnValue:
        employee = _current_employee()
        if employee is None:
            session.clear()
            if request.accept_mimetypes.accept_html:
                return redirect(url_for("manutention.login"))
            _abort_message("Authentification manutentionnaire requise.", 401)
        g.employee = employee
        return view(*args, **kwargs)

    return wrapped


def _supply_requests() -> Sequence[SupplyRequest]:
    priority_order = case(
        (SupplyRequest.priority == SupplyPriority.RUPTURE, 0),
        (SupplyRequest.priority == SupplyPriority.URGENT, 1),
        else_=2,
    )
    return _main_session().scalars(
        select(SupplyRequest)
        .options(selectinload(SupplyRequest.material), selectinload(SupplyRequest.post))
        .where(SupplyRequest.status.in_((RequestStatus.OPEN, RequestStatus.IN_PROGRESS)))
        .order_by(priority_order, SupplyRequest.created_at)
    ).all()


def _logistics_requests() -> Sequence[LogisticsSupportRequest]:
    return _main_session().scalars(
        select(LogisticsSupportRequest)
        .options(selectinload(LogisticsSupportRequest.post))
        .where(
            LogisticsSupportRequest.status.in_(
                (RequestStatus.OPEN, RequestStatus.IN_PROGRESS)
            )
        )
        .order_by(LogisticsSupportRequest.created_at)
    ).all()


def _supply_requests_fragment(message: str | None = None) -> str:
    return render_template(
        "fragments/supply_requests.html",
        supply_requests=_supply_requests(),
        employee=g.employee,
        message=message,
    )


def _logistics_requests_fragment(message: str | None = None) -> str:
    return render_template(
        "fragments/logistics_requests.html",
        logistics_requests=_logistics_requests(),
        employee=g.employee,
        message=message,
    )


@manutention_blueprint.route("/connexion", methods=("GET", "POST"))
def login() -> ResponseReturnValue:
    """Affiche ou traite la connexion identifiant/mot de passe."""
    if request.method == "GET":
        return render_template(LOGIN_PAGE)
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not username or not password:
        return render_template(
            LOGIN_PAGE, error="L'identifiant et le mot de passe sont requis."
        ), 400
    auth_session = _auth_session()
    user = auth_session.scalar(select(Users).where(Users.username == username))
    if user is None or user.is_locked or not user.is_active:
        return _login_failure(user)
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
        return _login_failure(user)
    if MANUTENTION not in user.permissions:
        return render_template(
            LOGIN_PAGE, error="Accès non autorisé pour ce service."
        ), 403
    employee = _main_session().scalar(
        select(Employees).where(
            Employees.auth_user_id == user.id,
            Employees.quit_date.is_(None),
        )
    )
    if employee is None:
        return render_template(
            LOGIN_PAGE, error="Aucun profil employé actif n'est associé à ce compte."
        ), 403
    user.nb_failed_logins = 0
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    auth_session.add(
        UserSession(token_hash=token_hash, user_id=user.id, expires_at=now + timedelta(hours=8))
    )
    auth_session.commit()
    session.clear()
    session["token_hash"] = token_hash
    return redirect(url_for("manutention.home"))


def _login_failure(user: Users | None) -> ResponseReturnValue:
    if user is not None:
        user.nb_failed_logins += 1
        if user.nb_failed_logins >= 5:
            user.is_locked = True
        _auth_session().commit()
    message = (
        "Compte verrouillé après cinq erreurs."
        if user is not None and user.is_locked
        else "Identifiant ou mot de passe invalide."
    )
    return render_template(LOGIN_PAGE, error=message), 401


@manutention_blueprint.post("/deconnexion")
def logout() -> WerkzeugResponse:
    """Révoque le jeton courant et supprime la session locale."""
    clear_environment_session(current_app.extensions["auth_session_factory"])
    return redirect(url_for("manutention.login"))


@manutention_blueprint.get("/")
@_require_employee
def home() -> str:
    """Affiche les files de demandes de la manutention."""
    return render_template("home.html", employee=g.employee)


@manutention_blueprint.get("/demandes")
@_require_employee
def requests_fragment() -> str:
    """Retourne le fragment HTMX des demandes d'approvisionnement."""
    return _supply_requests_fragment()


@manutention_blueprint.get("/demandes-logistiques")
@_require_employee
def logistics_requests_fragment() -> str:
    """Retourne le fragment HTMX des demandes de support logistique."""
    return _logistics_requests_fragment()


def _supply_request_to_handle(request_id: int) -> SupplyRequest:
    supply_request = _main_session().scalar(
        select(SupplyRequest)
        .where(SupplyRequest.id == request_id)
        .with_for_update()
    )
    if supply_request is None:
        _abort_message("Demande d'approvisionnement introuvable.", 404)
    return supply_request


@manutention_blueprint.post("/demandes/<int:request_id>/prendre-en-charge")
@_require_employee
def take_in_charge(request_id: int) -> tuple[str, int]:
    """Affecte une demande ouverte au manutentionnaire connecté."""
    supply_request = _supply_request_to_handle(request_id)
    if supply_request.status is not RequestStatus.OPEN:
        return _supply_requests_fragment("Cette demande n'est plus disponible."), 409
    supply_request.status = RequestStatus.IN_PROGRESS
    supply_request.id_handler_employee = g.employee.id
    supply_request.taken_in_charge_at = datetime.now(timezone.utc)
    _main_session().commit()
    return _supply_requests_fragment("Demande prise en charge."), 200


@manutention_blueprint.post("/demandes/<int:request_id>/resoudre")
@_require_employee
def resolve(request_id: int) -> tuple[str, int]:
    """Clôture une demande prise en charge par l'utilisateur connecté."""
    supply_request = _supply_request_to_handle(request_id)
    if (
        supply_request.status is not RequestStatus.IN_PROGRESS
        or supply_request.id_handler_employee != g.employee.id
    ):
        return _supply_requests_fragment(
            "Seul le manutentionnaire responsable peut résoudre cette demande."
        ), 403
    supply_request.status = RequestStatus.RESOLVED
    supply_request.resolved_at = datetime.now(timezone.utc)
    _main_session().commit()
    return _supply_requests_fragment("Demande résolue."), 200


def _logistics_request_to_handle(request_id: int) -> LogisticsSupportRequest:
    logistics_request = _main_session().scalar(
        select(LogisticsSupportRequest)
        .where(LogisticsSupportRequest.id == request_id)
        .with_for_update()
    )
    if logistics_request is None:
        _abort_message("Demande de support logistique introuvable.", 404)
    return logistics_request


@manutention_blueprint.post("/demandes-logistiques/<int:request_id>/prendre-en-charge")
@_require_employee
def take_logistics_request_in_charge(request_id: int) -> tuple[str, int]:
    """Affecte une demande logistique ouverte au manutentionnaire connecté."""
    logistics_request = _logistics_request_to_handle(request_id)
    if logistics_request.status is not RequestStatus.OPEN:
        return _logistics_requests_fragment("Cette demande n'est plus disponible."), 409
    logistics_request.status = RequestStatus.IN_PROGRESS
    logistics_request.id_handler_employee = g.employee.id
    logistics_request.taken_in_charge_at = datetime.now(timezone.utc)
    _main_session().commit()
    return _logistics_requests_fragment("Demande prise en charge."), 200


@manutention_blueprint.post("/demandes-logistiques/<int:request_id>/resoudre")
@_require_employee
def resolve_logistics_request(request_id: int) -> tuple[str, int]:
    """Clôture une demande logistique prise en charge par l'utilisateur connecté."""
    logistics_request = _logistics_request_to_handle(request_id)
    if (
        logistics_request.status is not RequestStatus.IN_PROGRESS
        or logistics_request.id_handler_employee != g.employee.id
    ):
        return _logistics_requests_fragment(
            "Seul le manutentionnaire responsable peut résoudre cette demande."
        ), 403
    logistics_request.status = RequestStatus.RESOLVED
    logistics_request.resolved_at = datetime.now(timezone.utc)
    _main_session().commit()
    return _logistics_requests_fragment("Demande résolue."), 200


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


def create_app(
    main_database_url: str | None = None,
    auth_database_url: str | None = None,
) -> Flask:
    """Crée l'application Flask de la file Manutention."""
    flask_app = Flask(
        __name__,
        static_folder="../../common/static",
        static_url_path="/manutention/assets",
    )
    flask_app.config["SESSION_COOKIE_NAME"] = "manutention_session"
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
    csrf.init_app(flask_app)

    @flask_app.errorhandler(CSRFError)
    def handle_csrf_error(error: CSRFError) -> tuple[str, int]:
        return render_template("fragments/message.html", message=error.description), 400

    @flask_app.teardown_appcontext
    def close_database_sessions(_: BaseException | None) -> None:
        for name in ("main", "auth"):
            database_session = g.pop(f"{name}_database_session", None)
            if database_session is not None:
                database_session.close()

    flask_app.register_blueprint(manutention_blueprint)

    @flask_app.get("/")
    def service_root() -> WerkzeugResponse:
        return redirect(url_for("manutention.home"))

    register_environment_navigation(flask_app, "manutention")
    return flask_app


app = create_app()
