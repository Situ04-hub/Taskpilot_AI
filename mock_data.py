from datetime import datetime, timedelta
from models import Task, SourceEnum, SeverityEnum

# Base structured mock tasks
JIRA_TASKS = [
    Task(
        id="JIRA-101",
        title="Fix authentication bypass in SSO module",
        description="A critical vulnerability in the SSO module allows users to bypass 2FA when using legacy endpoints. Needs immediate remediation.",
        source=SourceEnum.JIRA,
        severity=SeverityEnum.P1,
        deadline=datetime.now() + timedelta(days=1),
        dependencies=[],
        business_impact=10,
        derived_priority_score=9.8,
        transparency_reason="High risk of data breach and regulatory penalty."
    ),
    Task(
        id="JIRA-102",
        title="Update database indexes for user table",
        description="User search queries are taking > 5 seconds. Adding composite indexes should resolve this.",
        source=SourceEnum.JIRA,
        severity=SeverityEnum.P3,
        deadline=datetime.now() + timedelta(days=7),
        dependencies=[],
        business_impact=5,
        derived_priority_score=4.5,
        transparency_reason="Improves user experience but not critical."
    )
]

SERVICENOW_TASKS = [
    Task(
        id="INC-5001",
        title="Payment gateway timeout issue",
        description="Payment gateway is occasionally timing out during peak hours. Customers are unable to complete checkout.",
        source=SourceEnum.SERVICENOW,
        severity=SeverityEnum.P2,
        deadline=datetime.now() + timedelta(days=2),
        dependencies=["JIRA-102"],
        business_impact=8,
        derived_priority_score=7.5,
        transparency_reason="Direct impact on revenue generation."
    )
]

GITHUB_TASKS = [
    Task(
        id="GH-89",
        title="Refactor task ingestion pipeline",
        description="The current task ingestion script is tightly coupled and hard to test. Refactor into modular components.",
        source=SourceEnum.GITHUB,
        severity=SeverityEnum.P4,
        deadline=datetime.now() + timedelta(days=14),
        dependencies=[],
        business_impact=3,
        derived_priority_score=2.5,
        transparency_reason="Technical debt reduction."
    )
]

# Unstructured Data
OUTLOOK_EMAIL_THREAD = """
From: Sarah Jenkins (Product Manager)
To: Engineering Team
Subject: URGENT: Memory Leak in Production

Hi team,
I've noticed that the main application server is restarting every 4 hours due to an Out Of Memory (OOM) error. 
Can someone please investigate the memory leak in the analytics microservice? This is causing sporadic downtime.
We need this fixed by Friday before the marketing push.

Thanks,
Sarah
"""

SLACK_TRANSCRIPT = """
[10:15 AM] @dev_lead: Hey team, the payment gateway is timing out again.
[10:17 AM] @backend_eng: Yeah, I'm seeing the logs. It looks like the timeout is happening during the peak load hours.
[10:20 AM] @dev_lead: Can you create a ticket and look into fixing the payment gateway timeout issue? Customers can't checkout.
[10:22 AM] @backend_eng: Will do. I'll add retry logic and increase the timeout threshold.
"""

def get_all_structured_tasks() -> list:
    return JIRA_TASKS + SERVICENOW_TASKS + GITHUB_TASKS
