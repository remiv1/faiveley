"""Modèle de données pour les articles. Contient la classe :

- Articles : Représente un article avec ses données de base et ses caractéristiques.
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

class Articles(WorkingBase, QueryMixin):
    """
    Modèle représentant un article.

    Attributs :
        id (int): Identifiant unique de l'article.
        name (str): Nom de l'article.
        description (str): Description de l'article.
        client (str): Nom du client associé à l'article.
        product (str): Nom du produit associé à l'article.
        date_creation (datetime): Date de création de l'article.
        date_modification (datetime): Date de dernière modification de l'article.
        article_meta (jsonb): Métadonnées supplémentaires de l'article.
    """
    __tablename__ = 'article'
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
    client: Mapped[str] = mapped_column(
        String,
        nullable=True,
    )
    product: Mapped[str] = mapped_column(
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
    article_meta: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=True,
    )

    ordre_fabrication: Mapped["OrdreFabrication"] = relationship(
        "OrdreFabrication",
        uselist=False,
        back_populates="ordre_fabrication",
    )
