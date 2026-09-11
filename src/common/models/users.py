"""Modèle de données pour les utilisateurs. Contient 2 classes :
- Users : Représente un utilisateur avec ses données de base et ses permissions.
- UsersPasswords : Représente les mots de passe des utilisateurs, avec une relation vers
    la classe Users. Permet de gérer l'historique des mots de passe et leur validité.
"""

from typing import Dict, Any
from datetime import datetime, timezone

from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from .. import SecureBase
from .common import QueryMixin

CASCADE_OPTIONS = "all, delete-orphan"
ADMIN = "1"
COMPTABLE = "2"
COMMERCIAL = "3"
LOGISTIQUE = "4"
SUPPORT = "5"
INFORMATIQUE = "6"
RH = "7"
DIRECTION = "8"
SUPER_ADMIN = "9"


class Users(SecureBase, QueryMixin):
    """
    Modèle pour les utilisateurs. Contient les méthodes :
        - __repr__ : Représentation textuelle de l'utilisateur.
        - to_dict : Convertit l'objet User en dictionnaire.
        - from_dict : Crée un objet User à partir d'un dictionnaire.
        - by : Permet de faire des requêtes personnalisées sur les utilisateurs.
    """

    __tablename__ = "users"
    __table_args__ = {"schema": "auth_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique de l'utilisateur",
    )

    # Données de base de l'utilisateur
    username: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, comment="Nom d'utilisateur"
    )
    email: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, comment="Adresse email de l'utilisateur"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="Utilisateur actif ?"
    )
    nb_failed_logins: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Nombre de tentatives de connexion échouées",
    )
    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Compte de l'utilisateur verrouillé ?",
    )
    # La gestion des droits se fait par une chaine de caractères avec des nombres accolés
    # Par exemple "1" admin, "2" comptable, "3" commercial, "4" logistique, "5" support,
    # "6" informatique, "7" RH, "8" direction, "9" super admin
    # Exemple : "13" pour un utilisateur qui est à la fois admin et commercial
    permissions: Mapped[str] = mapped_column(
        String, comment="Permissions de l'utilisateur"
    )

    # Méta-données de suivi
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création de l'utilisateur",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date de dernière MàJ de l'utilisateur",
    )

    # Relations
    passwords = relationship(
        "UsersPasswords", back_populates="user", cascade=CASCADE_OPTIONS
    )
    sessions = relationship(
        "UserSession", back_populates="user", cascade=CASCADE_OPTIONS
    )

    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, username={self.username}, email={self.email}, "
            f"is_active={self.is_active})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet User en dictionnaire."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "nb_failed_logins": self.nb_failed_logins,
            "is_locked": self.is_locked,
            "permissions": self.permissions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Users":
        """Crée un objet User à partir d'un dictionnaire."""
        return cls(**data)


class UserSession(SecureBase):  # pylint: disable=R0903
    """Session authentifiée associée à un utilisateur."""

    __tablename__ = "user_sessions"
    __table_args__ = {"schema": "auth_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique de la session",
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        comment="Empreinte SHA-256 du jeton de session",
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("auth_schema.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Identifiant de l'utilisateur associé",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Date d'expiration absolue de la session",
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de dernière activité de la session",
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date de révocation de la session",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création de la session",
    )

    user = relationship("Users", back_populates="sessions")

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet UserSession en dictionnaire."""
        return {
            "id": self.id,
            "token_hash": self.token_hash,
            "user_id": self.user_id,
            "expires_at": self.expires_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat(),
            "revoked_at": self.revoked_at.isoformat()
            if self.revoked_at
            else None,
            "created_at": self.created_at.isoformat(),
        }


class UsersPasswords(SecureBase):
    """
    Modèle pour les mots de passe des utilisateurs.
    Contient les méthodes :
        - __repr__ : Représentation textuelle du mot de passe.
        - to_dict : Convertit l'objet UserPassword en dictionnaire.
    """

    __table_args__ = {"schema": "auth_schema"}
    __tablename__ = "users_passwords"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique du mot de passe",
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("auth_schema.users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Identifiant de l'utilisateur associé",
    )
    password_hash: Mapped[str] = mapped_column(
        String, nullable=False, comment="Hash du mot de passe de l'utilisateur"
    )
    from_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de début de validité du mot de passe",
    )
    to_date: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="Date fin de validité du mot de passe"
    )

    # Méta-données de suivi
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création du mot de passe",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date de dernière MàJ du mot de passe",
    )

    # Relations
    user = relationship("Users", back_populates="passwords")

    def __repr__(self) -> str:
        return f"<UserPassword(id={self.id}, user_id={self.user_id})>"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'objet UserPassword en dictionnaire.
        Returns:
            Dict[str, Any]: Un dictionnaire représentant l'objet UserPassword.
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "from_date": self.from_date.isoformat() if self.from_date else None,
            "to_date": self.to_date.isoformat() if self.to_date else None,
        }
