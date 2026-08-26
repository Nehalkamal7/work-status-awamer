from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.entities import Priority, Source


class ORM(BaseModel): model_config = ConfigDict(from_attributes=True)
class Token(BaseModel): access_token: str; refresh_token: str; token_type: str = "bearer"
class Login(BaseModel): email: EmailStr; password: str
class Register(Login): name: str = Field(min_length=2, max_length=160)
class UserOut(ORM): id: str; email: EmailStr; name: str


class ProjectIn(BaseModel):
    name: str; client: str | None = None; description: str | None = None; daily_report: str | None = None; status: str = "ACTIVE"
    priority: Priority = Priority.medium; start_date: date | None = None; deadline: date | None = None
    progress: float = Field(0, ge=0, le=100); assigned_to: str | None = None


class ProjectOut(ProjectIn, ORM):
    id: str; source: Source; source_id: str | None; source_url: str | None; created_at: datetime; updated_at: datetime; last_synced_at: datetime | None


class TaskIn(BaseModel):
    project_id: str; name: str; description: str | None = None; status: str = "TODO"
    priority: Priority = Priority.medium; assigned_to: str | None = None; start_date: date | None = None
    deadline: date | None = None; progress: float = Field(0, ge=0, le=100)
    estimated_hours: float = Field(1, ge=0); actual_hours: float = Field(0, ge=0); dependencies: list[str] = []


class TaskOut(TaskIn, ORM):
    id: str; source: Source; source_id: str | None; source_url: str | None; created_at: datetime; updated_at: datetime; last_synced_at: datetime | None


class NotificationOut(ORM):
    id: str; type: str; title: str; message: str; project_id: str | None; task_id: str | None; is_read: bool; created_at: datetime


class ColumnMapping(BaseModel): mapping: dict[str, str]
class GoogleSelection(BaseModel): spreadsheet_id: str; worksheet: str; mapping: dict[str, str]
class SheetPasteImport(BaseModel): raw_text: str = Field(min_length=1)
class ConflictResolution(BaseModel): strategy: str; value: object | None = None
