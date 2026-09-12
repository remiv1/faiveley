"""Modèle de données pour le matériel.

Contient :
    - la classe Materials représentant le matériel avec ses attributs et relations.
    - la classe MaterialOF représentant la relation entre le matériel et un ordre de fabrication.

"""
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .. import WorkingBase
from .common import QueryMixin

if TYPE_CHECKING:
    from .ordre_fabrication import OrdreFabrication
    from .production import SupplyRequest


class Materials(WorkingBase, QueryMixin):
    """
    Modèle de données pour le matériel.

    Arguments:
        id (int): Identifiant unique du matériel.
        name (str): Nom du matériel.
        ref (str): Référence du matériel.
        description (str): Description du matériel.
    """
    __tablename__ = "materials"
    __table_args__ = {
        "schema": "app_schema"
    }

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    ref: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        String,
        nullable=True,
    )
    ordre_fabrication: Mapped[list["OrdreFabrication"]] = relationship(
        "OrdreFabrication",
        secondary="app_schema.materials_of",
        back_populates="materials",
    )
    supply_requests: Mapped[list["SupplyRequest"]] = relationship(
        "SupplyRequest",
        back_populates="material",
    )

    def __repr__(self) -> str:
        return f"<Materials(id={self.id}, name={self.name})>"

    def to_dict(self) -> dict[str, Any]:
        """
        Convertit l'objet Materials en dictionnaire.

        Retourne :
            dict[str, Any]: Dictionnaire contenant les attributs du matériel.
        """
        return {
            "id": self.id,
            "name": self.name,
            "ref": self.ref,
            "description": self.description,
        }


class MaterialOF(WorkingBase, QueryMixin):  # pylint: disable=R0903
    """
    Modèle de données pour la relation entre le matériel et un ordre de fabrication.

    Arguments:
        id (int): Identifiant unique de la relation.
        id_material (int): Identifiant du matériel.
        id_of (int): Identifiant de l'ordre de fabrication.
    """
    __tablename__ = "materials_of"
    __table_args__ = {
        "schema": "app_schema"
    }

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    id_material: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.materials.id"),
        nullable=False,
    )
    id_of: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.ordre_fabrication.id"),
        nullable=False,
    )
