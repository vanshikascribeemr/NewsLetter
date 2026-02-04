from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class Task(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    taskId: int = Field(alias="TaskId")
    taskSubject: str = Field(alias="SubjectLine", default="No Subject")
    taskStatus: str = Field(alias="LastStatusCode", default="Unknown")
    taskPriority: str = Field(alias="TaskPriority", default="Normal")
    assigneeName: str = Field(alias="TaskAssignedtoName", default="Unassigned")
    taskSummary: Optional[str] = None
    summarizedComments: Optional[str] = None
    followUpComments: List[str] = Field(default_factory=list)

class CategoryData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    categoryId: int = Field(alias="CategoryId")
    categoryName: str = Field(alias="CategoryName")
    tasks: List[Task] = Field(default_factory=list)

class NewsletterContent(BaseModel):
    content: str
    totalTasks: int

class WorkflowState(BaseModel):
    categories: List[CategoryData] = Field(default_factory=list)
    newsletter: Optional[NewsletterContent] = None
    error: Optional[str] = None
