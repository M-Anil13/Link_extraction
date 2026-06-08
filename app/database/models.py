from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime
from .db import Base

class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    job_url = Column(String, nullable=False)
    portal = Column(String)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    full_name = Column(String)
    email = Column(String)
    company = Column(String)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    picture = Column(String)
    password_hash = Column(String)
    verified = Column(Boolean, default=False)
    otp_code = Column(String)
    otp_expires = Column(DateTime)
    login_count = Column(Integer, default=0)
    run_count = Column(Integer, default=0)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)


class RunLog(Base):
    __tablename__ = "run_logs"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    links_saved = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)