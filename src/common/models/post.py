"""Modèle de données pour les opérateurs postés.

Contient la classe Post représentant un opérateur posté avec ses attributs et relations.
"""

from datetime import datetime, timezone

from sqlalchemy import Integer, DateTime, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped

from .. import WorkingBase
from .common import QueryMixin

class Post(WorkingBase, QueryMixin):
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
    __mapper_args__ = {
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
        ForeignKey("app_schema.managers.id"),
        nullable=False,
    )
    id_of: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.of.id"),
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=True,
    )
