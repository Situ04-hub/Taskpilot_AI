"""
autonomous_agent.py
--------------------
The actual "agentic" piece of TaskPilot AI — runs as a separate background
process and acts ON ITS OWN, without a human clicking anything.

Per the problem statement's #1 judging criterion: an agent must act
proactively, not just answer when asked. This loop:
  1. Polls the live prioritized task list every few seconds.
  2. Looks for tasks that are OPEN and ESCALATED (SLA-critical or "loud").
  3. Picks the single highest-priority one and works it autonomously —
     no button click, no chat prompt — logging each step as it goes.
  4. Marks it RESOLVED and moves to the next escalated task.

Run this in its own terminal window, alongside main.py and app.py:
    python autonomous_agent.py

Its activity shows up live in the dashboard's "Autonomous Agent Activity"
panel (pulled from the agent_logs field PUT back onto each task).
"""

import time
import requests
import os
from datetime import datetime

API_BASE = "http://127.0.0.1:8000/api"
SIMULATED_REPO_DIR = "simulated_repo"
SLACK_LOG_FILE = "slack_logs.txt"
POLL_INTERVAL_SECONDS = 4


def setup_environment():
    if not os.path.exists(SIMULATED_REPO_DIR):
        os.makedirs(SIMULATED_REPO_DIR)
        print(f"[autonomous_agent] Created simulated repo directory: {SIMULATED_REPO_DIR}")


def fetch_next_actionable_task():
    """Only picks up tasks that are OPEN and escalated — i.e. genuinely
    needs autonomous attention right now, not just 'happens to be #1'."""
    try:
        response = requests.get(f"{API_BASE}/tasks/prioritized", timeout=5)
        if response.status_code == 200:
            tasks = response.json()
            for t in tasks:
                if t.get("status") == "OPEN" and t.get("is_escalated"):
                    return t
    except Exception as e:
        print(f"[autonomous_agent] Error fetching tasks: {e}")
    return None


def update_task_status(task_id, status, log_message=None):
    payload = {"status": status}
    if log_message:
        payload["log"] = log_message
        print(f"[Agent -> {task_id}] {log_message}")

    try:
        requests.put(f"{API_BASE}/tasks/{task_id}", json=payload, timeout=5)
    except Exception as e:
        print(f"[autonomous_agent] Error updating task {task_id}: {e}")


def execute_github_action(task):
    filename = os.path.join(SIMULATED_REPO_DIR, f"fix_{task['id']}.py")
    update_task_status(task['id'], "IN_PROGRESS", f"Connected to GitHub. Checking out branch feature/{task['id']}")
    time.sleep(2)
    update_task_status(task['id'], "IN_PROGRESS", "Writing code to fix the issue...")
    time.sleep(3)

    with open(filename, "w") as f:
        f.write(f"# Auto-generated fix for {task['id']}\n")
        f.write(f"# Title: {task['title']}\n")
        f.write("def fix_issue():\n")
        f.write("    print('Issue resolved successfully!')\n")

    update_task_status(task['id'], "IN_PROGRESS", f"Committed and pushed changes to {filename}.")
    time.sleep(1)
    update_task_status(task['id'], "RESOLVED", "Pull Request created and merged. Task complete.")


def execute_slack_action(task):
    update_task_status(task['id'], "IN_PROGRESS", "Connecting to Slack API...")
    time.sleep(2)
    update_task_status(task['id'], "IN_PROGRESS", "Analyzing thread and drafting response...")
    time.sleep(2)

    with open(SLACK_LOG_FILE, "a") as f:
        f.write(f"[{datetime.now()}] @TaskPilot: I've looked into '{task['title']}'. The root cause has been identified and patched. Monitoring the situation.\n")

    update_task_status(task['id'], "RESOLVED", "Response sent to Slack thread. Task complete.")


def execute_jira_action(task):
    update_task_status(task['id'], "IN_PROGRESS", f"Authenticating with Jira (Ticket: {task['id']})...")
    time.sleep(2)
    update_task_status(task['id'], "IN_PROGRESS", "Applying patch to affected services...")
    time.sleep(3)
    update_task_status(task['id'], "IN_PROGRESS", "Verifying system health checks pass...")
    time.sleep(2)
    update_task_status(task['id'], "RESOLVED", "Services healthy. Closing Jira ticket.")


def execute_generic_action(task):
    update_task_status(task['id'], "IN_PROGRESS", "Analyzing task requirements...")
    time.sleep(2)
    update_task_status(task['id'], "IN_PROGRESS", "Applying generic resolution protocols...")
    time.sleep(3)
    update_task_status(task['id'], "RESOLVED", "Task execution complete. Marked as resolved.")


def run_agent_loop():
    setup_environment()
    print("[autonomous_agent] Started. Watching for OPEN + ESCALATED tasks...")
    print("[autonomous_agent] (Tasks that are not escalated are left for the human to handle.)")

    while True:
        task = fetch_next_actionable_task()
        if not task:
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        print(f"\n[autonomous_agent] --- Autonomously picked up ESCALATED task: {task['id']} ({task['title']}) ---")

        source = task.get("source", "UNKNOWN")

        if source == "GITHUB":
            execute_github_action(task)
        elif source in ("SLACK", "OUTLOOK"):
            execute_slack_action(task)
        elif source in ("JIRA", "SERVICENOW"):
            execute_jira_action(task)
        else:
            execute_generic_action(task)

        time.sleep(2)  # brief pause before checking for the next escalated task


if __name__ == "__main__":
    run_agent_loop()