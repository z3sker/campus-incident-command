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
    "Reported": "#D94B45",
    "In Progress": "#D99A22",
    "Closed": "#258B62",
}

ZONE_OPTIONS = {
    "main_building": "Main Building",
    "dormitory": "Dormitory",
    "sports_complex": "Sports Complex",
    "cafeteria": "Cafeteria",
    "library": "Library",
}


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #18212f;
            --muted: #687182;
            --line: #dce2ea;
            --panel: #ffffff;
            --wash: #f5f7fa;
            --accent: #1f7a8c;
            --danger: #d94b45;
            --amber: #d99a22;
            --green: #258b62;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(31, 122, 140, 0.10), transparent 34rem),
                linear-gradient(180deg, #f7f9fb 0%, #eef3f6 100%);
            color: var(--ink);
        }

        [data-testid="stSidebar"] {
            background: #f8fafc;
            border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] label {
            color: var(--ink);
        }

        .block-container {
            padding-top: 2.2rem;
            padding-bottom: 3rem;
            max-width: 1260px;
        }

        h1, h2, h3 {
            color: var(--ink);
            letter-spacing: 0;
        }

        h1 {
            font-size: 2.3rem;
            line-height: 1.06;
            margin-bottom: 0.25rem;
        }

        h2 {
            margin-top: 0.6rem;
        }

        .app-kicker {
            color: var(--accent);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }

        .app-subtitle {
            color: var(--muted);
            font-size: 1.04rem;
            max-width: 760px;
            margin-bottom: 1.35rem;
        }

        .metric-card {
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1rem 1.05rem;
            box-shadow: 0 16px 35px rgba(24, 33, 47, 0.06);
            min-height: 118px;
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .metric-value {
            color: var(--ink);
            font-size: 2.15rem;
            line-height: 1;
            font-weight: 800;
            margin: 0.35rem 0 0.2rem;
        }

        .metric-note {
            color: var(--muted);
            font-size: 0.88rem;
        }

        .section-panel {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 16px 35px rgba(24, 33, 47, 0.045);
        }

        .incident-card {
            background: #ffffff;
            border: 1px solid var(--line);
            border-left: 5px solid var(--accent);
            border-radius: 8px;
            padding: 0.95rem 1rem;
            margin-bottom: 0.75rem;
            box-shadow: 0 12px 26px rgba(24, 33, 47, 0.045);
        }

        .incident-title {
            color: var(--ink);
            font-size: 1.05rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }

        .incident-meta {
            color: var(--muted);
            font-size: 0.86rem;
            margin-bottom: 0.6rem;
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
            padding: 0.22rem 0.62rem;
            font-size: 0.78rem;
            font-weight: 800;
            margin-right: 0.35rem;
            border: 1px solid transparent;
        }

        .chip-reported {
            color: #8f2924;
            background: #fde7e4;
            border-color: #f8c7c2;
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
            border-radius: 7px;
            border: 1px solid #1f7a8c;
            background: #1f7a8c;
            color: #ffffff;
            font-weight: 800;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            border-color: #145d6b;
            background: #145d6b;
            color: #ffffff;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.35rem;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 7px;
            padding: 0.55rem 0.8rem;
            background: #ffffff;
            border: 1px solid var(--line);
        }

        .stTabs [aria-selected="true"] {
            background: #e7f1f4;
            border-color: #9ec8d2;
        }

        @media (max-width: 800px) {
            h1 {
                font-size: 1.75rem;
            }

            .app-subtitle {
                font-size: 0.96rem;
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


def render_header() -> None:
    st.markdown('<div class="app-kicker">University Safety Operations</div>', unsafe_allow_html=True)
    st.title("Campus Incident Command")
    st.markdown(
        '<div class="app-subtitle">Report, triage, assign, and monitor campus incidents from one polished operational dashboard powered by the existing FastAPI backend.</div>',
        unsafe_allow_html=True,
    )


def render_metric(label: str, value: str | int, note: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{escape(str(label))}</div>
            <div class="metric-value">{escape(str(value))}</div>
            <div class="metric-note">{escape(str(note))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(title: str, body: str) -> None:
    st.info(f"{title} {body}")


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

    total = len(incidents)
    open_count = int((incidents["status"] != "Closed").sum()) if not incidents.empty else 0
    closed_count = int((incidents["status"] == "Closed").sum()) if not incidents.empty else 0
    responder_count = int((users["role"] == "Responder").sum()) if not users.empty else 0
    resolution_rate = f"{round((closed_count / total) * 100)}%" if total else "0%"

    cols = st.columns(4)
    with cols[0]:
        render_metric("Total Incidents", total, "All reports in the system")
    with cols[1]:
        render_metric("Active Work", open_count, "Reported or in progress")
    with cols[2]:
        render_metric("Resolution Rate", resolution_rate, f"{closed_count} closed incident{'s' if closed_count != 1 else ''}")
    with cols[3]:
        render_metric("Responders", responder_count, "Available response users")

    if incidents.empty:
        render_empty_state("No incidents yet.", "Create a user and report the first campus issue to populate the dashboard.")
        return

    chart_col, zone_col = st.columns((1.1, 0.9), gap="large")
    with chart_col:
        st.subheader("Incident Flow")
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
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis_title="",
            yaxis_title="Incidents",
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#18212f"),
        )
        fig.update_traces(textposition="outside", marker_line_width=0)
        st.plotly_chart(fig, width="stretch")

    with zone_col:
        st.subheader("Zone Concentration")
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

    st.subheader("Operational Snapshot")
    left, right = st.columns((0.95, 1.05), gap="large")
    with left:
        if analytics.empty:
            zone_summary = incidents.groupby("zone", as_index=False).size().rename(columns={"size": "incident_count"})
            zone_summary["resolved_count"] = 0
        else:
            zone_summary = analytics[["zone", "incident_count", "resolved_count"]].copy()
        zone_summary["open_count"] = zone_summary["incident_count"] - zone_summary["resolved_count"]
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

    st.subheader("Report a New Incident")
    st.caption("Students and admins can submit incidents. The backend validates the selected role before saving.")

    create_tab, quick_user_tab = st.tabs(["Incident Report", "Create Reporter"])

    with quick_user_tab:
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
            st.warning("Create a Student or Admin user before reporting an incident.")
            return

        reporter_options = {
            f"{row['name']} - {row['role']} - ID {int(row['id'])}": int(row["id"])
            for _, row in eligible.sort_values(["role", "name"]).iterrows()
        }

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

    st.subheader("Response Center")
    st.caption("Admins assign work to responders. Admins and responders can update incident status.")

    if incidents.empty:
        render_empty_state("No incidents available.", "Report an incident before assigning or updating response work.")
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
        st.markdown("#### Queue")
        if filtered.empty:
            st.info("No incidents match the current filters.")
        else:
            for _, row in filtered.head(10).iterrows():
                render_incident_card(row)

    with right:
        assign_tab, status_tab = st.tabs(["Assign", "Update Status"])

        with assign_tab:
            if admins.empty or responders.empty:
                st.warning("Create at least one Admin and one Responder before assigning incidents.")
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
                        st.info("All incidents are closed.")
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
                st.warning("Create an Admin or Responder before updating status.")
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

    user_tab, audit_tab = st.tabs(["People", "Audit Trail"])

    with user_tab:
        st.subheader("People")
        cols = st.columns((0.9, 1.1), gap="large")
        with cols[0]:
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
                st.info("No users have been created yet.")
            else:
                display = users.sort_values(["role", "name"])[["id", "name", "role"]].rename(
                    columns={"id": "ID", "name": "Name", "role": "Role"}
                )
                st.dataframe(display, hide_index=True, width="stretch")

    with audit_tab:
        st.subheader("Audit Trail")
        if audit.empty:
            st.info("No audit events have been recorded yet.")
        else:
            display = audit[["time", "actor", "action", "incident_id"]].rename(
                columns={
                    "time": "Time",
                    "actor": "Actor",
                    "action": "Action",
                    "incident_id": "Incident ID",
                }
            )
            st.dataframe(display, hide_index=True, width="stretch")


def main() -> None:
    inject_styles()
    render_header()

    with st.sidebar:
        st.markdown("### Navigation")
        page = st.radio(
            "Go to",
            ["Dashboard", "Report Incident", "Response Center", "People & Audit"],
            label_visibility="collapsed",
        )
        st.divider()
        st.markdown("### Workspace")
        if st.button("Refresh data", width="stretch"):
            st.cache_data.clear()
            st.rerun()
        if st.button("Load demo workspace", width="stretch"):
            with st.spinner("Creating demo users and incidents..."):
                try:
                    seed_demo_workspace()
                    st.success("Demo workspace loaded.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Demo data could not be loaded: {exc}")
        st.caption("SQLite storage is created automatically by the backend on first run.")

    snapshot = load_snapshot()

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
