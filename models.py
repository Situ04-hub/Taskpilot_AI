from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional
from datetime import datetime, timedelta

class SourceEnum(str, Enum):
    JIRA = "JIRA"
    SLACK = "SLACK"
    EMAIL = "EMAIL"
    LOCAL_FILE = "LOCAL_FILE"
    SERVICENOW = "SERVICENOW"
    GITHUB = "GITHUB"
    OUTLOOK = "OUTLOOK"
    MULTI_CHANNEL = "MULTI_CHANNEL"

class TaskStatusEnum(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"

class SeverityEnum(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"

class Task(BaseModel):
    id: str
    title: str
    source: SourceEnum
    description: str = "No description provided."
    status: TaskStatusEnum = TaskStatusEnum.OPEN
    severity: SeverityEnum = SeverityEnum.P3
    business_impact: int = 0
    derived_priority_score: float = 0.0
    transparency_reason: str = "No reason provided."
    deadline: datetime = Field(default_factory=lambda: datetime.now() + timedelta(days=3))
    dependencies: List[str] = []
    agent_logs: List[str] = []
    is_escalated: bool = False          # True if SLA < 24h or "loud" keywords detected
    is_merged_duplicate: bool = False   # True if this task came from deduplication (for ROI tracker)
    is_summarized_unstructured: bool = False  # True if extracted/summarized from email or meeting text (for ROI tracker)