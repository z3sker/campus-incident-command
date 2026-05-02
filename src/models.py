from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from src.database import Base
from datetime import datetime

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    role_id = Column(Integer, ForeignKey("roles.id"))
    role = relationship("Role")

class IncidentStatus(Base):
    __tablename__ = "incident_status"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    status_id = Column(Integer, ForeignKey("incident_status.id"))
    reporter_id = Column(Integer, ForeignKey("users.id"))
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    h3_index = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Analytics(Base):
    __tablename__ = "analytics"
    id = Column(Integer, primary_key=True, index=True)
    region_h3 = Column(String)
    incident_count = Column(Integer, default=0)
    resolved_count = Column(Integer, default=0)