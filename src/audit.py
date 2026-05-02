from src.database import SessionLocal
from src.models import AuditLog
from datetime import datetime

def log_action(user_id: int, action: str, incident_id: int = None):
    db = SessionLocal()
    log = AuditLog(user_id=user_id, action=action, incident_id=incident_id, timestamp=datetime.utcnow())
    db.add(log)
    db.commit()
    db.close()