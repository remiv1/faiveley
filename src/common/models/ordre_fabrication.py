"""Modèle de données pour les utilisateurs. Contient 2 classes :
- Users : Représente un utilisateur avec ses données de base et ses permissions.
- UsersPasswords : Représente les mots de passe des utilisateurs, avec une relation vers
    la classe Users. Permet de gérer l'historique des mots de passe et leur validité.
"""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Enum as SQLEnum, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from sqlalchemy.dialects.postgresql import JSONB

from .. import WorkingBase
from .common import QueryMixin

if TYPE_CHECKING:
    from .machines import Machines
    from .articles import Articles
    from .materials import Materials
    from .posts import Posts


class OrdreFabricationStatus(str, Enum):
    """Statut du cycle de vie d'un ordre de fabrication."""

    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class OrdreFabrication(WorkingBase, QueryMixin):
    """
    Modèle représentant un ordre de fabrication.

    Attributs :
        id (int): Identifiant unique de l'ordre de fabrication.
        id_article (int): Identifiant de l'article.
        id_machine (int): Identifiant de la machine.
        code (str): Code de l'ordre de fabrication.
        capacities (int): Cadence de production de l'ordre de fabrication.
        date_creation (datetime): Date de création de l'ordre de fabrication.
        date_modification (datetime): Date de dernière modification de l'ordre de fabrication.
        of_meta (jsonb): Métadonnées supplémentaires de l'ordre de fabrication.
    """
    __tablename__ = 'ordre_fabrication'
    __table_args__ = {'schema': 'app_schema'}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    id_article: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('app_schema.articles.id'),
        nullable=False,
    )
    id_machine: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('app_schema.machines.id'),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    capacities: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
    )
    status: Mapped[OrdreFabricationStatus] = mapped_column(
        SQLEnum(OrdreFabricationStatus, name="ordre_fabrication_status_enum"),
        nullable=False,
        default=OrdreFabricationStatus.PLANNED,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.now(timezone.utc),
    )
    date_modification: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    of_meta: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=True,
    )

    machine: Mapped["Machines"] = relationship(
        "Machines",
        uselist=False,
        back_populates="ordre_fabrication",
    )
    articles: Mapped["Articles"] = relationship(
        "Articles",
        uselist=False,
        back_populates="ordre_fabrication",
    )
    materials: Mapped[list["Materials"]] = relationship(
        "Materials",
        secondary="app_schema.materials_of",
        back_populates="ordre_fabrication",
    )
    posts: Mapped[list["Posts"]] = relationship(
        "Posts",
        back_populates="ordre_fabrication",
    )

    def __repr__(self) -> str:
        return f"<OrdreFabrication(id={self.id}, code={self.code})>"

    def to_dict(self) -> dict[str, Any]:
        """
        Convertit l'objet OrdreFabrication en dictionnaire.

        Retourne :
            dict[str, Any]: Dictionnaire contenant les attributs de l'ordre de fabrication.
        """
        return {
            "id": self.id,
            "id_article": self.id_article,
            "id_machine": self.id_machine,
            "code": self.code,
            "capacities": self.capacities,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "date_creation": self.date_creation,
            "date_modification": self.date_modification,
            "of_meta": self.of_meta,
        }
