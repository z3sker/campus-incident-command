from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

# ───── USERS ─────

def test_create_student():
    response = client.post("/create_user?name=Alice&role=Student")
    assert response.status_code == 200
    assert response.json()["name"] == "Alice"

def test_create_admin():
    response = client.post("/create_user?name=Bob&role=Admin")
    assert response.status_code == 200
    assert response.json()["name"] == "Bob"

def test_create_responder():
    response = client.post("/create_user?name=Carl&role=Responder")
    assert response.status_code == 200
    assert response.json()["name"] == "Carl"

# ───── INCIDENTS ─────

def test_create_incident():
    # Сначала создаём пользователя
    user = client.post("/create_user?name=TestStudent&role=Student").json()
    response = client.post(
        f"/incidents?title=Test&description=TestDesc&reporter_id={user['id']}&zone=cafeteria"
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Test"
    assert response.json()["status_id"] == 1
    assert response.json()["h3_index"] is not None

def test_create_incident_invalid_zone():
    user = client.post("/create_user?name=TestStudent2&role=Student").json()
    response = client.post(
        f"/incidents?title=Test&description=TestDesc&reporter_id={user['id']}&zone=invalid_zone"
    )
    assert response.status_code == 400

def test_create_incident_wrong_role():
    # Responder не может создавать инциденты
    user = client.post("/create_user?name=TestResponder&role=Responder").json()
    response = client.post(
        f"/incidents?title=Test&description=TestDesc&reporter_id={user['id']}&zone=library"
    )
    assert response.status_code == 403

def test_get_incidents():
    response = client.get("/incidents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_incidents_by_zone():
    response = client.get("/incidents/by_zone?zone=cafeteria")
    assert response.status_code == 200
    assert "zone" in response.json()
    assert "incident_count" in response.json()

# ───── ASSIGN ─────

def test_assign_incident():
    admin = client.post("/create_user?name=AdminUser&role=Admin").json()
    responder = client.post("/create_user?name=ResponderUser&role=Responder").json()
    student = client.post("/create_user?name=StudentUser&role=Student").json()

    incident = client.post(
        f"/incidents?title=Fire&description=Fire in cafeteria&reporter_id={student['id']}&zone=cafeteria"
    ).json()

    response = client.put(
        f"/incidents/{incident['id']}/assign?responder_id={responder['id']}&admin_id={admin['id']}"
    )
    assert response.status_code == 200
    assert "assigned" in response.json()["message"]

def test_assign_incident_wrong_role():
    # Студент не может назначать
    student1 = client.post("/create_user?name=S1&role=Student").json()
    student2 = client.post("/create_user?name=S2&role=Student").json()
    incident = client.post(
        f"/incidents?title=Test&description=Test&reporter_id={student1['id']}&zone=library"
    ).json()

    response = client.put(
        f"/incidents/{incident['id']}/assign?responder_id={student2['id']}&admin_id={student1['id']}"
    )
    assert response.status_code == 403

# ───── UPDATE STATUS ─────

def test_update_incident_status():
    admin = client.post("/create_user?name=Admin2&role=Admin").json()
    student = client.post("/create_user?name=Student2&role=Student").json()
    incident = client.post(
        f"/incidents?title=Test&description=Test&reporter_id={student['id']}&zone=library"
    ).json()

    response = client.put(
        f"/incidents/{incident['id']}?status_id=2&user_id={admin['id']}"
    )
    assert response.status_code == 200
    assert response.json()["status_id"] == 2

def test_update_incident_student_forbidden():
    student = client.post("/create_user?name=Student3&role=Student").json()
    incident = client.post(
        f"/incidents?title=Test&description=Test&reporter_id={student['id']}&zone=dormitory"
    ).json()

    response = client.put(
        f"/incidents/{incident['id']}?status_id=3&user_id={student['id']}"
    )
    assert response.status_code == 403

# ───── AUDIT & ANALYTICS ─────

def test_get_audit_log():
    response = client.get("/audit_log")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_analytics():
    response = client.get("/analytics")
    assert response.status_code == 200
    assert isinstance(response.json(), list)