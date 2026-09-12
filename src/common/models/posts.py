"""Modèle de données pour les opérateurs postés.

Contient la classe Post représentant un opérateur posté avec ses attributs et relations.
"""

from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from sqlalchemy import Integer, DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped, relationship

from .. import WorkingBase
from .common import QueryMixin

if TYPE_CHECKING:
    from .employees import Employees
    from .ordre_fabrication import OrdreFabrication
    from .production import (
        LogisticsSupportRequest,
        MaintenanceRequest,
        ProductionComment,
        QualitySupportRequest,
        SupplyRequest,
    )

class Posts(WorkingBase, QueryMixin):
    """
    Modèle de données pour les postes opérateurs.

    Arguments:
        id (int): Identifiant unique du poste.
        id_employee (int): Identifiant de l'employé associé au poste.
        id_manager (int): Identifiant du manager associé au poste.
        id_of (int): Identifiant de l'ordre de fabrication associé au poste.
        start_datetime (datetime): Date et heure de début du poste.
        end_datetime (datetime, optional): Date et heure de fin du poste.
        created_at (datetime): Date et heure de création du poste.
        updated_at (datetime, optional): Date et heure de la dernière mise à jour du poste.
    """
    __tablename__ = "posts"
    __table_args__ = {
        "schema": "app_schema"
    }

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    id_employee: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.employees.id"),
        nullable=False,
    )
    id_manager: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.employees.id"),
        nullable=False,
    )
    id_of: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.ordre_fabrication.id"),
        nullable=False,
    )
    press_ref: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    start_datetime: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    end_datetime: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=True,
    )

    employee: Mapped["Employees"] = relationship(
        "Employees",
        uselist=False,
        back_populates="posts_as_employee",
        foreign_keys=[id_employee],
    )
    manager: Mapped["Employees"] = relationship(
        "Employees",
        uselist=False,
        back_populates="posts_as_manager",
        foreign_keys=[id_manager],
    )
    ordre_fabrication: Mapped["OrdreFabrication"] = relationship(
        "OrdreFabrication",
        uselist=False,
        back_populates="posts",
    )
    post_hours: Mapped[list["PostHours"]] = relationship(
        "PostHours",
        back_populates="post",
    )
    post_stops: Mapped[list["PostStops"]] = relationship(
        "PostStops",
        back_populates="post",
    )
    production_comments: Mapped[list["ProductionComment"]] = relationship(
        "ProductionComment",
        back_populates="post",
    )
    supply_requests: Mapped[list["SupplyRequest"]] = relationship(
        "SupplyRequest",
        back_populates="post",
    )
    quality_support_requests: Mapped[list["QualitySupportRequest"]] = relationship(
        "QualitySupportRequest",
        back_populates="post",
    )
    logistics_support_requests: Mapped[list["LogisticsSupportRequest"]] = relationship(
        "LogisticsSupportRequest",
        back_populates="post",
    )
    maintenance_requests: Mapped[list["MaintenanceRequest"]] = relationship(
        "MaintenanceRequest",
        back_populates="post",
    )

    def __repr__(self) -> str:
        return (
            f"<Posts(id={self.id}, "
            f"id_employee={self.id_employee}, "
            f"id_manager={self.id_manager}, "
            f"id_of={self.id_of})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convertit l'objet Posts en dictionnaire.

        Retourne :
            dict[str, Any]: Dictionnaire contenant les attributs du poste.
        """
        return {
            "id": self.id,
            "id_employee": self.id_employee,
            "id_manager": self.id_manager,
            "id_of": self.id_of,
            "press_ref": self.press_ref,
            "start_datetime": self.start_datetime,
            "end_datetime": self.end_datetime,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class PostHours(WorkingBase, QueryMixin):
    """
    Modèle représentant les heures de travail associées à un poste.

    Attributs :
        id (int) : Identifiant unique de l'enregistrement des heures.
        id_post (int) : Identifiant du poste associé.
        capacities (int) : Cadence de production du poste pour cette période.
        qty_goods (int) : Quantité de pièces bonnes produites pendant cette période.
        qty_bads (int) : Quantité de pièces défectueuses produites pendant cette période.
        bads_meta (jsonb, optional) : Métadonnées des pièces défectueuses produites pendant
        cette période.
    """
    __tablename__ = "post_hours"
    __table_args__ = (
        UniqueConstraint(
            "id_post",
            "recorded_at",
            name="uq_post_hours_post_recorded_at",
        ),
        {"schema": "app_schema"},
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    id_post: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.posts.id"),
        nullable=False,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    capacities: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
    )
    qty_goods: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
    )
    qty_bads: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
    )
    bads_meta: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=True,
    )
    post: Mapped["Posts"] = relationship(
        "Posts",
        uselist=False,
        back_populates="post_hours",
    )

    def __repr__(self) -> str:
        return (
            f"<PostHours(id={self.id}, id_post={self.id_post}, capacities={self.capacities}, "
            f"qty_goods={self.qty_goods}, qty_bads={self.qty_bads}, bads_meta={self.bads_meta})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convertit l'objet PostHours en dictionnaire.

        Retourne :
            dict[str, Any]: Dictionnaire contenant les attributs de l'heure de travail.
        """
        return {
            "id": self.id,
            "id_post": self.id_post,
            "capacities": self.capacities,
            "qty_goods": self.qty_goods,
            "qty_bads": self.qty_bads,
            "bads_meta": self.bads_meta,
        }


class PostStops(WorkingBase, QueryMixin):
    """
    Modèle représentant les arrêts de travail associés à un poste.

    Attributs :
        id (int) : Identifiant unique de l'arrêt.
        id_post (int) : Identifiant du poste associé.
        start_datetime (datetime) : Date et heure de début de l'arrêt.
        end_datetime (datetime, optional) : Date et heure de fin de l'arrêt.
        stop_meta (jsonb, optional) : Métadonnées supplémentaires concernant l'arrêt.
    """
    __tablename__ = "post_stops"
    __table_args__ = {
        "schema": "app_schema"
    }
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    id_post: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.posts.id"),
        nullable=False,
    )
    start_datetime: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    end_datetime: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True,
    )
    stop_meta: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=True,
    )
    post: Mapped["Posts"] = relationship(
        "Posts",
        uselist=False,
        back_populates="post_stops",
    )

    def __repr__(self) -> str:
        return (
            f"<PostStops(id={self.id}, "
            f"id_post={self.id_post}, "
            f"start_datetime={self.start_datetime}, "
            f"end_datetime={self.end_datetime}, "
            f"stop_meta={self.stop_meta})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convertit l'objet PostStops en dictionnaire.

        Retourne :
            dict[str, Any]: Dictionnaire contenant les attributs de l'arrêt de travail.
        """
        return {
            "id": self.id,
            "id_post": self.id_post,
            "start_datetime": self.start_datetime,
            "end_datetime": self.end_datetime,
            "stop_meta": self.stop_meta,
        }
