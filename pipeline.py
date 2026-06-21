import re
import math
from datetime import datetime, timedelta
from typing import List, Dict
from models import Task, SourceEnum, SeverityEnum
from mock_data import get_all_structured_tasks, OUTLOOK_EMAIL_THREAD, SLACK_TRANSCRIPT
from gmail_loader import fetch_real_gmail_tasks

LOUD_KEYWORDS = ["urgent", "critical", "production", "down", "outage", "asap", "sev1", "p1"]


def is_sla_escalated(task: Task) -> bool:
    """Section 3 of the manual: engineers chase what's LOUD, not what matters.
    We make the loudness signal explicit and visible instead of letting it silently bias humans."""
    hours_left = (task.deadline.replace(tzinfo=None) - datetime.now()).total_seconds() / 3600.0
    text = f"{task.title} {task.description}".lower()
    has_loud_keyword = any(kw in text for kw in LOUD_KEYWORDS)
    return hours_left <= 24 or (has_loud_keyword and task.severity == SeverityEnum.P1)


def extract_tasks_from_text(text: str, source: SourceEnum) -> List[Task]:
    tasks = []
    # Simple regex to find sentences containing action keywords
    action_keywords = r"(?i)(investigate|fix|look into|resolve|create a ticket for)\s+([^.]+)"
    matches = re.finditer(action_keywords, text)

    for i, match in enumerate(matches):
        action = match.group(1).lower()
        context = match.group(2).strip()
        title = f"{action.capitalize()} {context[:30]}..."
        description = f"Extracted action: {action} {context}. Source context: {text[:100]}..."

        # Simple heuristic for severity
        severity = SeverityEnum.P3
        if "urgent" in text.lower() or "critical" in text.lower():
            severity = SeverityEnum.P1

        tasks.append(
            Task(
                id=f"{source.value}-EXT-{i+1}",
                title=title,
                description=description,
                source=source,
                severity=severity,
                deadline=datetime.now() + timedelta(days=3),
                dependencies=[],
                business_impact=7,
                derived_priority_score=6.0,
                transparency_reason="Extracted automatically from unstructured text communications.",
                is_summarized_unstructured=True,  # powers the ROI tracker: +45 min per summarized item
            )
        )
    return tasks


def get_term_frequencies(text: str) -> Dict[str, int]:
    words = re.findall(r'\w+', text.lower())
    tf = {}
    for word in words:
        tf[word] = tf.get(word, 0) + 1
    return tf


def cosine_similarity(text1: str, text2: str) -> float:
    tf1 = get_term_frequencies(text1)
    tf2 = get_term_frequencies(text2)

    intersection = set(tf1.keys()) & set(tf2.keys())
    numerator = sum([tf1[x] * tf2[x] for x in intersection])

    sum1 = sum([tf1[x]**2 for x in tf1.keys()])
    sum2 = sum([tf2[x]**2 for x in tf2.keys()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    else:
        return float(numerator) / denominator


def deduplicate_and_merge_tasks(tasks: List[Task]) -> List[Task]:
    merged_tasks = []
    skip_indices = set()

    for i in range(len(tasks)):
        if i in skip_indices:
            continue

        current_task = tasks[i]
        merged = False

        for j in range(i + 1, len(tasks)):
            if j in skip_indices:
                continue

            sim_score = cosine_similarity(current_task.description, tasks[j].description)
            title_sim_score = cosine_similarity(current_task.title, tasks[j].title)

            # Using combined similarity threshold
            if sim_score > 0.85 or title_sim_score > 0.85 or (sim_score > 0.5 and title_sim_score > 0.5):
                # Merge tasks
                merged_task = Task(
                    id=f"MERGED-{current_task.id}-{tasks[j].id}",
                    title=f"Combined: {current_task.title}",
                    description=f"{current_task.description}\n\n---\n\n{tasks[j].description}",
                    source=SourceEnum.MULTI_CHANNEL,
                    severity=min(current_task.severity, tasks[j].severity, key=lambda x: x.value),  # P1 < P2 < P3 < P4
                    deadline=min(current_task.deadline, tasks[j].deadline),
                    dependencies=list(set(current_task.dependencies + tasks[j].dependencies)),
                    business_impact=max(current_task.business_impact, tasks[j].business_impact),
                    derived_priority_score=max(current_task.derived_priority_score, tasks[j].derived_priority_score),
                    transparency_reason=f"Merged due to high semantic similarity ({(max(sim_score, title_sim_score)*100):.1f}%).",
                    is_merged_duplicate=True,  # powers the ROI tracker: +23 min per merge
                )
                merged_tasks.append(merged_task)
                skip_indices.add(j)
                merged = True
                break

        if not merged:
            merged_tasks.append(current_task)

    return merged_tasks


def apply_escalation_flags(tasks: List[Task]) -> List[Task]:
    for t in tasks:
        t.is_escalated = is_sla_escalated(t)
    return tasks


def calculate_focus_time_reclaimed(tasks: List[Task]) -> Dict[str, int]:
    """Context-Switch Tax ROI Tracker.
    +23 min for every deduplicated/merged task (one less context switch to track it twice)
    +45 min for every unstructured item auto-extracted/summarized (time saved not reading raw threads)
    """
    dedup_count = sum(1 for t in tasks if t.is_merged_duplicate)
    summarized_count = sum(1 for t in tasks if t.is_summarized_unstructured)

    dedup_minutes = dedup_count * 23
    summarized_minutes = summarized_count * 45
    total_minutes = dedup_minutes + summarized_minutes

    return {
        "dedup_count": dedup_count,
        "summarized_count": summarized_count,
        "dedup_minutes": dedup_minutes,
        "summarized_minutes": summarized_minutes,
        "total_minutes": total_minutes,
        "total_hours_display": round(total_minutes / 60.0, 1),
    }


_cached_tasks = None


def process_pipeline(force_refresh: bool = False) -> List[Task]:
    global _cached_tasks
    if _cached_tasks is not None and not force_refresh:
        return _cached_tasks

    # 1. Ingest structured (mock Jira/ServiceNow/GitHub)
    structured_tasks = get_all_structured_tasks()

    # 2. Ingest REAL Gmail (read-only, fails safe to [] if not configured/unreachable)
    real_gmail_tasks = fetch_real_gmail_tasks()

    # 3. Extract unstructured (mock Outlook thread + Slack transcript)
    outlook_tasks = extract_tasks_from_text(OUTLOOK_EMAIL_THREAD, SourceEnum.OUTLOOK)
    slack_tasks = extract_tasks_from_text(SLACK_TRANSCRIPT, SourceEnum.SLACK)

    all_tasks = structured_tasks + real_gmail_tasks + outlook_tasks + slack_tasks

    # 4. Deduplicate and merge
    consolidated_tasks = deduplicate_and_merge_tasks(all_tasks)

    # 5. Flag SLA escalation / "loudness" signals
    consolidated_tasks = apply_escalation_flags(consolidated_tasks)

    _cached_tasks = consolidated_tasks
    return consolidated_tasks


def inject_new_defect() -> Task:
    """Used by the live demo 'Simulate new P1 defect' button to show real-time re-prioritization."""
    import random
    suffix = random.randint(1000, 9999)
    return Task(
        id=f"INC-{suffix}",
        title="Production outage: checkout service returning 500s",
        description="Live incident just paged in. Checkout service is throwing 500 errors for all users. Revenue-impacting, customer-facing.",
        source=SourceEnum.SERVICENOW,
        severity=SeverityEnum.P1,
        deadline=datetime.now() + timedelta(hours=2),
        dependencies=[],
        business_impact=10,
        transparency_reason="Newly injected live P1 incident - pending re-scoring.",
        is_escalated=True,
    )


def get_task_by_id(task_id: str) -> Task:
    tasks = process_pipeline()
    for t in tasks:
        if t.id == task_id:
            return t
    return None