"""Modèles de persistance propres à l'API de production."""

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .. import WorkingBase
from .common import QueryMixin

if TYPE_CHECKING:
    from .materials import Materials
    from .posts import Posts


class CommentAuthorType(str, Enum):
    """Type d'auteur d'un commentaire de production."""

    OPERATOR = "OPERATOR"
    TECHNICIAN = "TECHNICIAN"


class RequestStatus(str, Enum):
    """Statut de traitement d'une demande."""

    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class SupplyPriority(str, Enum):
    """Priorité d'une demande d'approvisionnement."""

    NORMAL = "NORMAL"
    URGENT = "URGENT"
    RUPTURE = "RUPTURE"


class ProductionComment(WorkingBase, QueryMixin):
    """Commentaire saisi par un opérateur ou un technicien sur un poste."""

    __tablename__ = "production_comments"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_post: Mapped[int] = mapped_column(
        ForeignKey("app_schema.posts.id"), nullable=False
    )
    author_type: Mapped[CommentAuthorType] = mapped_column(
        SQLEnum(CommentAuthorType, name="comment_author_type_enum"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    post: Mapped["Posts"] = relationship(
        "Posts", back_populates="production_comments"
    )


class SupplyRequest(WorkingBase, QueryMixin):
    """Demande d'approvisionnement pour un matériel associé à l'OF d'un poste."""

    __tablename__ = "supply_requests"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_post: Mapped[int] = mapped_column(
        ForeignKey("app_schema.posts.id"), nullable=False
    )
    id_material: Mapped[int] = mapped_column(
        ForeignKey("app_schema.materials.id"), nullable=False
    )
    priority: Mapped[SupplyPriority] = mapped_column(
        SQLEnum(SupplyPriority, name="supply_priority_enum"),
        default=SupplyPriority.NORMAL,
        nullable=False,
    )
    status: Mapped[RequestStatus] = mapped_column(
        SQLEnum(RequestStatus, name="request_status_enum"),
        default=RequestStatus.OPEN,
        nullable=False,
    )
    id_handler_employee: Mapped[int | None] = mapped_column(
        ForeignKey("app_schema.employees.id", ondelete="SET NULL"), nullable=True
    )
    taken_in_charge_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    post: Mapped["Posts"] = relationship("Posts", back_populates="supply_requests")
    material: Mapped["Materials"] = relationship(
        "Materials", back_populates="supply_requests"
    )


class PostRequest(WorkingBase, QueryMixin):
    """Base commune aux demandes de support liées à un poste."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_post: Mapped[int] = mapped_column(
        ForeignKey("app_schema.posts.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RequestStatus] = mapped_column(
        SQLEnum(RequestStatus, name="request_status_enum"),
        default=RequestStatus.OPEN,
        nullable=False,
    )
    id_handler_employee: Mapped[int | None] = mapped_column(
        ForeignKey("app_schema.employees.id", ondelete="SET NULL"), nullable=True
    )
    taken_in_charge_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class QualitySupportRequest(PostRequest):
    """Demande de support qualité liée à un poste."""

    __tablename__ = "quality_support_requests"
    __table_args__ = {"schema": "app_schema"}

    post: Mapped["Posts"] = relationship(
        "Posts", back_populates="quality_support_requests"
    )


class LogisticsSupportRequest(PostRequest):
    """Demande de support logistique liée à un poste."""

    __tablename__ = "logistics_support_requests"
    __table_args__ = {"schema": "app_schema"}

    post: Mapped["Posts"] = relationship(
        "Posts", back_populates="logistics_support_requests"
    )


class MaintenanceRequest(PostRequest):
    """Demande de maintenance qualité ou technique liée à un poste."""

    __tablename__ = "maintenance_requests"
    __table_args__ = {"schema": "app_schema"}

    request_type: Mapped[str] = mapped_column(String, nullable=False)
    post: Mapped["Posts"] = relationship(
        "Posts", back_populates="maintenance_requests"
    )
