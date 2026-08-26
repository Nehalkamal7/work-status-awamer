import enum
import uuid
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def uid(): return str(uuid.uuid4())
def now(): return datetime.utcnow()


class Priority(str, enum.Enum):
    critical = "CRITICAL"; high = "HIGH"; medium = "MEDIUM"; low = "LOW"


class Source(str, enum.Enum):
    local = "LOCAL"; odoo = "ODOO"; google_sheets = "GOOGLE_SHEETS"


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_project_source"), Index("ix_projects_deadline_priority", "deadline", "priority"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(255), index=True)
    client: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    daily_report: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(60), default="ACTIVE", index=True)
    priority: Mapped[Priority] = mapped_column(Enum(Priority), default=Priority.medium, index=True)
    start_date: Mapped[date | None] = mapped_column(Date)
    deadline: Mapped[date | None] = mapped_column(Date, index=True)
    progress: Mapped[float] = mapped_column(Float, default=0)
    assigned_to: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[Source] = mapped_column(Enum(Source), default=Source.local, index=True)
    source_id: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime)
    tasks: Mapped[list["Task"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_task_source"), Index("ix_tasks_deadline_priority", "deadline", "priority"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(60), default="TODO", index=True)
    priority: Mapped[Priority] = mapped_column(Enum(Priority), default=Priority.medium, index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(255), index=True)
    start_date: Mapped[date | None] = mapped_column(Date)
    deadline: Mapped[date | None] = mapped_column(Date, index=True)
    progress: Mapped[float] = mapped_column(Float, default=0)
    estimated_hours: Mapped[float] = mapped_column(Float, default=1)
    actual_hours: Mapped[float] = mapped_column(Float, default=0)
    dependencies: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[Source] = mapped_column(Enum(Source), default=Source.local, index=True)
    source_id: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime)
    project: Mapped[Project] = relationship(back_populates="tasks")


class Integration(Base):
    __tablename__ = "integrations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    provider: Mapped[str] = mapped_column(String(40), unique=True)
    status: Mapped[str] = mapped_column(String(40), default="DISCONNECTED")
    credentials: Mapped[dict] = mapped_column(JSON, default=dict)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    last_sync: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class SyncLog(Base):
    __tablename__ = "sync_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    operation: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), index=True)
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_deleted: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(60), index=True)
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class WorkdayPlan(Base):
    __tablename__ = "workday_plans"
    __table_args__ = (UniqueConstraint("user_id", "date", "task_id", name="uq_workday_task"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    planned_hours: Mapped[float] = mapped_column(Float)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class SyncConflict(Base):
    __tablename__ = "sync_conflicts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    field: Mapped[str] = mapped_column(String(80))
    odoo_value: Mapped[dict | None] = mapped_column(JSON)
    google_value: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="OPEN", index=True)
    resolution: Mapped[str | None] = mapped_column(String(40))
    resolved_value: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)


class Activity(Base):
    __tablename__ = "activities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    entity_type: Mapped[str] = mapped_column(String(30), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(80))
    old_value: Mapped[dict | None] = mapped_column(JSON)
    new_value: Mapped[dict | None] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(40), default="LOCAL")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
