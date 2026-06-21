import streamlit as st
import requests
import pandas as pd
import time

if "authorized" not in st.session_state:
    st.session_state.authorized = False

if not st.session_state.authorized:
    st.title("🛡️ TaskPilot Agent Authorization")
    st.markdown("TaskPilot requires read-only access to your local API logs to provide autonomous prioritization.")
    if st.button("Grant Access to Local Channels"):
        st.session_state.authorized = True
        st.rerun()
    st.stop()  # This halts the app until they click the button

# 1. Page Configuration & CSS Styling
st.set_page_config(page_title="TaskPilot AI Dashboard", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0B0F19; color: #F1F5F9; }
    .metric-container {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        padding: 20px; border-radius: 12px; border: 1px solid #334155;
    }
    .metric-value { font-size: 2.2rem; font-weight: 800; color: #FFFFFF; }
    .metric-title { font-size: 0.9rem; font-weight: 600; color: #94A3B8; }
    .priority-card { background-color: #151F32; border: 1px solid #243552; border-radius: 12px; padding: 16px; margin-bottom: 12px; }
    .priority-card-escalated { background-color: #2A1418; border: 1px solid #7F1D1D; border-radius: 12px; padding: 16px; margin-bottom: 12px; animation: pulseBorder 1.6s infinite; }
    .priority-card-title { font-size: 1.15rem; font-weight: 700; color: #FFFFFF; }
    .transparency-box { background-color: #0F172A; padding: 10px; border-radius: 6px; border: 1px dashed #38BDF8; color: #38BDF8; font-size: 0.88rem; margin-top: 8px; }
    .tag-source { background-color: #38BDF8; color: #0F172A; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }
    .tag-escalated { background-color: #EF4444; color: #FFFFFF; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; margin-left: 8px; }
    .roi-card {
        background: linear-gradient(135deg, #064E3B 0%, #022C22 100%);
        border: 1px solid #10B981; border-radius: 14px; padding: 22px; margin-bottom: 18px;
    }
    .roi-value { font-size: 2.6rem; font-weight: 900; color: #34D399; }
    .roi-title { font-size: 1rem; font-weight: 700; color: #A7F3D0; }
    .roi-sub { font-size: 0.82rem; color: #6EE7B7; margin-top: 4px; }
    .alert-banner {
        background-color: #7F1D1D; border: 1px solid #EF4444; border-radius: 10px;
        padding: 14px 18px; margin-bottom: 16px; color: #FECACA; font-weight: 600;
        animation: pulseBg 1.6s infinite;
    }
    .schedule-block-work { background-color: #1E293B; border-left: 4px solid #38BDF8; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; }
    .schedule-block-buffer { background-color: #151F32; border-left: 4px solid #475569; border-radius: 6px; padding: 8px 14px; margin-bottom: 8px; color: #94A3B8; font-size: 0.85rem; }
    .agent-log-entry { background-color: #0F172A; border-left: 3px solid #A855F7; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px; font-size: 0.85rem; color: #E9D5FF; }
    .agent-log-task { color: #C084FC; font-weight: 700; }
    @keyframes pulseBorder { 0% { border-color: #7F1D1D; } 50% { border-color: #EF4444; } 100% { border-color: #7F1D1D; } }
    @keyframes pulseBg { 0% { background-color: #7F1D1D; } 50% { background-color: #991B1B; } 100% { background-color: #7F1D1D; } }
    </style>
""", unsafe_allow_html=True)

# 2. Define Backend Connections (Points to your FastAPI agent server)
BACKEND_URL = "http://127.0.0.1:8000"


@st.cache_data(ttl=1)
def get_latest_tasks():
    try:
        response = requests.get(f"{BACKEND_URL}/api/tasks/prioritized", timeout=2)
        if response.status_code == 200:
            return response.json(), True
    except Exception:
        pass
    return [{"title": "System offline, showing cached tasks...", "source": "LOCAL", "score": 0}], False


@st.cache_data(ttl=1)
def get_gmail_status():
    try:
        response = requests.get(f"{BACKEND_URL}/api/gmail_status", timeout=2)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {"ok": False, "message": "Backend unreachable.", "count": 0}


@st.cache_data(ttl=1)
def get_agent_activity():
    try:
        response = requests.get(f"{BACKEND_URL}/api/agent_activity", timeout=2)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []


@st.cache_data(ttl=1)
def get_roi():
    try:
        response = requests.get(f"{BACKEND_URL}/api/roi", timeout=2)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {"total_minutes": 0, "dedup_count": 0, "summarized_count": 0, "total_hours_display": 0}


@st.cache_data(ttl=1)
def get_schedule():
    try:
        response = requests.get(f"{BACKEND_URL}/api/schedule", timeout=2)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []


@st.cache_data(ttl=1)
def get_alerts():
    try:
        response = requests.get(f"{BACKEND_URL}/api/alerts", timeout=2)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []


# 2. UI Controls
st.markdown("### Controls")
ctrl_col1, ctrl_col2, ctrl_col3 = st.columns(3)
with ctrl_col1:
    if st.button("🔄 Sync with Local Workspace"):
        st.cache_data.clear()
        st.rerun()
with ctrl_col2:
    if st.button("📧 Refresh Real Gmail Inbox"):
        try:
            requests.post(f"{BACKEND_URL}/api/tasks/refresh", timeout=15)
            st.cache_data.clear()
            st.rerun()
        except Exception:
            st.error("Could not refresh — backend unreachable.")
with ctrl_col3:
    if st.button("🔥 Simulate New P1 Defect", type="primary"):
        try:
            resp = requests.post(f"{BACKEND_URL}/api/tasks/simulate_p1", timeout=5)
            if resp.status_code == 200:
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Could not inject defect — backend unreachable.")
        except Exception:
            st.error("Connection error: Ensure your backend is running.")

tasks_list, is_connected = get_latest_tasks()
gmail_status = get_gmail_status()
roi_data = get_roi()
schedule_data = get_schedule()
alerts_data = get_alerts()
agent_activity = get_agent_activity()

if "messages" not in st.session_state:
    st.session_state.messages = []

# 2.5 GMAIL CONNECTION STATUS — only meaningful if the backend itself is reachable
if is_connected:
    if gmail_status.get("ok") and gmail_status.get("count", 0) > 0:
        st.success(f"📧 Real Gmail: {gmail_status.get('message')}")
    elif gmail_status.get("ok"):
        st.info(f"📧 Real Gmail: {gmail_status.get('message')}")
    else:
        st.warning(f"📧 Real Gmail not connected: {gmail_status.get('message')}")

# 3. UI Header
st.title("TaskPilot AI Engine")
if is_connected:
    st.success("🟢 Connected to Live Autonomous Agent Core Engine")
else:
    st.error("🔴 Backend unreachable. Run `python main.py` in a separate terminal (it must stay open), then click 'Sync with Local Workspace' above.")
    st.markdown("---")
    st.stop()  # No point rendering fake placeholder cards below — be honest about the state instead.

st.markdown("---")

# 3.5 PULSING SLA / "LOUDNESS" ALERT BANNER
if alerts_data:
    top_alert = alerts_data[0]
    st.markdown(f"""
        <div class="alert-banner">
            ⚠️ Critical Action Required: {len(alerts_data)} task(s) escalated —
            "<strong>{top_alert.get('title','')}</strong>" is within SLA breach window or flagged urgent.
            Bumped to top of queue.
        </div>
    """, unsafe_allow_html=True)

# 4. CONTEXT-SWITCH TAX ROI TRACKER
roi_minutes = roi_data.get("total_minutes", 0)
roi_hours = roi_data.get("total_hours_display", 0)
dedup_count = roi_data.get("dedup_count", 0)
summarized_count = roi_data.get("summarized_count", 0)

st.markdown(f"""
    <div class="roi-card">
        <div class="roi-title">⏱️ Focus Time Reclaimed Today (Context-Switch Tax ROI)</div>
        <div class="roi-value">{roi_minutes} min  <span style="font-size:1.1rem; color:#A7F3D0;">(~{roi_hours} hrs)</span></div>
        <div class="roi-sub">{dedup_count} duplicate task(s) merged (×23 min saved each) · {summarized_count} unstructured item(s) auto-summarized (×45 min saved each)</div>
    </div>
""", unsafe_allow_html=True)

# 5. KPI Top Rows
m_col1, m_col2, m_col3, m_col4 = st.columns(4)
with m_col1:
    st.markdown(f'<div class="metric-container"><div class="metric-title">Active Tasks Running</div><div class="metric-value">{len(tasks_list)}</div></div>', unsafe_allow_html=True)
with m_col2:
    st.markdown('<div class="metric-container"><div class="metric-title">Unstructured Sources Parsed</div><div class="metric-value">4 Channel Logs</div></div>', unsafe_allow_html=True)
with m_col3:
    st.markdown(f'<div class="metric-container"><div class="metric-title">Escalated / SLA-Critical</div><div class="metric-value">{len(alerts_data)}</div></div>', unsafe_allow_html=True)
with m_col4:
    st.markdown('<div class="metric-container"><div class="metric-title">SLA Breach Penalties Prevented</div><div class="metric-value">3</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 6. Split Main Area
left_col, right_col = st.columns([2, 1])

with left_col:
    st.markdown("### 🧠 Live Agent Prioritization Queue")

    for idx, task in enumerate(tasks_list):
        title = task.get("title", task.get("task_name", "Unnamed Assignment Task"))
        source = task.get("source", "Cross-Channel")
        score = task.get("score", task.get("derived_priority_score", 5.0))
        reason = task.get("reason", task.get("transparency_reason", "Computed by agent weighting metrics across active SLAs."))
        escalated = task.get("is_escalated", False)

        card_class = "priority-card-escalated" if escalated else "priority-card"
        escalated_tag = '<span class="tag-escalated">⚠️ ESCALATED</span>' if escalated else ""

        st.markdown(f"""
            <div class="{card_class}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span><span class="tag-source">{source.upper()}</span>{escalated_tag}</span>
                    <strong style="color:#00FF66; font-size:1.1rem;">Score: {score}</strong>
                </div>
                <div class="priority-card-title">{idx+1}. {title}</div>
                <div class="transparency-box">
                    <strong>Agent Reason:</strong> {reason}
                </div>
            </div>
        """, unsafe_allow_html=True)

    # DEEP WORK TIME-BLOCKING SCHEDULE
    st.markdown("### 🗓️ Deep Work Schedule — Today")
    if schedule_data:
        for block in schedule_data:
            if block["type"] == "deep_work":
                st.markdown(f"""
                    <div class="schedule-block-work">
                        <strong>{block['start']} – {block['end']}</strong> &nbsp;|&nbsp; {block['label']}
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="schedule-block-buffer">
                        {block['start']} – {block['end']} &nbsp;|&nbsp; {block['label']}
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Schedule will appear once tasks are loaded.")

with right_col:
    st.markdown("### 🚨 System Action Controls")

    if tasks_list and len(tasks_list) > 0:
        if st.button("🚀 Agent: Execute Auto-Remediation", use_container_width=True, type="primary"):
            top_task_id = tasks_list[0].get("id", "Unknown")
            try:
                response = requests.post(f"{BACKEND_URL}/api/tasks/auto_fix", json={"task_id": top_task_id}, timeout=5)
                if response.status_code == 200:
                    st.success(f"Agent successfully applied hotfix to: {top_task_id}")
                else:
                    st.error("Agent failed to execute remediation. Backend unreachable.")
            except Exception:
                st.error("Connection error: Ensure your backend is running.")
            st.rerun()
    else:
        st.info("No active tasks to remediate.")

    st.markdown("#### ⚠️ Active Escalations")
    if alerts_data:
        for a in alerts_data[:5]:
            st.markdown(f"- **{a.get('title','')}** ({a.get('id','')})")
    else:
        st.caption("No escalated tasks right now.")

    st.markdown("---")
    st.markdown("### 🤖 Autonomous Agent Activity")
    st.caption("Live feed of actions the background agent (`autonomous_agent.py`) takes on its own — no button clicks required. Run it in a separate terminal: `python autonomous_agent.py`")

    auto_refresh = st.checkbox("🔁 Auto-refresh every 4s", value=False)

    if agent_activity:
        for entry in agent_activity[:8]:
            st.markdown(f"""
                <div class="agent-log-entry">
                    <span class="agent-log-task">{entry.get('task_id','')}</span> — {entry.get('log','')}
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No autonomous actions yet. Start `python autonomous_agent.py` in a separate terminal — it will pick up any OPEN + ESCALATED task on its own.")

    if auto_refresh:
        time.sleep(4)
        st.cache_data.clear()
        st.rerun()

# 7. Conversational Agent Hub (Hits your actual POST /api/chat backend endpoint)
st.markdown("---")
st.markdown("### 💬 Chat directly with TaskPilot Chief of Staff")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask TaskPilot to summarize your schedule or explain a decision..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        resp = requests.post(f"{BACKEND_URL}/api/chat", json={"message": prompt}, timeout=5)
        if resp.status_code == 200:
            agent_reply = resp.json().get("reply", "No response from agent.")
        else:
            agent_reply = "Agent backend returned an error. Is main.py running?"
    except Exception:
        agent_reply = "Connection error: Ensure your FastAPI backend (main.py) is running on port 8000."

    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(agent_reply)
    st.session_state.messages.append({"role": "assistant", "content": agent_reply})