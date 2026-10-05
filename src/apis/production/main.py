"""Point d'entrée de l'API Flask dédiée aux consoles de production."""

import os
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, NoReturn, ParamSpec

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
from sqlalchemy import create_engine, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker
from flask_wtf.csrf import CSRFError, CSRFProtect  # type: ignore[import-untyped]
from werkzeug import Response as WerkzeugResponse

from common.environment_navigation import clear_environment_session, register_environment_navigation
from common.models.materials import MaterialOF, Materials
from common.models.posts import PostHours, PostStops, Posts
from common.models.production import (
    CommentAuthorType,
    LogisticsSupportRequest,
    MaintenanceRequest,
    ProductionComment,
    QualitySupportRequest,
    RequestStatus,
    SupplyPriority,
    SupplyRequest,
)

P = ParamSpec("P")
MESSAGE_TEMPLATE = "fragments/message.html"
production_blueprint = Blueprint(
    "production",
    __name__,
    url_prefix="/production",
    static_folder="static",
)
csrf = CSRFProtect()


def _message(message: str, status: int = 200) -> tuple[str, int]:
    return render_template(MESSAGE_TEMPLATE, message=message), status


def _abort_message(message: str, status: int) -> NoReturn:
    abort(Response(render_template(MESSAGE_TEMPLATE, message=message), status))


def _database_session() -> Session:
    if "database_session" not in g:
        g.database_session = current_app.extensions["session_factory"]()
    return g.database_session


def _form_int(field: str) -> int:
    value = request.form.get(field, "")
    try:
        return int(value)
    except ValueError:
        _abort_message(f"Le champ {field} doit être un entier.", 400)
    raise RuntimeError("La requête aurait dû être interrompue.")


def _require_post_context(
    require_check: bool = True,
) -> Callable[
    [Callable[P, ResponseReturnValue]], Callable[P, ResponseReturnValue]
]:
    def decorator(
        view: Callable[P, ResponseReturnValue],
    ) -> Callable[P, ResponseReturnValue]:
        @wraps(view)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> ResponseReturnValue:
            id_post = _form_int("id_post")
            if session.get("id_post") != id_post:
                _abort_message("Le poste transmis ne correspond pas à cette console.", 403)
            if require_check and not session.get("operator_checked"):
                _abort_message("La présence de l'opérateur doit être validée.", 403)
            post = _database_session().get(Posts, id_post)
            if post is None or post.end_datetime is not None:
                _abort_message("Ce poste n'est plus actif.", 403)
            g.post = post
            return view(*args, **kwargs)

        return wrapped

    return decorator


def _active_post(press_ref: str) -> Posts | None:
    return _database_session().scalar(
        select(Posts)
        .where(Posts.press_ref == press_ref, Posts.end_datetime.is_(None))
        .order_by(Posts.start_datetime.desc(), Posts.id.desc())
    )


@production_blueprint.route("/selection-presse", methods=("GET", "POST"))
def select_press() -> ResponseReturnValue:
    """Sélectionne une presse active sans clôturer ni modifier son poste."""
    error = None
    status = 200
    if request.method == "POST":
        post = _active_post(request.form.get("press_ref", "").strip())
        if post is None:
            error = "Cette presse n'a plus de poste actif. Sélectionnez une autre presse."
            status = 409
        else:
            clear_environment_session()
            session["id_post"] = post.id
            session["press_ref"] = post.press_ref
            session["operator_checked"] = False
            return redirect(url_for("production.home"), code=303)
    press_refs = _database_session().scalars(
        select(Posts.press_ref)
        .where(Posts.end_datetime.is_(None))
        .distinct()
        .order_by(Posts.press_ref)
    ).all()
    return render_template("press_selection.html", press_refs=press_refs, error=error), status


@production_blueprint.post("/deconnexion")
def logout() -> WerkzeugResponse:
    """Efface le contexte de console sans clôturer le poste de production."""
    clear_environment_session()
    return redirect(url_for("production.select_press"), code=303)


@production_blueprint.get("/")
@production_blueprint.get("/<press_ref>")
def home(press_ref: str | None = None) -> ResponseReturnValue:
    """Affiche la page d'accueil de la console de production pour une presse donnée."""
    database_session = _database_session()
    if press_ref is not None:
        post = _active_post(press_ref)
        if post is None:
            _abort_message("Aucun poste actif ne correspond à cette presse.", 404)
        current_post_id = session.get("id_post")
        current_press_ref = session.get("press_ref")
        if current_post_id != post.id or current_press_ref != press_ref:
            session.clear()
            session["id_post"] = post.id
            session["press_ref"] = press_ref
    else:
        post_id = session.get("id_post")
        post = database_session.get(Posts, post_id) if post_id else None
        if post is None or post.end_datetime is not None:
            return redirect(url_for("production.select_press"))
    checked = session.get("operator_checked", False)
    dashboard_context = _dashboard_context(post) if checked else {}
    return render_template("home.html", post=post, checked=checked, **dashboard_context)


@production_blueprint.post("/check")
@_require_post_context(require_check=False)
def check_operator() -> ResponseReturnValue:
    """Valide la présence de l'opérateur pour le poste actif."""
    code = request.form.get("code", "")
    if not code.isdigit() or len(code) != 4:
        return _message("Le code opérateur doit contenir quatre chiffres.", 400)

    session["operator_checked"] = True
    post = _database_session().get(Posts, session["id_post"])
    if post is None:
        _abort_message("Ce poste n'est plus actif.", 403)

    if request.headers.get("HX-Request"):
        return render_template(
            "home.html", post=post, checked=True, **_dashboard_context(post)
        )

    press_ref = session.get("press_ref") or post.press_ref
    return redirect(url_for("production.home", press_ref=press_ref))


def _current_hour() -> datetime:
    """Retourne l'heure actuelle arrondie à l'heure entière en UTC."""
    current_time = datetime.now(timezone.utc)
    return current_time.replace(minute=0, second=0, microsecond=0)


def _dashboard_context(post: Posts) -> dict[str, Any]:
    database_session = _database_session()
    active_statuses = (RequestStatus.OPEN, RequestStatus.IN_PROGRESS)
    hourly_record = database_session.scalar(
        select(PostHours).where(
            PostHours.id_post == post.id,
            PostHours.recorded_at == _current_hour(),
        )
    )
    rejects_count = sum(
        quantity or 0
        for quantity in database_session.scalars(
            select(PostHours.qty_bads).where(PostHours.id_post == post.id)
        ).all()
    )
    stops_count = len(
        database_session.scalars(
            select(PostStops.id).where(PostStops.id_post == post.id)
        ).all()
    )
    supply_count = len(
        database_session.scalars(
            select(SupplyRequest.id).where(
                SupplyRequest.id_post == post.id,
                SupplyRequest.status.in_(active_statuses),
            )
        ).all()
    )

    operations: list[dict[str, Any]] = []
    request_groups = (
        (
            "Support qualité",
            database_session.scalars(
                select(QualitySupportRequest).where(
                    QualitySupportRequest.id_post == post.id,
                    QualitySupportRequest.status.in_(active_statuses),
                )
            ).all(),
        ),
        (
            "Support logistique",
            database_session.scalars(
                select(LogisticsSupportRequest).where(
                    LogisticsSupportRequest.id_post == post.id,
                    LogisticsSupportRequest.status.in_(active_statuses),
                )
            ).all(),
        ),
        (
            "Maintenance",
            database_session.scalars(
                select(MaintenanceRequest).where(
                    MaintenanceRequest.id_post == post.id,
                    MaintenanceRequest.status.in_(active_statuses),
                )
            ).all(),
        ),
    )
    for operation_type, requests in request_groups:
        for support_request in requests:
            display_type = operation_type
            if isinstance(support_request, MaintenanceRequest):
                maintenance_type = (
                    "qualité"
                    if support_request.request_type == "QUALITY"
                    else "technique"
                )
                display_type = f"Maintenance {maintenance_type}"
            operations.append(
                {
                    "type": display_type,
                    "reason": support_request.reason,
                    "status": support_request.status.value,
                    "created_at": support_request.created_at,
                }
            )
    operations.sort(key=lambda operation: operation["created_at"], reverse=True)

    return {
        "pieces_count": hourly_record.qty_goods if hourly_record else 0,
        "rejects_count": rejects_count or 0,
        "stops_count": stops_count or 0,
        "supply_count": supply_count or 0,
        "operations": operations,
    }


def _action_result(message: str) -> ResponseReturnValue:
    if request.headers.get("HX-Request"):
        return render_template(
            "fragments/dashboard.html",
            post=g.post,
            message=message,
            **_dashboard_context(g.post),
        )
    return _message(message)


def _hourly_record(post: Posts) -> PostHours:
    database_session = _database_session()
    recorded_at = _current_hour()
    record = database_session.scalar(
        select(PostHours).where(
            PostHours.id_post == post.id,
            PostHours.recorded_at == recorded_at,
        )
    )
    if record is None:
        record = PostHours(
            id_post=post.id,
            recorded_at=recorded_at,
            qty_goods=0,
            qty_bads=0,
            bads_meta={"causes": []},
        )
        database_session.add(record)
    return record


@production_blueprint.post("/pieces")
@_require_post_context()
def record_pieces() -> ResponseReturnValue:
    """Enregistre le nombre de pièces réalisées pour le poste actif."""
    quantity = _form_int("quantity")
    if quantity <= 0:
        return _message("La quantité doit être positive.", 400)
    record = _hourly_record(g.post)
    record.qty_goods = (record.qty_goods or 0) + quantity
    _database_session().commit()
    return _action_result("Pièces réalisées enregistrées.")


@production_blueprint.post("/rebuts")
@_require_post_context()
def record_rejects() -> ResponseReturnValue:
    """Enregistre le nombre de rebuts pour le poste actif."""
    quantity = _form_int("quantity")
    cause = request.form.get("cause", "").strip()
    if quantity <= 0 or not cause:
        return _message("Une quantité positive et une cause sont requises.", 400)
    record = _hourly_record(g.post)
    record.qty_bads = (record.qty_bads or 0) + quantity
    metadata = record.bads_meta or {"causes": []}
    metadata.setdefault("causes", []).append({"cause": cause, "quantity": quantity})
    record.bads_meta = metadata
    _database_session().commit()
    return _action_result("Rebuts enregistrés.")


@production_blueprint.post("/arrets")
@_require_post_context()
def record_stop() -> ResponseReturnValue:
    """Enregistre un arrêt de production pour le poste actif."""
    cause = request.form.get("cause", "").strip()
    try:
        started_at = datetime.fromisoformat(request.form["start_datetime"])
        ended_at = datetime.fromisoformat(request.form["end_datetime"])
    except (KeyError, ValueError):
        return _message("Les dates de début et de fin sont invalides.", 400)
    if not cause or ended_at <= started_at:
        return _message("La cause et une durée positive sont requises.", 400)
    _database_session().add(
        PostStops(
            id_post=g.post.id,
            start_datetime=started_at,
            end_datetime=ended_at,
            stop_meta={"cause": cause},
        )
    )
    _database_session().commit()
    return _action_result("Arrêt de production enregistré.")


def _record_comment(author_type: CommentAuthorType) -> ResponseReturnValue:
    """Enregistre un commentaire pour le poste actif."""
    content = request.form.get("content", "").strip()
    if not content:
        return _message("Le commentaire ne peut pas être vide.", 400)
    _database_session().add(
        ProductionComment(id_post=g.post.id, author_type=author_type, content=content)
    )
    _database_session().commit()
    return _message("Commentaire enregistré.")


@production_blueprint.post("/commentaires-operateurs")
@_require_post_context()
def record_operator_comment() -> ResponseReturnValue:
    """Enregistre un commentaire opérateur pour le poste actif."""
    return _record_comment(CommentAuthorType.OPERATOR)


@production_blueprint.post("/commentaires-techniciens")
@_require_post_context()
def record_technician_comment() -> ResponseReturnValue:
    """Enregistre un commentaire technicien pour le poste actif."""
    return _record_comment(CommentAuthorType.TECHNICIAN)


@production_blueprint.get("/approvisionnement")
def supplies() -> str:
    """Affiche la page des demandes d'approvisionnement pour le poste actif."""
    id_post = request.args.get("id_post", type=int)
    if id_post is None or session.get("id_post") != id_post:
        _abort_message("Le poste transmis ne correspond pas à cette console.", 403)
    database_session = _database_session()
    post = database_session.get(Posts, id_post)
    if post is None:
        _abort_message("Poste introuvable.", 404)
    materials = database_session.scalars(
        select(Materials)
        .join(MaterialOF, MaterialOF.id_material == Materials.id)
        .where(MaterialOF.id_of == post.id_of)
        .order_by(Materials.ref)
    ).all()
    supply_requests = database_session.scalars(
        select(SupplyRequest)
        .where(SupplyRequest.id_post == post.id)
        .order_by(SupplyRequest.created_at.desc())
    ).all()
    return render_template(
        "supplies.html", post=post, materials=materials, supply_requests=supply_requests
    )


@production_blueprint.post("/appro")
@_require_post_context()
def create_supply_request() -> ResponseReturnValue:
    """Crée une nouvelle demande d'approvisionnement pour le poste actif."""
    id_material = _form_int("id_material")
    database_session = _database_session()
    is_material_allowed = database_session.scalar(
        select(MaterialOF.id).where(
            MaterialOF.id_of == g.post.id_of,
            MaterialOF.id_material == id_material,
        )
    )
    if is_material_allowed is None:
        return _message("Ce matériel n'est pas rattaché à l'OF du poste.", 400)
    database_session.add(SupplyRequest(id_post=g.post.id, id_material=id_material))
    database_session.commit()

    if request.headers.get("HX-Request"):
        post = g.post
        materials = database_session.scalars(
            select(Materials)
            .join(MaterialOF, MaterialOF.id_material == Materials.id)
            .where(MaterialOF.id_of == post.id_of)
            .order_by(Materials.ref)
        ).all()
        supply_requests = database_session.scalars(
            select(SupplyRequest)
            .where(SupplyRequest.id_post == post.id)
            .order_by(SupplyRequest.created_at.desc())
        ).all()
        return render_template(
            "fragments/supply_requests.html",
            post=post,
            materials=materials,
            supply_requests=supply_requests,
        )

    return _message("Demande d'approvisionnement créée.")


@production_blueprint.post("/appro/escalade")
@_require_post_context()
def escalate_supply_request() -> ResponseReturnValue:
    """Augmente le niveau de priorité d'une demande d'approvisionnement pour le poste actif."""
    supply_request = _database_session().get(SupplyRequest, _form_int("id_request"))
    if supply_request is None or supply_request.id_post != g.post.id:
        return _message("Demande d'approvisionnement introuvable.", 404)
    priorities = [SupplyPriority.NORMAL, SupplyPriority.URGENT, SupplyPriority.RUPTURE]
    priority_index = priorities.index(supply_request.priority)
    if priority_index == len(priorities) - 1:
        return _message("La demande est déjà au niveau de priorité maximal.", 400)
    supply_request.priority = priorities[priority_index + 1]
    _database_session().commit()

    if request.headers.get("HX-Request"):
        post = g.post
        materials = _database_session().scalars(
            select(Materials)
            .join(MaterialOF, MaterialOF.id_material == Materials.id)
            .where(MaterialOF.id_of == post.id_of)
            .order_by(Materials.ref)
        ).all()
        supply_requests = _database_session().scalars(
            select(SupplyRequest)
            .where(SupplyRequest.id_post == post.id)
            .order_by(SupplyRequest.created_at.desc())
        ).all()
        return render_template(
            "fragments/supply_requests.html",
            post=post,
            materials=materials,
            supply_requests=supply_requests,
        )

    return _message("Priorité de la demande augmentée.")


def _create_post_request(
    request_model: type[Any], message: str
) -> ResponseReturnValue:
    """Crée une nouvelle requête pour le poste actif avec un motif fourni."""
    reason = request.form.get("reason", "").strip()
    if not reason:
        return _message("Un motif est requis.", 400)
    _database_session().add(request_model(id_post=g.post.id, reason=reason))
    _database_session().commit()
    return _action_result(message)


@production_blueprint.post("/support/qualite")
@_require_post_context()
def request_quality_support() -> ResponseReturnValue:
    """Crée une nouvelle demande de support qualité pour le poste actif."""
    return _create_post_request(QualitySupportRequest, "Demande de support qualité créée.")


@production_blueprint.post("/support/logistique")
@_require_post_context()
def request_logistics_support() -> ResponseReturnValue:
    """Crée une nouvelle demande de support logistique pour le poste actif."""
    return _create_post_request(LogisticsSupportRequest, "Demande de support logistique créée.")


def _create_maintenance_request(request_type: str) -> ResponseReturnValue:
    """Crée une nouvelle demande de maintenance pour le poste actif avec un type spécifié."""
    reason = request.form.get("reason", "").strip()
    if not reason:
        return _message("Un motif est requis.", 400)
    _database_session().add(
        MaintenanceRequest(id_post=g.post.id, reason=reason, request_type=request_type)
    )
    _database_session().commit()
    return _action_result("Demande de maintenance créée.")


@production_blueprint.post("/maintenance/qualite")
@_require_post_context()
def request_quality_maintenance() -> ResponseReturnValue:
    """Crée une nouvelle demande de maintenance qualité pour le poste actif."""
    return _create_maintenance_request("QUALITY")


@production_blueprint.post("/maintenance/technique")
@_require_post_context()
def request_technical_maintenance() -> ResponseReturnValue:
    """Crée une nouvelle demande de maintenance technique pour le poste actif."""
    return _create_maintenance_request("TECHNICAL")


def _database_url(database_url: str | None) -> str | URL:
    configured_url = database_url or os.environ.get("DATABASE_URL")
    if configured_url:
        return configured_url
    required_settings = (
        "POSTGRES_USER_APP",
        "POSTGRES_PASSWORD_APP",
        "POSTGRES_DB_MAIN",
    )
    missing_settings = [key for key in required_settings if not os.environ.get(key)]
    if missing_settings:
        missing = ", ".join(missing_settings)
        raise RuntimeError(f"Variables d'environnement manquantes : {missing}.")
    return URL.create(
        "postgresql+psycopg2",
        username=os.environ["POSTGRES_USER_APP"],
        password=os.environ["POSTGRES_PASSWORD_APP"],
        host=os.environ.get("POSTGRES_HOST", "db-main"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ["POSTGRES_DB_MAIN"],
    )


def create_app(database_url: str | None = None) -> Flask:
    """Crée l'application Flask de l'API Production."""
    flask_app = Flask(__name__, static_url_path="/production/assets")
    flask_app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "")
    if not flask_app.config["SECRET_KEY"]:
        raise RuntimeError("La variable d'environnement FLASK_SECRET_KEY est requise.")
    engine = create_engine(_database_url(database_url), pool_pre_ping=True)
    flask_app.extensions["session_factory"] = sessionmaker(bind=engine)
    csrf.init_app(flask_app)

    @flask_app.errorhandler(CSRFError)
    def handle_csrf_error(error: CSRFError) -> tuple[str, int]:
        return _message(error.description or "Jeton CSRF invalide.", 400)

    @flask_app.teardown_appcontext
    def close_database_session(_: BaseException | None) -> None:
        database_session = g.pop("database_session", None)
        if database_session is not None:
            database_session.close()

    flask_app.register_blueprint(production_blueprint)

    @flask_app.get("/")
    def service_root() -> WerkzeugResponse:
        return redirect(url_for("production.home"))

    register_environment_navigation(flask_app, "production")
    return flask_app


app = create_app()
