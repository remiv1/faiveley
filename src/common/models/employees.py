"""Modèle de données pour les employés.

Contient la classe Employees représentant un employé avec ses attributs et relations.
"""
from typing import Any, TYPE_CHECKING
from datetime import datetime
from enum import Enum

from sqlalchemy import Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import mapped_column, Mapped, relationship

from .. import WorkingBase
from .common import QueryMixin

if TYPE_CHECKING:
    from .posts import Posts

class JobTitleEnum(str, Enum):
    """Enumération des postes de travail possibles pour un employé."""
    MANUTENTIONNAIRE = "MANUTENTIONNAIRE"
    PRODUCTEUR = "PRODUCTEUR"
    SUPERVISEUR = "SUPERVISEUR"
    ADMINISTRATEUR = "ADMINISTRATEUR"

class DepartmentEnum(str, Enum):
    """Enumération des départements possibles pour un employé."""
    PRODUCTION = "PRODUCTION"
    LOGISTIQUE = "LOGISTIQUE"
    RH = "RH"
    IT = "IT"
    ADMINISTRATION = "ADMINISTRATION"

class Employees(WorkingBase, QueryMixin):
    """
    Modèle de données pour un employé.
    
    Arguments:
        id (int): Identifiant unique de l'employé.
        first_name (str): Prénom de l'employé.
        last_name (str): Nom de l'employé.
        email (str): Adresse email de l'employé.
        is_manager (bool): Indique si l'employé est un manager.
        phone (str, optional): Numéro de téléphone de l'employé.
        hire_date (datetime, optional): Date d'embauche de l'employé.
        quit_date (datetime, optional): Date de départ de l'employé.
        job_title (enum[JobTitleEnum]): Poste de l'employé.
        department (enum[DepartmentEnum]): Département de l'employé.
        manager_id (int, optional): Identifiant du manager de l'employé.
    """

    __tablename__ = "employees"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    first_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    last_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
    )
    auth_user_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    is_manager: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )
    phone: Mapped[str] = mapped_column(
        String,
        nullable=True,
    )
    hire_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    quit_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    job_title: Mapped[str] = mapped_column(
        SQLEnum(
            JobTitleEnum,
            name="job_title_enum",
            create_type=True,
        ),
        nullable=False,
    )
    department: Mapped[str] = mapped_column(
        SQLEnum(
            DepartmentEnum,
            name="department_enum",
            create_type=True,
        ),
        nullable=False,
    )
    manager_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.employees.id"),
        nullable=True,
    )
    manager: Mapped["Employees"] = relationship(
        "Employees",
        remote_side=[id],
        backref="subordinates",
    )
    posts_as_manager: Mapped[list["Posts"]] = relationship(
        "Posts",
        back_populates="manager",
        foreign_keys="Posts.id_manager",
    )
    posts_as_employee: Mapped[list["Posts"]] = relationship(
        "Posts",
        back_populates="employee",
        foreign_keys="Posts.id_employee",
    )

    def __repr__(self) -> str:
        return (f"<Employees(id={self.id}, " +
               f"first_name={self.first_name}, " +
               f"last_name={self.last_name}, " +
               f"email={self.email}, " +
               f"job_title={self.job_title}, " +
               f"department={self.department}, " +
               f"is_manager={self.is_manager})>"
        )

    def full_name(self) -> str:
        """Retourne le nom complet de l'employé."""
        return f"{self.first_name} {self.last_name}"

    def to_dict(self) -> dict[str, Any]:
        """Retourne un dictionnaire représentant l'employé."""
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "auth_user_id": self.auth_user_id,
            "is_manager": self.is_manager,
            "phone": self.phone,
            "hire_date": self.hire_date,
            "quit_date": self.quit_date,
            "job_title": self.job_title,
            "department": self.department,
            "manager_id": self.manager_id,
            "full_name": self.full_name(),
        }
