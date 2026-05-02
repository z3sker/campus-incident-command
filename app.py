from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
from fastapi.testclient import TestClient

from src.database import SessionLocal
from src.h3_utils import get_zone_name
from src.main import app as fastapi_app
from src.models import Analytics, AuditLog, Incident, IncidentStatus, Role, User


st.set_page_config(
    page_title="Campus Incident Command",
    page_icon=":material/security:",
    layout="wide",
    initial_sidebar_state="auto",
)


STATUS_LABELS = {
    1: "Reported",
    2: "In Progress",
    3: "Closed",
}

STATUS_COLORS = {
    "Reported": "#df5c4f",
    "In Progress": "#d99a22",
    "Closed": "#2f9d68",
}

ZONE_OPTIONS = {
    "main_building": "Main Building",
    "dormitory": "Dormitory",
    "sports_complex": "Sports Complex",
    "cafeteria": "Cafeteria",
    "library": "Library",
}

ZONE_DESCRIPTIONS = {
    "Main Building": "Academic hub",
    "Dormitory": "Residential safety",
    "Sports Complex": "Athletics and events",
    "Cafeteria": "Food service area",
    "Library": "Study spaces",
}


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #17202d;
            --ink-2: #283447;
            --muted: #667487;
            --line: #d8e1ea;
            --panel: #ffffff;
            --panel-soft: #f8fbfc;
            --wash: #eef4f7;
            --accent: #16798c;
            --accent-2: #26a69a;
            --danger: #df5c4f;
            --amber: #d99a22;
            --green: #2f9d68;
            --blue: #3c6df0;
            --shadow: 0 18px 45px rgba(23, 32, 45, 0.08);
            --shadow-soft: 0 10px 26px rgba(23, 32, 45, 0.055);
        }

        .stApp {
            background:
                linear-gradient(135deg, rgba(22, 121, 140, 0.10) 0%, transparent 34%),
                linear-gradient(180deg, #f7fafc 0%, #edf4f7 100%);
            color: var(--ink);
        }

        header[data-testid="stHeader"] {
            background: rgba(247, 250, 252, 0.82);
            backdrop-filter: blur(14px);
            border-bottom: 1px solid rgba(216, 225, 234, 0.72);
        }

        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, #ffffff 0%, #f2f7f9 100%);
            border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1.3rem;
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] label {
            color: var(--ink);
        }

        .block-container {
            padding-top: 4.25rem;
            padding-bottom: 3.8rem;
            max-width: 1240px;
        }

        h1, h2, h3 {
            color: var(--ink);
            letter-spacing: 0;
        }

        h1 {
            font-size: 2.45rem;
            line-height: 1.12;
            margin-bottom: 0.4rem;
        }

        h2 {
            margin-top: 0.6rem;
        }

        div[data-testid="stMarkdownContainer"] p {
            line-height: 1.55;
        }

        .sidebar-brand {
            padding: 0.9rem 0.9rem 1rem;
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: var(--shadow-soft);
            margin-bottom: 1rem;
        }

        .sidebar-brand-title {
            font-size: 1.02rem;
            font-weight: 900;
            color: var(--ink);
            line-height: 1.2;
            margin-bottom: 0.35rem;
        }

        .sidebar-brand-subtitle {
            color: var(--muted);
            font-size: 0.84rem;
            line-height: 1.45;
        }

        .sidebar-label {
            color: var(--muted);
            font-size: 0.72rem;
            font-weight: 850;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin: 1.1rem 0 0.45rem;
        }

        .sidebar-stat-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.5rem;
            margin: 0.8rem 0 0.9rem;
        }

        .sidebar-stat {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.65rem 0.7rem;
        }

        .sidebar-stat-value {
            font-size: 1.15rem;
            font-weight: 900;
            color: var(--ink);
            line-height: 1;
        }

        .sidebar-stat-label {
            color: var(--muted);
            font-size: 0.72rem;
            margin-top: 0.28rem;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] {
            gap: 0.35rem;
        }

        [data-testid="stSidebar"] label[data-baseweb="radio"] {
            background: rgba(255, 255, 255, 0.68);
            border: 1px solid transparent;
            border-radius: 8px;
            padding: 0.42rem 0.52rem;
            transition: all 130ms ease;
        }

        [data-testid="stSidebar"] label[data-baseweb="radio"]:hover {
            background: #ffffff;
            border-color: var(--line);
        }

        [data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {
            background: #e8f4f6;
            border-color: #a8d3db;
            box-shadow: inset 3px 0 0 var(--accent);
        }

        .hero-shell {
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(196, 214, 222, 0.88);
            border-radius: 8px;
            background:
                linear-gradient(110deg, rgba(255, 255, 255, 0.98), rgba(239, 249, 250, 0.94) 62%, rgba(232, 242, 246, 0.94)),
                linear-gradient(90deg, rgba(22, 121, 140, 0.12), rgba(223, 92, 79, 0.05));
            box-shadow: var(--shadow);
            padding: clamp(1.25rem, 2.5vw, 2.05rem);
            margin-bottom: 1.25rem;
        }

        .hero-shell:after {
            content: "";
            position: absolute;
            right: -4rem;
            top: -6rem;
            width: 18rem;
            height: 18rem;
            background:
                linear-gradient(135deg, rgba(22, 121, 140, 0.12), rgba(47, 157, 104, 0.06));
            border: 1px solid rgba(22, 121, 140, 0.08);
            transform: rotate(20deg);
            border-radius: 8px;
        }

        .hero-content {
            position: relative;
            z-index: 1;
            max-width: 850px;
        }

        .app-kicker {
            color: var(--accent);
            font-size: 0.76rem;
            line-height: 1.45;
            font-weight: 900;
            letter-spacing: 0.085em;
            text-transform: uppercase;
            margin-bottom: 0.52rem;
        }

        .hero-title {
            color: var(--ink);
            font-size: clamp(2rem, 4.4vw, 4.05rem);
            font-weight: 950;
            line-height: 1.02;
            letter-spacing: 0;
            max-width: 760px;
            margin: 0 0 0.78rem;
        }

        .app-subtitle {
            color: var(--muted);
            font-size: clamp(1rem, 1.4vw, 1.12rem);
            max-width: 710px;
            margin: 0 0 1.15rem;
            line-height: 1.62;
        }

        .hero-meta-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-top: 0.95rem;
        }

        .hero-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            min-height: 2.15rem;
            padding: 0.42rem 0.74rem;
            border-radius: 999px;
            border: 1px solid #c5dbe2;
            background: rgba(255, 255, 255, 0.72);
            color: var(--ink-2);
            font-size: 0.84rem;
            font-weight: 800;
        }

        .hero-pill-dot {
            width: 0.55rem;
            height: 0.55rem;
            border-radius: 50%;
            background: var(--green);
            box-shadow: 0 0 0 4px rgba(47, 157, 104, 0.13);
        }

        .section-heading {
            margin: 1.35rem 0 0.85rem;
        }

        .section-eyebrow {
            color: var(--accent);
            font-size: 0.73rem;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            line-height: 1.4;
            margin-bottom: 0.2rem;
        }

        .section-title {
            color: var(--ink);
            font-size: clamp(1.28rem, 2vw, 1.72rem);
            font-weight: 900;
            line-height: 1.22;
            margin: 0;
        }

        .section-copy {
            color: var(--muted);
            font-size: 0.95rem;
            margin-top: 0.25rem;
            max-width: 760px;
        }

        .metric-grid {
            margin-top: 0.2rem;
        }

        .metric-card {
            position: relative;
            overflow: hidden;
            background: rgba(255, 255, 255, 0.96);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1.05rem;
            box-shadow: var(--shadow-soft);
            min-height: 130px;
        }

        .metric-card:before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, var(--accent), var(--accent-2));
        }

        .metric-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.65rem;
            margin-bottom: 0.5rem;
        }

        .metric-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2rem;
            height: 2rem;
            border-radius: 8px;
            background: #e8f4f6;
            color: var(--accent);
            font-size: 0.78rem;
            font-weight: 900;
            border: 1px solid #c6dde4;
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.74rem;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            line-height: 1.35;
        }

        .metric-value {
            color: var(--ink);
            font-size: clamp(2rem, 3vw, 2.65rem);
            line-height: 1.02;
            font-weight: 950;
            margin: 0.2rem 0 0.3rem;
        }

        .metric-note {
            color: var(--muted);
            font-size: 0.88rem;
            line-height: 1.45;
        }

        .panel {
            background: rgba(255, 255, 255, 0.94);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: clamp(0.95rem, 1.6vw, 1.25rem);
            box-shadow: var(--shadow-soft);
            margin-bottom: 1rem;
        }

        .welcome-band {
            margin-top: 1rem;
            background:
                linear-gradient(120deg, rgba(23, 32, 45, 0.95), rgba(28, 69, 82, 0.94)),
                linear-gradient(90deg, rgba(22, 121, 140, 0.28), rgba(223, 92, 79, 0.18));
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 8px;
            box-shadow: var(--shadow);
            padding: clamp(1.1rem, 2.2vw, 1.55rem);
        }

        .welcome-title {
            font-size: clamp(1.35rem, 2.4vw, 1.9rem);
            line-height: 1.18;
            font-weight: 950;
            margin: 0 0 0.4rem;
        }

        .welcome-copy {
            color: rgba(255, 255, 255, 0.78);
            max-width: 760px;
            line-height: 1.58;
            margin-bottom: 1rem;
        }

        .step-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.7rem;
        }

        .step-item {
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            padding: 0.85rem;
            background: rgba(255, 255, 255, 0.08);
        }

        .step-number {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 1.65rem;
            height: 1.65rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.14);
            color: #ffffff;
            font-size: 0.8rem;
            font-weight: 900;
            margin-bottom: 0.55rem;
        }

        .step-title {
            font-weight: 900;
            margin-bottom: 0.2rem;
        }

        .step-copy {
            color: rgba(255, 255, 255, 0.72);
            font-size: 0.88rem;
            line-height: 1.45;
        }

        .zone-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 0.75rem;
            margin-top: 0.75rem;
        }

        .zone-card {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.95rem;
            box-shadow: var(--shadow-soft);
            min-height: 112px;
        }

        .zone-index {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 1.7rem;
            height: 1.7rem;
            border-radius: 8px;
            background: #eef7f8;
            color: var(--accent);
            font-size: 0.76rem;
            font-weight: 950;
            margin-bottom: 0.55rem;
        }

        .zone-title {
            color: var(--ink);
            font-weight: 900;
            line-height: 1.25;
            margin-bottom: 0.2rem;
        }

        .zone-copy {
            color: var(--muted);
            font-size: 0.86rem;
            line-height: 1.45;
        }

        .empty-state {
            background: rgba(255, 255, 255, 0.94);
            border: 1px solid var(--line);
            border-left: 5px solid var(--accent);
            border-radius: 8px;
            padding: 1rem 1.05rem;
            box-shadow: var(--shadow-soft);
            color: var(--ink);
        }

        .empty-state-title {
            font-weight: 900;
            font-size: 1rem;
            margin-bottom: 0.22rem;
        }

        .empty-state-copy {
            color: var(--muted);
            font-size: 0.92rem;
            line-height: 1.52;
        }

        .incident-card {
            background: #ffffff;
            border: 1px solid var(--line);
            border-left: 5px solid var(--accent);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 0.8rem;
            box-shadow: var(--shadow-soft);
        }

        .incident-title {
            color: var(--ink);
            font-size: 1.02rem;
            font-weight: 900;
            line-height: 1.35;
            margin-bottom: 0.25rem;
        }

        .incident-meta {
            color: var(--muted);
            font-size: 0.86rem;
            line-height: 1.45;
            margin-bottom: 0.65rem;
        }

        .incident-desc {
            color: #334155;
            font-size: 0.95rem;
            margin-bottom: 0.75rem;
        }

        .chip {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 0.24rem 0.64rem;
            font-size: 0.76rem;
            line-height: 1.25;
            font-weight: 900;
            margin-right: 0.35rem;
            border: 1px solid transparent;
        }

        .chip-reported {
            color: #96352d;
            background: #fdecea;
            border-color: #f6c7c2;
        }

        .chip-progress {
            color: #805300;
            background: #fff2d7;
            border-color: #f4d48d;
        }

        .chip-closed {
            color: #176041;
            background: #dff5ea;
            border-color: #a9dfc2;
        }

        .chip-neutral {
            color: #34515d;
            background: #e7f1f4;
            border-color: #c4dbe2;
        }

        .table-caption {
            color: var(--muted);
            font-size: 0.88rem;
            margin: -0.25rem 0 0.6rem;
        }

        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.9rem 1rem;
            box-shadow: 0 12px 28px rgba(24, 33, 47, 0.05);
        }

        div[data-testid="stMetricValue"] {
            color: var(--ink);
            font-weight: 800;
        }

        .stButton > button,
        .stDownloadButton > button {
            min-height: 2.65rem;
            border-radius: 8px;
            border: 1px solid #1f7a8c;
            background: linear-gradient(180deg, #238da0 0%, #16798c 100%);
            color: #ffffff;
            font-weight: 900;
            box-shadow: 0 10px 18px rgba(22, 121, 140, 0.18);
            transition: all 130ms ease;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            border-color: #126578;
            background: linear-gradient(180deg, #1d8194 0%, #126578 100%);
            color: #ffffff;
            transform: translateY(-1px);
            box-shadow: 0 14px 24px rgba(22, 121, 140, 0.22);
        }

        .stButton > button:disabled {
            box-shadow: none;
        }

        .stTextInput input,
        .stTextArea textarea,
        [data-baseweb="select"] > div {
            border-radius: 8px;
            border-color: #cfdbe4;
            background-color: #ffffff;
        }

        .stTextInput input:focus,
        .stTextArea textarea:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(22, 121, 140, 0.12);
        }

        label, .stSelectbox label, .stTextInput label, .stTextArea label, .stMultiSelect label {
            font-weight: 800;
            color: var(--ink-2);
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.35rem;
            border-bottom: 1px solid var(--line);
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0;
            padding: 0.62rem 0.85rem;
            background: #ffffff;
            border: 1px solid var(--line);
            border-bottom: none;
            color: var(--ink-2);
            font-weight: 850;
        }

        .stTabs [aria-selected="true"] {
            background: #e7f1f4;
            border-color: #9ec8d2;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: var(--shadow-soft);
        }

        div[data-testid="stAlert"] {
            border-radius: 8px;
        }

        @media (max-width: 800px) {
            .block-container {
                padding-top: 3.45rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }

            h1 {
                font-size: 1.75rem;
            }

            .hero-shell {
                padding: 1.05rem;
            }

            .app-subtitle {
                font-size: 0.96rem;
            }

            .step-row,
            .zone-grid {
                grid-template-columns: 1fr;
            }

            .metric-card {
                min-height: 112px;
            }
        }

        @media (min-width: 801px) and (max-width: 1120px) {
            .zone-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource
def get_client() -> TestClient:
    return TestClient(fastapi_app, raise_server_exceptions=False)


def format_dt(value: Any) -> str:
    if value in (None, ""):
        return "Unknown"
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y %H:%M")
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%b %d, %Y %H:%M")
    except ValueError:
        return str(value)


def zone_from_h3(h3_index: str | None) -> str:
    if not h3_index:
        return "Unknown Zone"
    return get_zone_name(h3_index)


def status_chip(status: str) -> str:
    css_class = {
        "Reported": "chip-reported",
        "In Progress": "chip-progress",
        "Closed": "chip-closed",
    }.get(status, "chip-neutral")
    return f'<span class="chip {css_class}">{escape(status)}</span>'


def api_error(response: Any, fallback: str) -> str:
    try:
        payload = response.json()
        detail = payload.get("detail")
        if isinstance(detail, list):
            return "; ".join(str(item.get("msg", item)) for item in detail)
        if detail:
            return str(detail)
    except Exception:
        pass
    return fallback


def post_create_user(name: str, role: str) -> tuple[bool, dict[str, Any] | str]:
    response = get_client().post("/create_user", params={"name": name, "role": role})
    if response.status_code == 200:
        st.cache_data.clear()
        return True, response.json()
    return False, api_error(response, "The user could not be created.")


def post_create_incident(title: str, description: str, reporter_id: int, zone: str) -> tuple[bool, dict[str, Any] | str]:
    response = get_client().post(
        "/incidents",
        params={
            "title": title,
            "description": description,
            "reporter_id": reporter_id,
            "zone": zone,
        },
    )
    if response.status_code == 200:
        st.cache_data.clear()
        return True, response.json()
    return False, api_error(response, "The incident could not be created.")


def put_assign_incident(incident_id: int, responder_id: int, admin_id: int) -> tuple[bool, str]:
    response = get_client().put(
        f"/incidents/{incident_id}/assign",
        params={"responder_id": responder_id, "admin_id": admin_id},
    )
    if response.status_code == 200:
        st.cache_data.clear()
        return True, response.json().get("message", "Incident assigned.")
    return False, api_error(response, "The incident could not be assigned.")


def put_update_status(incident_id: int, status_id: int, user_id: int) -> tuple[bool, str]:
    response = get_client().put(
        f"/incidents/{incident_id}",
        params={"status_id": status_id, "user_id": user_id},
    )
    if response.status_code == 200:
        st.cache_data.clear()
        return True, "Incident status updated."
    return False, api_error(response, "The incident status could not be updated.")


@st.cache_data(ttl=4)
def load_snapshot() -> dict[str, pd.DataFrame]:
    db = SessionLocal()
    try:
        roles = {role.id: role.name for role in db.query(Role).all()}
        statuses = {status.id: status.name for status in db.query(IncidentStatus).all()}
        users = [
            {
                "id": user.id,
                "name": user.name,
                "role_id": user.role_id,
                "role": roles.get(user.role_id, "Unknown"),
            }
            for user in db.query(User).order_by(User.id.desc()).all()
        ]
        user_lookup = {user["id"]: user for user in users}

        incidents = []
        for incident in db.query(Incident).order_by(Incident.created_at.desc(), Incident.id.desc()).all():
            reporter = user_lookup.get(incident.reporter_id, {})
            assignee = user_lookup.get(incident.assigned_to, {})
            status = statuses.get(incident.status_id, STATUS_LABELS.get(incident.status_id, "Unknown"))
            zone = zone_from_h3(incident.h3_index)
            incidents.append(
                {
                    "id": incident.id,
                    "title": incident.title or "Untitled incident",
                    "description": incident.description or "",
                    "status_id": incident.status_id,
                    "status": status,
                    "reporter_id": incident.reporter_id,
                    "reporter": reporter.get("name", f"User {incident.reporter_id}"),
                    "assigned_to": incident.assigned_to,
                    "assignee": assignee.get("name", "Unassigned"),
                    "zone": zone,
                    "h3_index": incident.h3_index,
                    "created_at": incident.created_at,
                    "created": format_dt(incident.created_at),
                }
            )

        audit = []
        for log in db.query(AuditLog).order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).limit(200).all():
            actor = user_lookup.get(log.user_id, {})
            audit.append(
                {
                    "id": log.id,
                    "timestamp": log.timestamp,
                    "time": format_dt(log.timestamp),
                    "actor": actor.get("name", f"User {log.user_id}"),
                    "action": log.action,
                    "incident_id": log.incident_id,
                }
            )

        analytics = []
        for row in db.query(Analytics).order_by(Analytics.incident_count.desc()).all():
            analytics.append(
                {
                    "zone": zone_from_h3(row.region_h3),
                    "h3_index": row.region_h3,
                    "incident_count": row.incident_count or 0,
                    "resolved_count": row.resolved_count or 0,
                }
            )

        return {
            "users": pd.DataFrame(users),
            "incidents": pd.DataFrame(incidents),
            "audit": pd.DataFrame(audit),
            "analytics": pd.DataFrame(analytics),
        }
    finally:
        db.close()


def seed_demo_workspace() -> None:
    snapshot = load_snapshot()
    users = snapshot["users"]

    def find_or_create(name: str, role: str) -> int:
        if not users.empty:
            matches = users[(users["name"] == name) & (users["role"] == role)]
            if not matches.empty:
                return int(matches.iloc[0]["id"])
        ok, payload = post_create_user(name, role)
        if not ok:
            raise RuntimeError(str(payload))
        return int(payload["id"])

    admin_id = find_or_create("Campus Admin", "Admin")
    responder_id = find_or_create("Safety Responder", "Responder")
    student_id = find_or_create("Student Reporter", "Student")

    demo_incidents = [
        ("Water leak near lockers", "Water is spreading across the first-floor corridor near the lockers.", "main_building"),
        ("Broken exterior light", "The walkway light outside the dormitory entrance is not working after sunset.", "dormitory"),
        ("Cafeteria smoke alarm", "Smoke alarm activated in the kitchen service area during lunch preparation.", "cafeteria"),
    ]

    created_ids: list[int] = []
    for title, description, zone in demo_incidents:
        ok, payload = post_create_incident(title, description, student_id, zone)
        if ok and isinstance(payload, dict):
            created_ids.append(int(payload["id"]))

    if created_ids:
        put_assign_incident(created_ids[-1], responder_id, admin_id)

    st.cache_data.clear()


def snapshot_counts(snapshot: dict[str, pd.DataFrame]) -> dict[str, int | str]:
    incidents = snapshot["incidents"]
    users = snapshot["users"]
    total = len(incidents)
    active = int((incidents["status"] != "Closed").sum()) if not incidents.empty else 0
    closed = int((incidents["status"] == "Closed").sum()) if not incidents.empty else 0
    responders = int((users["role"] == "Responder").sum()) if not users.empty else 0
    resolution = f"{round((closed / total) * 100)}%" if total else "0%"
    return {
        "total": total,
        "active": active,
        "closed": closed,
        "responders": responders,
        "resolution": resolution,
    }


def render_header(snapshot: dict[str, pd.DataFrame]) -> None:
    counts = snapshot_counts(snapshot)
    st.markdown(
        f"""
        <section class="hero-shell">
            <div class="hero-content">
                <div class="app-kicker">University Safety Operations</div>
                <h1 class="hero-title">Campus Incident Command</h1>
                <p class="app-subtitle">
                    A calm, focused workspace for reporting incidents, assigning responders,
                    and monitoring campus risk across priority zones.
                </p>
                <div class="hero-meta-row">
                    <span class="hero-pill"><span class="hero-pill-dot"></span>Live workspace</span>
                    <span class="hero-pill">{counts["active"]} active incidents</span>
                    <span class="hero-pill">{counts["responders"]} responders listed</span>
                    <span class="hero-pill">Updated {escape(datetime.now().strftime("%b %d, %H:%M"))}</span>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_section_heading(eyebrow: str, title: str, copy: str | None = None) -> None:
    copy_html = f'<div class="section-copy">{escape(copy)}</div>' if copy else ""
    st.markdown(
        f"""
        <div class="section-heading">
            <div class="section-eyebrow">{escape(eyebrow)}</div>
            <h2 class="section-title">{escape(title)}</h2>
            {copy_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric(label: str, value: str | int, note: str, icon: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-top">
                <div class="metric-label">{escape(str(label))}</div>
                <div class="metric-icon">{escape(icon)}</div>
            </div>
            <div class="metric-value">{escape(str(value))}</div>
            <div class="metric-note">{escape(str(note))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-state-title">{escape(title)}</div>
            <div class="empty-state-copy">{escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_welcome_empty_dashboard() -> None:
    st.markdown(
        """
        <section class="welcome-band">
            <div class="welcome-title">Your command center is ready.</div>
            <div class="welcome-copy">
                Start with a clean workspace, add the campus team, then report the first incident.
                The dashboard will immediately populate with status, zone, and audit views.
            </div>
            <div class="step-row">
                <div class="step-item">
                    <div class="step-number">1</div>
                    <div class="step-title">Create roles</div>
                    <div class="step-copy">Add a student reporter, an admin, and at least one responder.</div>
                </div>
                <div class="step-item">
                    <div class="step-number">2</div>
                    <div class="step-title">Report an incident</div>
                    <div class="step-copy">Capture the issue, choose a campus zone, and submit it for triage.</div>
                </div>
                <div class="step-item">
                    <div class="step-number">3</div>
                    <div class="step-title">Assign and close</div>
                    <div class="step-copy">Route work to responders and keep leadership informed as status changes.</div>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_zone_overview() -> None:
    cards = []
    for index, zone in enumerate(ZONE_OPTIONS.values(), start=1):
        cards.append(
            (
                '<div class="zone-card">'
                f'<div class="zone-index">Z{index}</div>'
                f'<div class="zone-title">{escape(zone)}</div>'
                f'<div class="zone-copy">{escape(ZONE_DESCRIPTIONS.get(zone, "Campus area"))}</div>'
                "</div>"
            )
        )
    st.markdown(f'<div class="zone-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_sidebar(snapshot: dict[str, pd.DataFrame]) -> str:
    counts = snapshot_counts(snapshot)
    st.sidebar.markdown(
        f"""
        <div class="sidebar-brand">
            <div class="sidebar-brand-title">Campus Incident Command</div>
            <div class="sidebar-brand-subtitle">Operational workspace for campus safety teams.</div>
            <div class="sidebar-stat-grid">
                <div class="sidebar-stat">
                    <div class="sidebar-stat-value">{counts["total"]}</div>
                    <div class="sidebar-stat-label">Incidents</div>
                </div>
                <div class="sidebar-stat">
                    <div class="sidebar-stat-value">{counts["active"]}</div>
                    <div class="sidebar-stat-label">Active</div>
                </div>
            </div>
        </div>
        <div class="sidebar-label">Navigation</div>
        """,
        unsafe_allow_html=True,
    )
    page = st.sidebar.radio(
        "Go to",
        ["Dashboard", "Report Incident", "Response Center", "People & Audit"],
        label_visibility="collapsed",
    )
    st.sidebar.markdown('<div class="sidebar-label">Workspace</div>', unsafe_allow_html=True)
    if st.sidebar.button("Refresh data", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    if st.sidebar.button("Load demo workspace", width="stretch"):
        with st.spinner("Creating demo users and incidents..."):
            try:
                seed_demo_workspace()
                st.success("Demo workspace loaded.")
                st.rerun()
            except Exception as exc:
                st.error(f"Demo data could not be loaded: {exc}")
    st.sidebar.caption("SQLite storage is created automatically on first run.")
    return page


def render_incident_card(row: pd.Series) -> None:
    status = str(row.get("status", "Unknown"))
    assignee = str(row.get("assignee", "Unassigned"))
    assignment_chip = (
        '<span class="chip chip-neutral">Unassigned</span>'
        if assignee == "Unassigned"
        else f'<span class="chip chip-neutral">Assigned to {escape(assignee)}</span>'
    )
    st.markdown(
        f"""
        <div class="incident-card">
            <div class="incident-title">#{int(row["id"])} - {escape(str(row["title"]))}</div>
            <div class="incident-meta">{escape(str(row["zone"]))} - Reported by {escape(str(row["reporter"]))} - {escape(str(row["created"]))}</div>
            <div class="incident-desc">{escape(str(row["description"]))}</div>
            {status_chip(status)}
            {assignment_chip}
        </div>
        """,
        unsafe_allow_html=True,
    )


def dashboard(snapshot: dict[str, pd.DataFrame]) -> None:
    incidents = snapshot["incidents"]
    users = snapshot["users"]
    analytics = snapshot["analytics"]

    counts = snapshot_counts(snapshot)

    render_section_heading("Overview", "Command Dashboard", "Monitor active work, response capacity, and campus risk at a glance.")
    cols = st.columns(4)
    with cols[0]:
        render_metric("Total Incidents", counts["total"], "All reports in the system", "IR")
    with cols[1]:
        render_metric("Active Work", counts["active"], "Reported or in progress", "AW")
    with cols[2]:
        closed_count = int(counts["closed"])
        render_metric("Resolution Rate", counts["resolution"], f"{closed_count} closed incident{'s' if closed_count != 1 else ''}", "RR")
    with cols[3]:
        render_metric("Responders", counts["responders"], "Available response users", "RS")

    if incidents.empty:
        render_welcome_empty_dashboard()
        render_section_heading("Coverage", "Campus Zones", "The app groups reports into these operational zones for faster triage.")
        render_zone_overview()
        return

    chart_col, zone_col = st.columns((1.1, 0.9), gap="large")
    with chart_col:
        render_section_heading("Status", "Incident Flow")
        status_counts = (
            incidents.groupby("status", as_index=False)
            .size()
            .rename(columns={"size": "count"})
            .sort_values("count", ascending=False)
        )
        fig = px.bar(
            status_counts,
            x="status",
            y="count",
            color="status",
            color_discrete_map=STATUS_COLORS,
            text="count",
        )
        fig.update_layout(
            height=360,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="",
            yaxis_title="Incidents",
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#18212f"),
            bargap=0.36,
        )
        fig.update_traces(textposition="outside", marker_line_width=0, marker_cornerradius=7)
        st.plotly_chart(fig, width="stretch")

    with zone_col:
        render_section_heading("Zones", "Zone Concentration")
        zone_counts = incidents.groupby("zone", as_index=False).size().rename(columns={"size": "count"})
        fig = px.pie(
            zone_counts,
            values="count",
            names="zone",
            hole=0.58,
            color_discrete_sequence=["#1f7a8c", "#d94b45", "#d99a22", "#258b62", "#516173"],
        )
        fig.update_layout(
            height=360,
            margin=dict(l=10, r=10, t=20, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#18212f"),
            legend=dict(orientation="h", y=-0.08),
        )
        st.plotly_chart(fig, width="stretch")

    render_section_heading("Operations", "Operational Snapshot", "Compare zone workload and recent response activity.")
    left, right = st.columns((0.95, 1.05), gap="large")
    with left:
        if analytics.empty:
            zone_summary = incidents.groupby("zone", as_index=False).size().rename(columns={"size": "incident_count"})
            zone_summary["resolved_count"] = 0
        else:
            zone_summary = analytics[["zone", "incident_count", "resolved_count"]].copy()
        zone_summary["open_count"] = zone_summary["incident_count"] - zone_summary["resolved_count"]
        st.markdown('<div class="table-caption">Zone workload</div>', unsafe_allow_html=True)
        st.dataframe(
            zone_summary.rename(
                columns={
                    "zone": "Zone",
                    "incident_count": "Reported",
                    "resolved_count": "Closed",
                    "open_count": "Open",
                }
            ),
            hide_index=True,
            width="stretch",
        )
    with right:
        recent_cols = ["id", "title", "status", "zone", "reporter", "assignee", "created"]
        st.markdown('<div class="table-caption">Latest reports</div>', unsafe_allow_html=True)
        st.dataframe(
            incidents[recent_cols].head(8).rename(
                columns={
                    "id": "ID",
                    "title": "Incident",
                    "status": "Status",
                    "zone": "Zone",
                    "reporter": "Reporter",
                    "assignee": "Assigned To",
                    "created": "Created",
                }
            ),
            hide_index=True,
            width="stretch",
        )


def report_incident(snapshot: dict[str, pd.DataFrame]) -> None:
    users = snapshot["users"]
    eligible = users[users["role"].isin(["Student", "Admin"])] if not users.empty else pd.DataFrame()

    render_section_heading(
        "Intake",
        "Report a New Incident",
        "Capture the situation clearly so the response team can triage it quickly.",
    )

    create_tab, quick_user_tab = st.tabs(["Incident Report", "Create Reporter"])

    with quick_user_tab:
        render_empty_state("Need a reporter?", "Create a Student or Admin profile, then return to the incident report tab.")
        with st.form("create_reporter", clear_on_submit=True):
            name = st.text_input("Reporter name", placeholder="Example: Dana Kim")
            role = st.selectbox("Role", ["Student", "Admin"])
            submitted = st.form_submit_button("Create reporter")
            if submitted:
                clean_name = name.strip()
                if len(clean_name) < 2:
                    st.error("Enter a reporter name with at least 2 characters.")
                else:
                    with st.spinner("Creating reporter..."):
                        ok, payload = post_create_user(clean_name, role)
                    if ok:
                        st.success(f"Created {payload['name']} as {role}.")
                        st.rerun()
                    else:
                        st.error(str(payload))

    with create_tab:
        if eligible.empty:
            render_empty_state("No eligible reporters yet.", "Create a Student or Admin user before reporting an incident.")
            return

        reporter_options = {
            f"{row['name']} - {row['role']} - ID {int(row['id'])}": int(row["id"])
            for _, row in eligible.sort_values(["role", "name"]).iterrows()
        }

        st.markdown(
            """
            <div class="panel">
                <div class="section-eyebrow">Report quality</div>
                <div class="section-copy">
                    Use a concise title, include the immediate risk, and choose the closest campus zone.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("incident_report_form", clear_on_submit=True):
            title = st.text_input("Incident title", placeholder="Example: Water leak near the library entrance")
            description = st.text_area(
                "Description",
                placeholder="Describe what happened, where it is, and what immediate action is needed.",
                height=150,
            )
            form_cols = st.columns(2)
            with form_cols[0]:
                reporter_label = st.selectbox("Reporter", list(reporter_options.keys()))
            with form_cols[1]:
                zone_label = st.selectbox("Campus zone", list(ZONE_OPTIONS.values()))

            submitted = st.form_submit_button("Submit incident")
            if submitted:
                clean_title = title.strip()
                clean_description = description.strip()
                zone_key = next(key for key, label in ZONE_OPTIONS.items() if label == zone_label)
                reporter_id = reporter_options[reporter_label]

                errors = []
                if len(clean_title) < 4:
                    errors.append("Use a title with at least 4 characters.")
                if len(clean_description) < 12:
                    errors.append("Use a description with at least 12 characters.")

                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    with st.spinner("Submitting incident through the backend..."):
                        ok, payload = post_create_incident(clean_title, clean_description, reporter_id, zone_key)
                    if ok:
                        st.success(f"Incident #{payload['id']} was reported for {zone_label}.")
                        st.rerun()
                    else:
                        st.error(str(payload))


def response_center(snapshot: dict[str, pd.DataFrame]) -> None:
    incidents = snapshot["incidents"]
    users = snapshot["users"]

    render_section_heading(
        "Triage",
        "Response Center",
        "Assign active work, filter the queue, and keep incident status current.",
    )

    if incidents.empty:
        render_empty_state("No incidents available.", "Report an incident before assigning or updating response work.")
        render_zone_overview()
        return

    admins = users[users["role"] == "Admin"] if not users.empty else pd.DataFrame()
    responders = users[users["role"] == "Responder"] if not users.empty else pd.DataFrame()
    managers = users[users["role"].isin(["Admin", "Responder"])] if not users.empty else pd.DataFrame()

    filters = st.columns(3)
    with filters[0]:
        status_filter = st.multiselect("Status", ["Reported", "In Progress", "Closed"], default=["Reported", "In Progress"])
    with filters[1]:
        zone_filter = st.multiselect("Zone", sorted(incidents["zone"].unique()))
    with filters[2]:
        assignment_filter = st.selectbox("Assignment", ["All", "Unassigned", "Assigned"])

    filtered = incidents.copy()
    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]
    if zone_filter:
        filtered = filtered[filtered["zone"].isin(zone_filter)]
    if assignment_filter == "Unassigned":
        filtered = filtered[filtered["assigned_to"].isna()]
    elif assignment_filter == "Assigned":
        filtered = filtered[filtered["assigned_to"].notna()]

    left, right = st.columns((1.05, 0.95), gap="large")

    with left:
        render_section_heading("Queue", "Active Incident Queue")
        if filtered.empty:
            render_empty_state("No matches.", "Adjust the filters or create a new incident.")
        else:
            for _, row in filtered.head(10).iterrows():
                render_incident_card(row)

    with right:
        render_section_heading("Actions", "Responder Workflow")
        assign_tab, status_tab = st.tabs(["Assign", "Update Status"])

        with assign_tab:
            if admins.empty or responders.empty:
                render_empty_state("Team setup needed.", "Create at least one Admin and one Responder before assigning incidents.")
            else:
                with st.form("assign_form"):
                    assignable = incidents[incidents["status"] != "Closed"].copy()
                    incident_options = {
                        f"#{int(row['id'])} - {row['title']} - {row['zone']}": int(row["id"])
                        for _, row in assignable.iterrows()
                    }
                    admin_options = {
                        f"{row['name']} - ID {int(row['id'])}": int(row["id"]) for _, row in admins.iterrows()
                    }
                    responder_options = {
                        f"{row['name']} - ID {int(row['id'])}": int(row["id"]) for _, row in responders.iterrows()
                    }
                    if not incident_options:
                        render_empty_state("Nothing to assign.", "All incidents are currently closed.")
                    else:
                        selected_incident = st.selectbox("Incident", list(incident_options.keys()))
                        selected_responder = st.selectbox("Responder", list(responder_options.keys()))
                        selected_admin = st.selectbox("Approving admin", list(admin_options.keys()))
                        submitted = st.form_submit_button("Assign responder")
                        if submitted:
                            with st.spinner("Assigning responder..."):
                                ok, message = put_assign_incident(
                                    incident_options[selected_incident],
                                    responder_options[selected_responder],
                                    admin_options[selected_admin],
                                )
                            if ok:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)

        with status_tab:
            if managers.empty:
                render_empty_state("No status editors yet.", "Create an Admin or Responder before updating status.")
            else:
                with st.form("status_form"):
                    incident_options = {
                        f"#{int(row['id'])} - {row['title']} - {row['status']}": int(row["id"])
                        for _, row in incidents.iterrows()
                    }
                    manager_options = {
                        f"{row['name']} - {row['role']} - ID {int(row['id'])}": int(row["id"])
                        for _, row in managers.iterrows()
                    }
                    selected_incident = st.selectbox("Incident", list(incident_options.keys()), key="status_incident")
                    selected_status = st.selectbox("New status", ["Reported", "In Progress", "Closed"])
                    selected_manager = st.selectbox("Updated by", list(manager_options.keys()))
                    submitted = st.form_submit_button("Update status")
                    if submitted:
                        status_id = next(key for key, value in STATUS_LABELS.items() if value == selected_status)
                        with st.spinner("Updating status..."):
                            ok, message = put_update_status(
                                incident_options[selected_incident],
                                status_id,
                                manager_options[selected_manager],
                            )
                        if ok:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)


def people_and_audit(snapshot: dict[str, pd.DataFrame]) -> None:
    users = snapshot["users"]
    audit = snapshot["audit"]

    render_section_heading(
        "Administration",
        "People & Audit",
        "Manage campus roles and review the system history created by operational actions.",
    )
    user_tab, audit_tab = st.tabs(["People", "Audit Trail"])

    with user_tab:
        render_section_heading("Directory", "People")
        cols = st.columns((0.9, 1.1), gap="large")
        with cols[0]:
            st.markdown(
                """
                <div class="panel">
                    <div class="section-eyebrow">New profile</div>
                    <div class="section-copy">Roles control what users can do in the response workflow.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.form("create_any_user", clear_on_submit=True):
                name = st.text_input("Name", placeholder="Example: Alex Morgan")
                role = st.selectbox("Role", ["Student", "Responder", "Admin"])
                submitted = st.form_submit_button("Create user")
                if submitted:
                    clean_name = name.strip()
                    if len(clean_name) < 2:
                        st.error("Enter a name with at least 2 characters.")
                    else:
                        with st.spinner("Creating user..."):
                            ok, payload = post_create_user(clean_name, role)
                        if ok:
                            st.success(f"Created {payload['name']} as {role}.")
                            st.rerun()
                        else:
                            st.error(str(payload))
        with cols[1]:
            if users.empty:
                render_empty_state("No people yet.", "Create the first campus profile to begin reporting and assigning incidents.")
            else:
                display = users.sort_values(["role", "name"])[["id", "name", "role"]].rename(
                    columns={"id": "ID", "name": "Name", "role": "Role"}
                )
                st.markdown('<div class="table-caption">Campus directory</div>', unsafe_allow_html=True)
                st.dataframe(display, hide_index=True, width="stretch")

    with audit_tab:
        render_section_heading("History", "Audit Trail")
        if audit.empty:
            render_empty_state("No audit events yet.", "Create or update an incident to start the audit trail.")
        else:
            display = audit[["time", "actor", "action", "incident_id"]].rename(
                columns={
                    "time": "Time",
                    "actor": "Actor",
                    "action": "Action",
                    "incident_id": "Incident ID",
                }
            )
            st.markdown('<div class="table-caption">Recent system events</div>', unsafe_allow_html=True)
            st.dataframe(display, hide_index=True, width="stretch")


def main() -> None:
    inject_styles()
    snapshot = load_snapshot()
    page = render_sidebar(snapshot)
    render_header(snapshot)

    if page == "Dashboard":
        dashboard(snapshot)
    elif page == "Report Incident":
        report_incident(snapshot)
    elif page == "Response Center":
        response_center(snapshot)
    else:
        people_and_audit(snapshot)


if __name__ == "__main__":
    main()
