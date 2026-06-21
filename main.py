try:
    from dotenv import load_dotenv
    load_dotenv()  # loads GMAIL_USER / GMAIL_APP_PASSWORD from .env if present
except ImportError:
    pass  # python-dotenv not installed — fine, just export env vars manually instead

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from models import Task, SourceEnum, TaskStatusEnum
from pipeline import process_pipeline, get_task_by_id, inject_new_defect, calculate_focus_time_reclaimed
from agent_engine import prioritize_tasks
from planner import generate_deep_work_schedule
from gmail_loader import get_last_gmail_status

app = FastAPI(title="TaskPilot AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- In-memory "live" task store (so PUT / re-prioritize persist across requests) ----------
_live_tasks: Optional[List[Task]] = None

def get_live_tasks() -> List[Task]:
    global _live_tasks
    if _live_tasks is None:
        tasks = process_pipeline()            # ingest (real Gmail + mocks) + extract + dedupe + escalation flags
        _live_tasks = prioritize_tasks(tasks)  # score + sort + transparency reasons
    return _live_tasks


@app.get("/")
def root():
    return {"status": "TaskPilot AI backend running"}


@app.get("/api/tasks/prioritized")
def get_prioritized_tasks():
    tasks = get_live_tasks()
    return [t.model_dump(mode="json") for t in tasks]


@app.get("/api/tasks/email")
def get_email_tasks():
    return [t.model_dump(mode="json") for t in get_live_tasks() if t.source in (SourceEnum.EMAIL, SourceEnum.OUTLOOK)]


@app.get("/api/gmail_status")
def gmail_status():
    """Diagnostic endpoint: shows exactly why real Gmail did/didn't load."""
    return get_last_gmail_status()


@app.get("/api/agent_activity")
def agent_activity():
    """Shows the autonomous_agent.py worker's recent actions across all tasks,
    proving the agent acted on its own without a human clicking anything."""
    tasks = get_live_tasks()
    activity = []
    for t in tasks:
        for log in t.agent_logs:
            activity.append({"task_id": t.id, "title": t.title, "log": log})
    # Most recently appended logs last; show newest first, capped to last 15
    return list(reversed(activity))[:15]


@app.get("/api/roi")
def get_roi():
    """Context-Switch Tax ROI Tracker — minutes of focus time reclaimed via dedup + auto-summarization."""
    tasks = get_live_tasks()
    return calculate_focus_time_reclaimed(tasks)


@app.get("/api/schedule")
def get_schedule():
    """Deep Work time-blocked schedule for the top 3 prioritized tasks."""
    tasks = get_live_tasks()
    return generate_deep_work_schedule(tasks)


@app.get("/api/alerts")
def get_alerts():
    """Pulsing SLA breach / 'loudness' alerts — tasks escalated due to deadline or urgent language."""
    tasks = get_live_tasks()
    escalated = [t for t in tasks if t.is_escalated]
    return [t.model_dump(mode="json") for t in escalated]


class StatusUpdate(BaseModel):
    status: str
    log: Optional[str] = None


@app.put("/api/tasks/{task_id}")
def update_task(task_id: str, update: StatusUpdate):
    tasks = get_live_tasks()
    for t in tasks:
        if t.id == task_id:
            try:
                t.status = TaskStatusEnum(update.status)
            except ValueError:
                pass
            if update.log:
                t.agent_logs.append(update.log)
            return {"ok": True, "task": t.model_dump(mode="json")}
    return {"ok": False, "error": "Task not found"}


class AutoFixRequest(BaseModel):
    task_id: str


@app.post("/api/tasks/auto_fix")
def auto_fix(req: AutoFixRequest):
    tasks = get_live_tasks()
    for t in tasks:
        if t.id == req.task_id:
            t.status = TaskStatusEnum.RESOLVED
            t.agent_logs.append("Auto-remediation triggered from dashboard.")
            return {"ok": True, "message": f"Remediation applied to {req.task_id}"}
    return {"ok": False, "error": "Task not found"}


@app.post("/api/tasks/simulate_p1")
def simulate_p1():
    """Demo show-stopper: inject a fresh P1 defect and re-rank live."""
    global _live_tasks
    tasks = get_live_tasks()
    new_task = inject_new_defect()
    tasks.append(new_task)
    _live_tasks = prioritize_tasks(tasks)
    return {"ok": True, "injected": new_task.model_dump(mode="json")}


@app.post("/api/tasks/refresh")
def refresh_tasks():
    """Re-pulls from all sources, including real Gmail, clearing caches."""
    global _live_tasks
    tasks = process_pipeline(force_refresh=True)
    _live_tasks = prioritize_tasks(tasks)
    return {"ok": True, "count": len(_live_tasks)}


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
def chat(req: ChatRequest):
    tasks = get_live_tasks()
    q = req.message.lower().strip()

    if not tasks:
        return {"reply": "No tasks loaded yet."}

    # Broad keyword sets so informal phrasing ("so 1st", "which work to be done") still resolves.
    least_kw = ["least", "bottom", "lowest", "last", "defer", "skip", "ignore"]
    top_kw = ["top", "first", "1st", "priority", "important", "what should i", "which work",
              "what work", "what to do", "what next", "begin", "start with", "do first", "main task"]
    why_kw = ["why", "reason", "explain", "because"]
    schedule_kw = ["schedule", "plan", "calendar", "block", "time", "day look"]
    alert_kw = ["escalat", "alert", "sla", "urgent", "critical", "breach", "fire", "loud"]
    list_kw = ["all task", "list", "everything", "summary", "summarize", "overview", "show me", "what do i have"]

    def matches(keywords):
        return any(k in q for k in keywords)

    if matches(least_kw):
        t = tasks[-1]
        reply = f"Your least important task is **{t.title}** ({t.id}). {t.transparency_reason}"
    elif matches(top_kw):
        t = tasks[0]
        reply = f"Your top priority is **{t.title}** ({t.id}). {t.transparency_reason}"
    elif matches(why_kw):
        t = tasks[0]
        reply = f"Explainable AI: {t.transparency_reason}"
    elif matches(schedule_kw):
        roi = calculate_focus_time_reclaimed(tasks)
        reply = f"Your top 3 tasks are mapped into deep work blocks starting at 9 AM. You've also reclaimed {roi['total_minutes']} minutes today via deduplication and auto-summarization — check the Focus Time card above."
    elif matches(alert_kw):
        escalated = [t for t in tasks if t.is_escalated]
        if escalated:
            reply = f"⚠️ {len(escalated)} task(s) are escalated right now, including **{escalated[0].title}** — within 24h of SLA breach or flagged urgent."
        else:
            reply = "No tasks are currently escalated. You're clear of SLA breaches for now."
    elif matches(list_kw):
        top5 = tasks[:5]
        lines = [f"{i+1}. **{t.title}** ({t.source.value}, score {t.derived_priority_score})" for i, t in enumerate(top5)]
        reply = "Here's your current ranked queue:\n" + "\n".join(lines)
    else:
        sources = set(t.source.value for t in tasks)
        reply = f"I'm tracking {len(tasks)} tasks across {len(sources)} sources ({', '.join(sorted(sources))}). Ask me about your top or least priority task, why something is ranked, your schedule, or active SLA alerts."

    return {"reply": reply}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)