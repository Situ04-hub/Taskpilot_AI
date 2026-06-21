from typing import List
from datetime import datetime
from models import Task, SeverityEnum

def prioritize_tasks(tasks: List[Task]) -> List[Task]:
    now = datetime.now()
    
    for task in tasks:
        # 1. Severity points
        severity_points = 0.0
        if task.severity == SeverityEnum.P1:
            severity_points = 4.0
        elif task.severity == SeverityEnum.P2:
            severity_points = 2.5
        elif task.severity == SeverityEnum.P3:
            severity_points = 1.0
        elif task.severity == SeverityEnum.P4:
            severity_points = 0.5

        # 2. Deadline proximity points
        time_diff = task.deadline.replace(tzinfo=None) - now
        hours_until_deadline = time_diff.total_seconds() / 3600.0
        
        if hours_until_deadline <= 24:
            deadline_points = 3.0
            deadline_desc = "breaches its deadline within 24 hours"
        elif hours_until_deadline >= 168:  # 7 days * 24 hours
            deadline_points = 0.0
            deadline_desc = "has a deadline more than 7 days away"
        else:
            # Linearly scale from 3.0 (at 24h) to 0.0 (at 168h)
            deadline_points = 3.0 * (1 - ((hours_until_deadline - 24) / 144.0))
            deadline_desc = f"has a deadline in about {int(hours_until_deadline / 24)} days"

        # 3. Dependencies count points
        dependencies_count = len(task.dependencies) if task.dependencies else 0
        dependencies_points = min(dependencies_count * 0.5, 2.0)

        # 4. Business impact points
        business_impact_points = min(task.business_impact * 0.1, 1.0)

        # Derived priority score calculation
        total_score = severity_points + deadline_points + dependencies_points + business_impact_points
        task.derived_priority_score = min(round(total_score, 1), 10.0)

        # AI Transparency Reason
        rank_level = "Ranked highly" if task.derived_priority_score >= 7.0 else "Ranked moderately" if task.derived_priority_score >= 4.0 else "Ranked lower"
        
        task.transparency_reason = (
            f"{rank_level} (Score: {task.derived_priority_score}) because this is a {task.severity.value} issue "
            f"with {dependencies_count} blocking dependencies, a business impact of {task.business_impact}/10, "
            f"and it {deadline_desc}."
        )

    # Sort tasks from highest score to lowest score
    tasks.sort(key=lambda t: t.derived_priority_score, reverse=True)
    return tasks
