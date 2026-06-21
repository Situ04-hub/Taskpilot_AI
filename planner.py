"""
planner.py
----------
Turns the ranked task list into a "Deep Work" time-blocked daily schedule.
This is the agent doing actual planning, not just ranking — it answers
"when do I do this" not just "what should I do".
"""

from datetime import datetime, timedelta
from typing import List, Dict
from models import Task


def generate_deep_work_schedule(tasks: List[Task], start_hour: int = 9, top_n: int = 3) -> List[Dict]:
    """Maps the top N prioritized tasks into 90-minute deep work blocks,
    separated by 30-minute buffer/email-review slots, starting at start_hour."""

    schedule = []
    current = datetime.now().replace(hour=start_hour, minute=0, second=0, microsecond=0)
    top_tasks = tasks[:top_n]

    for i, task in enumerate(top_tasks):
        block_end = current + timedelta(minutes=90)
        schedule.append({
            "start": current.strftime("%H:%M"),
            "end": block_end.strftime("%H:%M"),
            "type": "deep_work",
            "label": f"Deep Work Block {i+1}: {task.title}",
            "task_id": task.id,
            "score": task.derived_priority_score,
            "reason": task.transparency_reason,
        })
        current = block_end

        # Add buffer after each deep work block except the last
        if i < len(top_tasks) - 1:
            buffer_end = current + timedelta(minutes=30)
            schedule.append({
                "start": current.strftime("%H:%M"),
                "end": buffer_end.strftime("%H:%M"),
                "type": "buffer",
                "label": "Buffer / Email & Slack Review",
                "task_id": None,
                "score": None,
                "reason": None,
            })
            current = buffer_end

    return schedule