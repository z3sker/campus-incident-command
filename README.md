# Campus Incident Command

A polished Streamlit frontend for the University Incident Management backend. The app lets campus teams create users, report incidents, assign responders, update incident status, inspect audit history, and review zone-level analytics powered by H3 spatial indexing.

## What It Does

- Creates Student, Responder, and Admin users through the existing FastAPI backend.
- Reports campus incidents by zone with backend role validation.
- Assigns incidents to responders and moves work through Reported, In Progress, and Closed states.
- Shows dashboard metrics, status charts, zone concentration, incident queues, and audit logs.
- Uses SQLite for local storage and automatically creates the database tables on first run.

## Tech Stack

- Streamlit frontend
- FastAPI backend
- SQLAlchemy ORM
- SQLite database
- H3 spatial indexing
- Pandas and Plotly for analytics views

## Run Locally

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the Streamlit app:

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`. Use the sidebar button `Load demo workspace` if you want sample users and incidents.

## Backend API

The original backend remains available as a FastAPI app:

```bash
uvicorn src.main:app --reload
```

Core endpoints include:

- `POST /create_user`
- `POST /incidents`
- `GET /incidents`
- `GET /incidents/by_zone`
- `PUT /incidents/{incident_id}`
- `PUT /incidents/{incident_id}/assign`
- `GET /audit_log`
- `GET /analytics`

## Deploy to Streamlit Community Cloud

1. Push this project to a GitHub repository.
2. Open [Streamlit Community Cloud](https://share.streamlit.io/).
3. Choose `New app`.
4. Select the repository and branch.
5. Set the main file path to `app.py`.
6. Deploy the app.

Streamlit Cloud installs dependencies from `requirements.txt` and creates the local SQLite database automatically on first launch.

## Public App

Streamlit app URL: [https://khgkkhidyup7tqskw7gtmq.streamlit.app/](https://khgkkhidyup7tqskw7gtmq.streamlit.app/)
