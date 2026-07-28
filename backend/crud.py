"""
crud.py
-------
Operacoes CRUD para o banco de dados CortexEdit.
Todas as funcoes recebem uma sessao SQLAlchemy e operam de forma segura.
"""

import time
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import Job, AgentResult, JobLog, JobError, UploadSession, UserPreference

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# JOBS
# ══════════════════════════════════════════════════════════════════════════════

def create_job(
    db: Session,
    job_id: str,
    profile_name: str = "default",
    profile_data: Optional[Dict] = None,
    export_formats: Optional[List[str]] = None,
    ffmpeg_available: Optional[bool] = None,
) -> Job:
    job = Job(
        id=job_id,
        status="running",
        profile_name=profile_name,
        profile_data=profile_data,
        export_formats=export_formats or [],
        ffmpeg_available=ffmpeg_available,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info(f"[DB] Job {job_id} criado (perfil={profile_name})")
    return job


def get_job(db: Session, job_id: str) -> Optional[Job]:
    return db.query(Job).filter(Job.id == job_id).first()


def list_jobs(db: Session, limit: int = 50, offset: int = 0) -> List[Job]:
    return (
        db.query(Job)
        .order_by(desc(Job.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )


def update_job(db: Session, job_id: str, **kwargs) -> Optional[Job]:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return None
    for key, value in kwargs.items():
        if hasattr(job, key):
            setattr(job, key, value)
    db.commit()
    db.refresh(job)
    return job


def complete_job(
    db: Session,
    job_id: str,
    status: str = "completed",
    output_files: Optional[List[Dict]] = None,
    qc_approved: Optional[bool] = None,
    qc_issues: Optional[List[str]] = None,
    total_duration: Optional[float] = None,
    error_message: Optional[str] = None,
) -> Optional[Job]:
    from datetime import datetime, timezone
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return None
    job.status = status
    job.completed_at = datetime.now(timezone.utc)
    if output_files is not None:
        job.output_files = output_files
    if qc_approved is not None:
        job.qc_approved = qc_approved
    if qc_issues is not None:
        job.qc_issues = qc_issues
    if total_duration is not None:
        job.total_duration = total_duration
    if error_message is not None:
        job.error_message = error_message
    db.commit()
    db.refresh(job)
    logger.info(f"[DB] Job {job_id} finalizado (status={status})")
    return job


def count_jobs(db: Session) -> int:
    return db.query(Job).count()


# ══════════════════════════════════════════════════════════════════════════════
# AGENT RESULTS
# ══════════════════════════════════════════════════════════════════════════════

def save_agent_result(
    db: Session,
    job_id: str,
    agent_name: str,
    success: bool = True,
    data: Optional[Dict] = None,
    execution_time: float = 0.0,
    confidence: float = 1.0,
    limitations: Optional[List[str]] = None,
    suggestions: Optional[List[str]] = None,
    error: Optional[str] = None,
) -> AgentResult:
    result = AgentResult(
        job_id=job_id,
        agent_name=agent_name,
        success=success,
        data=data,
        execution_time=execution_time,
        confidence=confidence,
        limitations=limitations or [],
        suggestions=suggestions or [],
        error=error,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def get_agent_results(db: Session, job_id: str) -> List[AgentResult]:
    return (
        db.query(AgentResult)
        .filter(AgentResult.job_id == job_id)
        .order_by(AgentResult.created_at)
        .all()
    )


# ══════════════════════════════════════════════════════════════════════════════
# LOGS
# ══════════════════════════════════════════════════════════════════════════════

def save_logs(db: Session, job_id: str, logs: List[Dict[str, Any]]):
    if not logs:
        return
    objects = [
        JobLog(
            job_id=job_id,
            timestamp=log.get("timestamp", time.time()),
            level=log.get("level", "info"),
            message=log.get("message", ""),
        )
        for log in logs
    ]
    db.bulk_save_objects(objects)
    db.commit()


def save_log(db: Session, job_id: str, message: str, level: str = "info"):
    log = JobLog(
        job_id=job_id,
        timestamp=time.time(),
        level=level,
        message=message,
    )
    db.add(log)
    db.commit()


def get_logs(db: Session, job_id: str, limit: int = 500) -> List[JobLog]:
    return (
        db.query(JobLog)
        .filter(JobLog.job_id == job_id)
        .order_by(JobLog.timestamp)
        .limit(limit)
        .all()
    )


# ══════════════════════════════════════════════════════════════════════════════
# ERRORS
# ══════════════════════════════════════════════════════════════════════════════

def save_errors(db: Session, job_id: str, errors: List[Dict[str, Any]]):
    if not errors:
        return
    objects = [
        JobError(
            job_id=job_id,
            agent=err.get("agent", "unknown"),
            error=err.get("error", ""),
            timestamp=err.get("timestamp", time.time()),
        )
        for err in errors
    ]
    db.bulk_save_objects(objects)
    db.commit()


def save_error(db: Session, job_id: str, agent: str, error: str):
    obj = JobError(
        job_id=job_id,
        agent=agent,
        error=error,
        timestamp=time.time(),
    )
    db.add(obj)
    db.commit()


def get_errors(db: Session, job_id: str) -> List[JobError]:
    return (
        db.query(JobError)
        .filter(JobError.job_id == job_id)
        .order_by(JobError.timestamp)
        .all()
    )


# ══════════════════════════════════════════════════════════════════════════════
# UPLOAD SESSIONS
# ══════════════════════════════════════════════════════════════════════════════

def create_upload_session(
    db: Session,
    session_id: str,
    files_data: List[Dict],
) -> UploadSession:
    total_size = sum(f.get("size_mb", 0) for f in files_data)
    session = UploadSession(
        id=session_id,
        file_count=len(files_data),
        total_size_mb=total_size,
        files_data=files_data,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_upload_session(db: Session, session_id: str) -> Optional[UploadSession]:
    return db.query(UploadSession).filter(UploadSession.id == session_id).first()


# ══════════════════════════════════════════════════════════════════════════════
# USER PREFERENCES (Memory Agent)
# ══════════════════════════════════════════════════════════════════════════════

def save_preference(db: Session, profile_name: str, preferences: Dict) -> UserPreference:
    pref = db.query(UserPreference).filter(UserPreference.profile_name == profile_name).first()
    if pref:
        pref.preferences = preferences
    else:
        pref = UserPreference(profile_name=profile_name, preferences=preferences)
        db.add(pref)
    db.commit()
    db.refresh(pref)
    return pref


def get_preference(db: Session, profile_name: str) -> Optional[UserPreference]:
    return db.query(UserPreference).filter(UserPreference.profile_name == profile_name).first()


def list_preferences(db: Session) -> List[UserPreference]:
    return db.query(UserPreference).all()


def delete_preference(db: Session, profile_name: str) -> bool:
    pref = db.query(UserPreference).filter(UserPreference.profile_name == profile_name).first()
    if pref:
        db.delete(pref)
        db.commit()
        return True
    return False
