"""Modèle de données pour les machines. Contient la classe :

- Machines : Représente une machine avec ses données de base et ses caractéristiques.
"""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.dialects.postgresql import JSONB

from .. import WorkingBase
from .common import QueryMixin

if TYPE_CHECKING:
    from .ordre_fabrication import OrdreFabrication

class Machines(WorkingBase, QueryMixin):
    """
    Modèle représentant une machine.

    Attributs :
        id (int): Identifiant unique de la machine.
        name (str): Nom de la machine.
        description (str): Description de la machine.
        date_creation (datetime): Date de création de la machine.
        date_modification (datetime): Date de dernière modification de la machine.
        location (jsonb): Localisation de la machine : position, row, column.
        machine_meta (jsonb): Métadonnées supplémentaires de la machine.
    """
    __tablename__ = 'machines'
    __table_args__ = {'schema': 'app_schema'}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        String,
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
    location: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=True,
    )
    machine_meta: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=True,
    )
    ordre_fabrication: Mapped[list["OrdreFabrication"]] = relationship(
        "OrdreFabrication",
        back_populates="machine",
    )

    def __repr__(self) -> str:
        return (f"<Machines(id={self.id}, " +
               f"name={self.name}, " +
               f"description={self.description}, " +
               f"date_creation={self.date_creation}, " +
               f"date_modification={self.date_modification}, " +
               f"location={self.location}, " +
               f"machine_meta={self.machine_meta})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Retourne un dictionnaire représentant la machine."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "date_creation": self.date_creation,
            "date_modification": self.date_modification,
            "location": self.location,
            "machine_meta": self.machine_meta,
        }
