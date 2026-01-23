from typing import List, Optional
from pydantic import BaseModel, Field

class FollowUpComment(BaseModel):
    comment: str

class Task(BaseModel):
    taskId: int = Field(alias="TaskId")
    taskSubject: str = Field(alias="SubjectLine")
    taskStatus: str = Field(alias="LastStatusCode")
    taskPriority: str = Field(alias="TaskPriority")
    assigneeName: str = Field(alias="TaskAssignedtoName")
    taskSummary: Optional[str] = None
    followUpComments: List[str] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True  # Allow both alias and field name

class CategoryData(BaseModel):
    categoryId: int = Field(alias="CategoryId")
    categoryName: str = Field(alias="CategoryName")
    tasks: List[Task] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True

class NewsletterContent(BaseModel):
    content: str
    totalTasks: int

class WorkflowState(BaseModel):
    categories: List[CategoryData] = Field(default_factory=list)
    newsletter: Optional[NewsletterContent] = None
    error: Optional[str] = None
