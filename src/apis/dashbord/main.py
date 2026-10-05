"""Portail Flask de supervision et de gestion industrielle."""

import os
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from functools import wraps
from typing import Any, NoReturn, ParamSpec

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
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload, sessionmaker
from werkzeug import Response as WerkzeugResponse
from werkzeug.security import check_password_hash, generate_password_hash

from common.environment_navigation import clear_environment_session, register_environment_navigation
from common.models.articles import Articles
from common.models.employees import DepartmentEnum, Employees, JobTitleEnum
from common.models.machines import Machines
from common.models.materials import Materials
from common.models.ordre_fabrication import OrdreFabrication, OrdreFabricationStatus
from common.models.posts import PostHours, Posts
from common.models.production import SupplyRequest  # noqa: F401 # pylint: disable=W0611
from common.models.users import ADMIN, DIRECTION, SUPER_ADMIN, UserSession, Users, UsersPasswords

P = ParamSpec("P")
dashboard_blueprint = Blueprint("dashboard", __name__, url_prefix="/gestion")
csrf = CSRFProtect()
ACCESS_PERMISSIONS = frozenset((ADMIN, DIRECTION, SUPER_ADMIN))
ACCOUNT_PERMISSIONS = frozenset((ADMIN, SUPER_ADMIN))
ENTITY_LIST_ENDPOINT = "dashboard.entity_list"
USER_LIST_ENDPOINT = "dashboard.user_list"
USER_NOT_FOUND_MESSAGE = "Utilisateur introuvable."
ROLE_OPTIONS = (
    ("1", "Administrateur"), ("2", "Comptabilité"), ("3", "Commercial"),
    ("4", "Logistique"), ("5", "Support"), ("6", "Informatique"),
    ("7", "Ressources humaines"), ("8", "Direction"), ("9", "Super administrateur"),
    ("m", "Manutention"), ("t", "Techniciens"), ("q", "Qualité"),
)


def _database_session(name: str) -> Session:
    key = f"{name}_database_session"
    if key not in g:
        setattr(g, key, current_app.extensions[f"{name}_session_factory"]())
    return getattr(g, key)


def _abort(message: str, status: int) -> NoReturn:
    abort(Response(render_template("message.html", message=message), status))


def _current_user() -> Users | None:
    user_id = session.get("user_id")
    if not isinstance(user_id, int):
        return None
    user = _database_session("secure").get(Users, user_id)
    if user is None or not user.is_active or user.is_locked:
        session.clear()
        return None
    return user


def _is_allowed(user: Users, permissions: frozenset[str]) -> bool:
    return any(permission in user.permissions for permission in permissions)


def _require_permissions(
    permissions: frozenset[str],
) -> Callable[[Callable[P, ResponseReturnValue]], Callable[P, ResponseReturnValue]]:
    def decorator(view: Callable[P, ResponseReturnValue]) -> Callable[P, ResponseReturnValue]:
        @wraps(view)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> ResponseReturnValue:
            user = _current_user()
            if user is None:
                return redirect(url_for("dashboard.login"))
            if not _is_allowed(user, permissions):
                _abort("Vous n'êtes pas autorisé à accéder à cette fonction.", 403)
            g.current_user = user
            return view(*args, **kwargs)

        return wrapped

    return decorator


def _form_value(name: str, required: bool = False) -> str | None:
    value = request.form.get(name, "").strip()
    if required and not value:
        _abort(f"Le champ {name} est requis.", 400)
    return value or None


def _required_form_value(name: str) -> str:
    value = _form_value(name, required=True)
    if value is None:
        raise RuntimeError(f"Le champ requis {name} est absent.")
    return value


def _form_integer(name: str, required: bool = False) -> int | None:
    value = _form_value(name, required)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        _abort(f"Le champ {name} doit être un entier.", 400)


def _dashboard_data() -> list[dict[str, Any]]:
    main_session = _database_session("main")
    machines = main_session.scalars(
        select(Machines).options(selectinload(Machines.ordre_fabrication))
    ).all()
    entries: list[dict[str, Any]] = []
    for machine in machines:
        active_order = next(
            (
                order for order in machine.ordre_fabrication
                if order.status is OrdreFabricationStatus.ACTIVE
            ),
            None,
        )
        active_post = None
        goods = 0
        rejects = 0
        if active_order is not None:
            active_post = main_session.scalar(
                select(Posts)
                .options(selectinload(Posts.employee))
                .where(Posts.id_of == active_order.id, Posts.end_datetime.is_(None))
                .order_by(Posts.start_datetime.desc())
            )
            if active_post is not None:
                goods, rejects = main_session.execute(
                    select(
                        func.coalesce(
                            func.sum(
                                PostHours.qty_goods
                            ),
                            0,
                        ),
                        func.coalesce(
                            func.sum(
                                PostHours.qty_bads),
                                0,
                            )
                        )
                    .where(PostHours.id_post == active_post.id)
                ).one()
        entries.append(
            {
                "machine": machine,
                "order": active_order,
                "post": active_post,
                "goods": goods,
                "rejects": rejects,
            }
        )
    return entries


def _entity_configuration(entity: str) -> tuple[type[Any], str, Sequence[Any]]:
    main_session = _database_session("main")
    configurations: dict[str, Any] = {
        "machines": (
            Machines,
            "Machines",
            main_session.scalars(
                select(Machines).order_by(Machines.name)
            ).all()
        ),
        "articles": (
            Articles,
            "Articles",
            main_session.scalars(
                select(Articles).order_by(Articles.name)
            ).all()
        ),
        "materiels": (
            Materials,
            "Matériels",
            main_session.scalars(
                select(Materials).order_by(Materials.ref)
            ).all()
        ),
        "personnels": (
            Employees,
            "Personnels",
            main_session.scalars(
                select(Employees).order_by(Employees.last_name, Employees.first_name)
            ).all()
        ),
        "ofs": (
            OrdreFabrication,
            "Ordres de fabrication",
            main_session.scalars(
                select(OrdreFabrication)
                .options(
                    selectinload(OrdreFabrication.machine),
                    selectinload(OrdreFabrication.articles),
                    selectinload(OrdreFabrication.materials)
                )
                .order_by(OrdreFabrication.code)
            ).all()
        ),
        "posts": (
            Posts,
            "Postes",
            main_session.scalars(
                select(Posts)
                .options(
                    selectinload(Posts.employee),
                    selectinload(Posts.ordre_fabrication)
                )
                .order_by(Posts.start_datetime.desc())
            ).all()
        ),
    }
    if entity not in configurations:
        _abort("Référentiel introuvable.", 404)
    return configurations[entity]


def _reference_data() -> dict[str, Any]:
    main_session = _database_session("main")
    return {
        "machines": main_session.scalars(
            select(Machines).order_by(Machines.name)
        ).all(),
        "articles": main_session.scalars(
            select(Articles).order_by(Articles.name)
        ).all(),
        "materials": main_session.scalars(
            select(Materials).order_by(Materials.ref)
        ).all(),
        "employees": main_session.scalars(
            select(Employees).order_by(Employees.last_name)
        ).all(),
        "orders": main_session.scalars(
            select(OrdreFabrication).order_by(OrdreFabrication.code)
        ).all(),
        "job_titles": tuple(JobTitleEnum),
        "departments": tuple(DepartmentEnum),
        "statuses": tuple(OrdreFabricationStatus),
    }


def _populate_entity(entity: str, instance: Any) -> None:
    if entity == "machines":
        instance.name = _required_form_value("name")
        instance.description = _form_value("description")
    elif entity == "articles":
        instance.name = _required_form_value("name")
        instance.description = _form_value("description")
        instance.client = _form_value("client")
        instance.product = _form_value("product")
    elif entity == "materiels":
        instance.name = _required_form_value("name")
        instance.ref = _required_form_value("ref")
        instance.description = _form_value("description")
    elif entity == "personnels":
        instance.first_name = _required_form_value("first_name")
        instance.last_name = _required_form_value("last_name")
        instance.email = _required_form_value("email")
        instance.phone = _form_value("phone")
        instance.job_title = JobTitleEnum(_required_form_value("job_title"))
        instance.department = DepartmentEnum(_required_form_value("department"))
        instance.is_manager = request.form.get("is_manager") == "on"
        instance.manager_id = _form_integer("manager_id")
    elif entity == "ofs":
        instance.code = _required_form_value("code")
        instance.id_machine = _form_integer("id_machine", True)
        instance.id_article = _form_integer("id_article", True)
        instance.capacities = _form_integer("capacities")
        status = OrdreFabricationStatus(_required_form_value("status"))
        instance.status = status
        if status is OrdreFabricationStatus.ACTIVE and instance.started_at is None:
            instance.started_at = datetime.now(timezone.utc)
        if status in (
            OrdreFabricationStatus.COMPLETED, OrdreFabricationStatus.CANCELLED
        ) and instance.completed_at is None:
            instance.completed_at = datetime.now(timezone.utc)
        material_ids = request.form.getlist("material_ids", type=int)
        instance.materials = _database_session("main").scalars(
            select(Materials).where(Materials.id.in_(material_ids))
        ).all()
    elif entity == "posts":
        instance.id_of = _form_integer("id_of", True)
        instance.id_employee = _form_integer("id_employee", True)
        instance.id_manager = _form_integer("id_manager", True)
        instance.press_ref = _required_form_value("press_ref")
        if instance.start_datetime is None:
            instance.start_datetime = datetime.now(timezone.utc)


def _commit_or_abort(database_session: Session) -> None:
    try:
        database_session.commit()
    except IntegrityError:
        database_session.rollback()
        _abort("Cette opération contrevient à une contrainte de données.", 409)


def _link_employee_to_user(employee_id: int | None, user_id: int) -> None:
    main_session = _database_session("main")
    linked_employee = main_session.scalar(
        select(Employees).where(Employees.auth_user_id == user_id)
    )
    selected_employee = main_session.get(Employees, employee_id) if employee_id else None
    if employee_id is not None and selected_employee is None:
        _abort("Employé introuvable.", 404)
    if selected_employee is not None and selected_employee.auth_user_id not in (None, user_id):
        _abort("Cet employé est déjà associé à un autre utilisateur.", 409)
    if linked_employee is not None and linked_employee is not selected_employee:
        linked_employee.auth_user_id = None
    if selected_employee is not None:
        selected_employee.auth_user_id = user_id
    _commit_or_abort(main_session)


@dashboard_blueprint.route("/connexion", methods=("GET", "POST"))
def login() -> ResponseReturnValue:
    """Authentifie un administrateur du portail Gestion."""
    if request.method == "GET":
        return render_template("login.html")
    username = _required_form_value("username")
    password = request.form.get("password", "")
    user = _database_session("secure").scalar(select(Users).where(Users.username == username))
    current_password = None
    if user is not None:
        current_password = _database_session("secure").scalar(
            select(UsersPasswords).where(
                UsersPasswords.user_id == user.id,
                UsersPasswords.to_date.is_(None),
            )
        )
    if (
        user is None or
        current_password is None or
        not check_password_hash(current_password.password_hash, password) or
        not _is_allowed(user, ACCESS_PERMISSIONS)
    ):
        return render_template(
            "login.html",
            error="Identifiants invalides ou accès non autorisé.",
        ), 401
    session.clear()
    session["user_id"] = user.id
    return redirect(url_for("dashboard.home"))


@dashboard_blueprint.post("/deconnexion")
def logout() -> WerkzeugResponse:
    """Ferme la session HTTP du portail Gestion."""
    clear_environment_session()
    return redirect(url_for("dashboard.login"))


@dashboard_blueprint.get("/")
@_require_permissions(ACCESS_PERMISSIONS)
def home() -> str:
    """Affiche la supervision des machines et des postes actifs."""
    return render_template("home.html", entries=_dashboard_data())


@dashboard_blueprint.get("/<entity>")
@_require_permissions(ACCESS_PERMISSIONS)
def entity_list(entity: str) -> str:
    """Affiche un référentiel métier éditable."""
    _, title, items = _entity_configuration(entity)
    return render_template("entity_list.html", entity=entity, title=title, items=items)


@dashboard_blueprint.route("/<entity>/nouveau", methods=("GET", "POST"))
@_require_permissions(ACCESS_PERMISSIONS)
def entity_create(entity: str) -> ResponseReturnValue:
    """Crée une entité métier du référentiel sélectionné."""
    model, title, _ = _entity_configuration(entity)
    if request.method == "GET":
        return render_template(
            "entity_form.html",
            entity=entity,
            title=title,
            item=None,
            **_reference_data()
        )
    instance = model()
    _populate_entity(entity, instance)
    database_session = _database_session("main")
    database_session.add(instance)
    _commit_or_abort(database_session)
    return redirect(url_for(ENTITY_LIST_ENDPOINT, entity=entity))


@dashboard_blueprint.route("/<entity>/<int:item_id>/modifier", methods=("GET", "POST"))
@_require_permissions(ACCESS_PERMISSIONS)
def entity_edit(entity: str, item_id: int) -> ResponseReturnValue:
    """Modifie une entité métier du référentiel sélectionné."""
    model, title, _ = _entity_configuration(entity)
    instance = _database_session("main").get(model, item_id)
    if instance is None:
        _abort("Élément introuvable.", 404)
    if request.method == "GET":
        return render_template(
            "entity_form.html",
            entity=entity,
            title=title,
            item=instance,
            **_reference_data(),
        )
    _populate_entity(entity, instance)
    _commit_or_abort(_database_session("main"))
    return redirect(url_for(ENTITY_LIST_ENDPOINT, entity=entity))


@dashboard_blueprint.post("/<entity>/<int:item_id>/supprimer")
@_require_permissions(ACCESS_PERMISSIONS)
def entity_delete(entity: str, item_id: int) -> WerkzeugResponse:
    """Supprime une entité métier lorsqu'elle n'est plus référencée."""
    model, _, _ = _entity_configuration(entity)
    database_session = _database_session("main")
    instance = database_session.get(model, item_id)
    if instance is None:
        _abort("Élément introuvable.", 404)
    database_session.delete(instance)
    _commit_or_abort(database_session)
    return redirect(url_for(ENTITY_LIST_ENDPOINT, entity=entity))


@dashboard_blueprint.get("/utilisateurs")
@_require_permissions(ACCOUNT_PERMISSIONS)
def user_list() -> str:
    """Affiche les comptes d'authentification et leurs rôles."""
    users = _database_session("secure").scalars(select(Users).order_by(Users.username)).all()
    return render_template("users.html", users=users, roles=ROLE_OPTIONS)


@dashboard_blueprint.route("/utilisateurs/nouveau", methods=("GET", "POST"))
@dashboard_blueprint.route("/utilisateurs/<int:user_id>/modifier", methods=("GET", "POST"))
@_require_permissions(ACCOUNT_PERMISSIONS)
def user_form(user_id: int | None = None) -> ResponseReturnValue:
    """Crée ou modifie un compte et ses permissions."""
    database_session = _database_session("secure")
    user = database_session.get(Users, user_id) if user_id is not None else None
    if user_id is not None and user is None:
        _abort(USER_NOT_FOUND_MESSAGE, 404)
    if request.method == "GET":
        return render_template(
            "user_form.html",
            user=user,
            roles=ROLE_OPTIONS,
            employees=_database_session("main").scalars(
                select(Employees).order_by(Employees.last_name, Employees.first_name)
            ).all(),
        )
    is_new = user is None
    user = user or Users()
    user.username = _required_form_value("username")
    user.email = _required_form_value("email")
    user.permissions = "".join(
        code for code, _ in ROLE_OPTIONS
        if code in request.form.getlist("permissions")
    )
    user.is_active = request.form.get("is_active") == "on"
    user.is_locked = request.form.get("is_locked") == "on"
    password = request.form.get("password", "")
    if is_new and not password:
        _abort("Un mot de passe initial est requis.", 400)
    if is_new:
        database_session.add(user)
        database_session.flush()
    if password:
        now = datetime.now(timezone.utc)
        database_session.query(UsersPasswords).filter(
            UsersPasswords.user_id == user.id,
            UsersPasswords.to_date.is_(None),
        ).update({UsersPasswords.to_date: now})
        database_session.add(
            UsersPasswords(
                user_id=user.id,
                password_hash=generate_password_hash(password),
                from_date=now,
            )
        )
    _commit_or_abort(database_session)
    _link_employee_to_user(_form_integer("employee_id"), user.id)
    return redirect(url_for(USER_LIST_ENDPOINT))


@dashboard_blueprint.post("/utilisateurs/<int:user_id>/revoquer-sessions")
@_require_permissions(ACCOUNT_PERMISSIONS)
def revoke_user_sessions(user_id: int) -> WerkzeugResponse:
    """Révoque toutes les sessions Bearer actives d'un utilisateur."""
    database_session = _database_session("secure")
    user = database_session.get(Users, user_id)
    if user is None:
        _abort(USER_NOT_FOUND_MESSAGE, 404)
    database_session.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.revoked_at.is_(None),
    ).update({UserSession.revoked_at: datetime.now(timezone.utc)})
    _commit_or_abort(database_session)
    return redirect(url_for(USER_LIST_ENDPOINT))


@dashboard_blueprint.post("/utilisateurs/<int:user_id>/supprimer")
@_require_permissions(ACCOUNT_PERMISSIONS)
def delete_user(user_id: int) -> WerkzeugResponse:
    """Supprime un compte, ses accès et son association métier éventuelle."""
    secure_session = _database_session("secure")
    user = secure_session.get(Users, user_id)
    if user is None:
        _abort(USER_NOT_FOUND_MESSAGE, 404)
    employee = _database_session("main").scalar(
        select(Employees).where(Employees.auth_user_id == user.id)
    )
    if employee is not None:
        employee.auth_user_id = None
        _commit_or_abort(_database_session("main"))
    secure_session.delete(user)
    _commit_or_abort(secure_session)
    return redirect(url_for(USER_LIST_ENDPOINT))


def _database_url(
        database_name: str,
        username_name: str,
        password_name: str,
        configured_url: str | None = None,
    ) -> str | URL:
    if configured_url:
        return configured_url
    required = (database_name, username_name, password_name)
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Variables d'environnement manquantes : {', '.join(missing)}.")
    return URL.create(
        "postgresql+psycopg2",
        username=os.environ[username_name],
        password=os.environ[password_name],
        host=os.environ.get("POSTGRES_HOST", "db-main"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ[database_name],
    )


def create_app(
        main_database_url: str | None = None,
        secure_database_url: str | None = None,
    ) -> Flask:
    """Crée le portail de supervision et de gestion."""
    flask_app = Flask(__name__, static_url_path="/gestion/static")
    flask_app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "")
    if not flask_app.config["SECRET_KEY"]:
        raise RuntimeError("La variable d'environnement FLASK_SECRET_KEY est requise.")
    flask_app.extensions["main_session_factory"] = sessionmaker(
        bind=create_engine(
            _database_url(
                "POSTGRES_DB_MAIN",
                "POSTGRES_USER_APP",
                "POSTGRES_PASSWORD_APP",
                main_database_url,
            ),
            pool_pre_ping=True,
        )
    )
    flask_app.extensions["secure_session_factory"] = sessionmaker(
        bind=create_engine(
            _database_url(
                "POSTGRES_DB_USERS",
                "POSTGRES_USER_SECURE",
                "POSTGRES_PASSWORD_SECURE",
                secure_database_url,
            ),
            pool_pre_ping=True,
        )
    )
    csrf.init_app(flask_app)

    @flask_app.errorhandler(CSRFError)
    def handle_csrf_error(error: CSRFError) -> tuple[str, int]:
        return render_template("message.html", message=error.description), 400

    @flask_app.teardown_appcontext
    def close_database_sessions(_: BaseException | None) -> None:
        for name in ("main", "secure"):
            database_session = g.pop(f"{name}_database_session", None)
            if database_session is not None:
                database_session.close()

    flask_app.register_blueprint(dashboard_blueprint)

    @flask_app.get("/")
    def service_root() -> WerkzeugResponse:
        return redirect(url_for("dashboard.home"))

    register_environment_navigation(flask_app, "dashboard")
    return flask_app


app = create_app()
