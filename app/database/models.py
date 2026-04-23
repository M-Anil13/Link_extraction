from sqlalchemy import Column, Integer, String, DateTime
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
    status = Column(String)