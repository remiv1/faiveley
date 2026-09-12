"""
Modèles pour les contrôles qualité de pièces de production
"""

from typing import Any, TYPE_CHECKING

from sqlalchemy import Integer, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common import WorkingBase
from common.models.common import QueryMixin

if TYPE_CHECKING:
    from common.models.posts import Posts

class Controls(WorkingBase, QueryMixin):
    """
    Modèle représentant les autocontrôles qualité des pièces de production

    Attributs :
        id (int) : Identifiant unique du contrôle
        id_post (int) : Identifiant du poste de travail associé
        spec (bool) : Présence des spécifications sur le poste de travail
        panoplie (bool) : Présence de la panoplie sur le poste de travail
        panoplie_listing (bool) : Présence de la liste de la panoplie sur le poste de travail
        gabarits (bool) : Présence des gabarits sur le poste de travail
    """
    __tablename__ = "controls"
    __table_args__ = {'schema': 'app_schema'}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    id_post: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.posts.id"),
    )
    spec: Mapped[bool] = mapped_column(
        Boolean,
        nullable=True,
    )
    panoplie: Mapped[bool] = mapped_column(
        Boolean,
        nullable=True,
    )
    panoplie_listing: Mapped[bool] = mapped_column(
        Boolean,
        nullable=True,
    )
    gabarits: Mapped[bool] = mapped_column(
        Boolean,
        nullable=True,
    )

    post: Mapped["Posts"] = relationship("Posts")
    control_items: Mapped[list["ControlItems"]] = relationship(
        "ControlItems",
        back_populates="control",
        cascade="all, delete-orphan",
        uselist=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Controls(id={self.id}, id_post={self.id_post}, spec={self.spec}, "
            f"panoplie={self.panoplie}, panoplie_listing={self.panoplie_listing}, "
            f"gabarits={self.gabarits})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet Controls en dictionnaire."""
        return {
            "id": self.id,
            "id_post": self.id_post,
            "spec": self.spec,
            "panoplie": self.panoplie,
            "panoplie_listing": self.panoplie_listing,
            "gabarits": self.gabarits,
        }


class ControlItems(WorkingBase, QueryMixin):
    """
    Modèle représentant les éléments de contrôle qualité des pièces de production

    Attributs :
        id (int) : Identifiant unique de l'élément de contrôle
        id_control (int) : Identifiant du contrôle associé
        ref_colis (str) : Référence du colis associé
        view_control (enum) : contrôle visuel
        scale_control (enum) : contrôle dimensionnel
    """
    __tablename__ = "control_items"
    __table_args__ = {'schema': 'app_schema'}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    id_control: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.controls.id"),
    )
    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    value: Mapped[bool] = mapped_column(
        Boolean,
        nullable=True,
    )

    control: Mapped["Controls"] = relationship(
        "Controls",
        foreign_keys=[id_control],
        uselist=False,
        back_populates="control_items",
    )

    def __repr__(self) -> str:
        return (
            f"<ControlItems(id={self.id}, id_control={self.id_control}, name={self.name}, "
            f"value={self.value})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet ControlItems en dictionnaire."""
        return {
            "id": self.id,
            "id_control": self.id_control,
            "name": self.name,
            "value": self.value,
        }
