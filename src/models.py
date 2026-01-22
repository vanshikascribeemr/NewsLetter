from typing import List, Optional
from pydantic import BaseModel, Field

class FollowUpComment(BaseModel):
    comment: str

class Task(BaseModel):
    taskId: int
    taskSubject: str
    taskStatus: str
    taskPriority: str
    assigneeName: str
    taskSummary: Optional[str] = None
    followUpComments: List[str] = Field(default_factory=list)

class NewsletterContent(BaseModel):
    content: str
    totalTasks: int

class WorkflowState(BaseModel):
    categoryId: int
    tasks: List[Task] = Field(default_factory=list)
    newsletter: Optional[NewsletterContent] = None
    error: Optional[str] = None
