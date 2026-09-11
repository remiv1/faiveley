"""Modèle de données pour les utilisateurs. Contient 2 classes :
- Users : Représente un utilisateur avec ses données de base et ses permissions.
- UsersPasswords : Représente les mots de passe des utilisateurs, avec une relation vers
    la classe Users. Permet de gérer l'historique des mots de passe et leur validité.
"""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from sqlalchemy.dialects.postgresql import JSONB

from .. import WorkingBase
from .common import QueryMixin

if TYPE_CHECKING:
    from .machines import Machines
    from .articles import Articles

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
        ForeignKey('app_schema.article.id'),
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
    article: Mapped["Articles"] = relationship(
        "Articles",
        uselist=False,
        back_populates="ordre_fabrication",
    )
