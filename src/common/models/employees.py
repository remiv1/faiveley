"""Modèle de données pour les employés.

Contient la classe Employees représentant un employé avec ses attributs et relations.
"""
from datetime import datetime

from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from .. import WorkingBase
from .common import QueryMixin

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
        job_title (str): Poste de l'employé.
        department (str, optional): Département de l'employé.
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
        String,
        nullable=False,
    )
    department: Mapped[str] = mapped_column(
        String,
        nullable=True,
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
