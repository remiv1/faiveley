"""Module commun pour les objets de données SQLAlchemy."""

from typing import Any, TypeVar, Type
from sqlalchemy import select
from sqlalchemy.sql import Select

T = TypeVar("T", bound="QueryMixin")


class QueryMixin:   # pylint: disable=R0903
    """Mixin pour ajouter une méthode de requête générique à un modèle SQLAlchemy."""

    @classmethod
    def by(cls: Type[T], **filters: Any) -> Select[Any]:
        """Récupère un enregistrement en fonction de filtres dynamiques.
        Args:
            **filters: Filtres sous forme de paramètres nommés.
        Returns:
            Select[Any]: Le constructeur de requête SQLAlchemy pour la requête.
        """
        return select(cls).filter_by(**filters)
