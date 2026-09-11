"""Modèle de données pour les matériaux.

Contient :
    - la classe Material représentant un matériau avec ses attributs et relations.
    - la classe MaterialOF représentant la relation entre un matériau et un ordre de fabrication.

"""
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped

from .. import WorkingBase
from .common import QueryMixin

class Material(WorkingBase, QueryMixin):
    """
    Modèle de données pour les matériaux.

    Arguments:
        id (int): Identifiant unique du matériel.
        name (str): Nom du matériau.
        ref (str): Référence du matériau.
        description (str): Description du matériau.
    """
    __tablename__ = "materials"
    __mapper_args__ = {
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


class MaterialOF(WorkingBase, QueryMixin):
    """
    Modèle de données pour la relation entre un matériau et un ordre de fabrication.

    Arguments:
        id (int): Identifiant unique de la relation.
        id_material (int): Identifiant du matériau.
        id_of (int): Identifiant de l'ordre de fabrication.
    """
    __tablename__ = "materials_of"
    __mapper_args__ = {
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
        ForeignKey("app_schema.of.id"),
        nullable=False,
    )
