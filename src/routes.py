from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.models import Incident, User, Analytics, AuditLog, Role
from src.audit import log_action
from src.h3_utils import get_h3_index, get_zone_name, get_h3_by_zone_name
from src.services import notify_new_incident
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_role(user: User, allowed_roles):
    role_name = user.role.name if user.role else ""
    if role_name not in allowed_roles:
        raise HTTPException(status_code=403, detail="Access denied")


@router.post("/create_user")
def create_user(name: str, role: str, db: Session = Depends(get_db)):
    role_obj = db.query(Role).filter(Role.name == role).first()
    if not role_obj:
        role_obj = Role(name=role)
        db.add(role_obj)
        db.commit()
        db.refresh(role_obj)

    user = User(name=name, role_id=role_obj.id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/incidents")
def create_incident(
    title: str,
    description: str,
    reporter_id: int,
    zone: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == reporter_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    check_role(user, ["Student", "Admin"])

    try:
        h3_index = get_h3_by_zone_name(zone)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    incident = Incident(
        title=title,
        description=description,
        reporter_id=reporter_id,
        h3_index=h3_index,
        status_id=1,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    background_tasks.add_task(notify_new_incident, incident.id)
    log_action(user_id=reporter_id, action="Create Incident", incident_id=incident.id)

    analytics = db.query(Analytics).filter(Analytics.region_h3 == h3_index).first()
    if analytics:
        analytics.incident_count += 1
    else:
        analytics = Analytics(region_h3=h3_index, incident_count=1, resolved_count=0)
        db.add(analytics)

    db.commit()

    return {
        "id": incident.id,
        "title": incident.title,
        "description": incident.description,
        "status_id": incident.status_id,
        "reporter_id": incident.reporter_id,
        "assigned_to": incident.assigned_to,
        "h3_index": incident.h3_index,
        "created_at": incident.created_at,
    }


@router.get("/incidents")
def get_incidents(db: Session = Depends(get_db)):
    return db.query(Incident).all()


@router.get("/incidents/by_zone")
def get_incidents_by_zone(zone: str, db: Session = Depends(get_db)):
    try:
        h3_index = get_h3_by_zone_name(zone)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    zone_name = get_zone_name(h3_index)
    incidents = db.query(Incident).filter(Incident.h3_index == h3_index).all()
    return {
        "h3_index": h3_index,
        "zone": zone_name,
        "incident_count": len(incidents),
        "incidents": incidents,
    }


@router.put("/incidents/{incident_id}")
def update_incident(incident_id: int, status_id: int, user_id: int, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    check_role(user, ["Admin", "Responder"])

    incident.status_id = status_id

    if status_id == 3:
        analytics = db.query(Analytics).filter(Analytics.region_h3 == incident.h3_index).first()
        if analytics:
            analytics.resolved_count += 1

    db.commit()
    log_action(user_id=user_id, action="Update Incident Status", incident_id=incident.id)
    return incident


@router.put("/incidents/{incident_id}/assign")
def assign_incident(incident_id: int, responder_id: int, admin_id: int, db: Session = Depends(get_db)):
    admin = db.query(User).filter(User.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin user not found")

    check_role(admin, ["Admin"])

    responder = db.query(User).filter(User.id == responder_id).first()
    if not responder:
        raise HTTPException(status_code=404, detail="Responder not found")

    check_role(responder, ["Responder"])

    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident.assigned_to = responder_id
    incident.status_id = 2
    db.commit()

    log_action(user_id=admin_id, action="Assign Incident", incident_id=incident.id)
    return {"message": f"Incident {incident_id} assigned to responder {responder_id}"}


@router.get("/audit_log")
def get_audit_log(db: Session = Depends(get_db)):
    return db.query(AuditLog).all()


@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    return db.query(Analytics).all()