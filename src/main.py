from fastapi import FastAPI
from src.models import Base, IncidentStatus
from src.database import engine, SessionLocal
from src.routes import router
from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)

def seed_roles():
    db = SessionLocal()
    try:
        from src.models import Role
        if not db.query(Role).first():
            db.add_all([
                Role(id=1, name="Student"),
                Role(id=2, name="Responder"),
                Role(id=3, name="Admin"),
            ])
            db.commit()
    finally:
        db.close()

def seed_statuses():
    db = SessionLocal()
    try:
        exists = db.query(IncidentStatus).first()
        if not exists:
            db.add_all([
                IncidentStatus(id=1, name="Reported"),
                IncidentStatus(id=2, name="In Progress"),
                IncidentStatus(id=3, name="Closed"),
            ])
            db.commit()
    finally:
        db.close()

seed_roles()
seed_statuses()

app = FastAPI(title="University Incident Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)