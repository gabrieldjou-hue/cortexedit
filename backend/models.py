"""
models.py
---------
Modelos SQLAlchemy do CortexEdit.
Define todas as tabelas do banco de dados relacional.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, Boolean, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from database import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())[:8]


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(8), primary_key=True, default=_uuid)
    status = Column(String(20), nullable=False, default="pending")
    profile_name = Column(String(100), nullable=False, default="default")
    profile_data = Column(JSON, nullable=True)
    export_formats = Column(JSON, nullable=True, default=list)
    stage_index = Column(Integer, nullable=False, default=-1)
    stage_percent = Column(Integer, nullable=False, default=0)
    total_duration = Column(Float, nullable=True)
    ffmpeg_available = Column(Boolean, nullable=True)
    output_files = Column(JSON, nullable=True, default=list)
    qc_approved = Column(Boolean, nullable=True)
    qc_issues = Column(JSON, nullable=True, default=list)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    completed_at = Column(DateTime, nullable=True)

    agent_results = relationship("AgentResult", back_populates="job", cascade="all, delete-orphan")
    logs = relationship("JobLog", back_populates="job", cascade="all, delete-orphan")
    errors = relationship("JobError", back_populates="job", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "profile_name": self.profile_name,
            "profile_data": self.profile_data,
            "export_formats": self.export_formats,
            "stage_index": self.stage_index,
            "stage_percent": self.stage_percent,
            "total_duration": self.total_duration,
            "ffmpeg_available": self.ffmpeg_available,
            "output_files": self.output_files or [],
            "qc_approved": self.qc_approved,
            "qc_issues": self.qc_issues or [],
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class AgentResult(Base):
    __tablename__ = "agent_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(8), ForeignKey("jobs.id"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    success = Column(Boolean, nullable=False, default=True)
    data = Column(JSON, nullable=True)
    execution_time = Column(Float, nullable=True, default=0.0)
    confidence = Column(Float, nullable=True, default=1.0)
    limitations = Column(JSON, nullable=True, default=list)
    suggestions = Column(JSON, nullable=True, default=list)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    job = relationship("Job", back_populates="agent_results")

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "agent_name": self.agent_name,
            "success": self.success,
            "execution_time": self.execution_time,
            "confidence": self.confidence,
            "limitations": self.limitations or [],
            "suggestions": self.suggestions or [],
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class JobLog(Base):
    __tablename__ = "job_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(8), ForeignKey("jobs.id"), nullable=False)
    timestamp = Column(Float, nullable=False)
    level = Column(String(20), nullable=False, default="info")
    message = Column(Text, nullable=False)

    job = relationship("Job", back_populates="logs")

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
        }


class JobError(Base):
    __tablename__ = "job_errors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(8), ForeignKey("jobs.id"), nullable=False)
    agent = Column(String(100), nullable=False)
    error = Column(Text, nullable=False)
    timestamp = Column(Float, nullable=False)

    job = relationship("Job", back_populates="errors")

    def to_dict(self):
        return {
            "agent": self.agent,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    id = Column(String(8), primary_key=True)
    file_count = Column(Integer, nullable=False, default=0)
    total_size_mb = Column(Float, nullable=False, default=0.0)
    files_data = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "file_count": self.file_count,
            "total_size_mb": self.total_size_mb,
            "files_data": self.files_data or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_name = Column(String(100), nullable=False, unique=True)
    preferences = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    def to_dict(self):
        return {
            "profile_name": self.profile_name,
            "preferences": self.preferences,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
