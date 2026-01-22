import httpx
from typing import List
import os
from .models import Task
import datetime
import structlog

logger = structlog.get_logger()

class TaskAPIClient:
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or os.getenv("API_BASE_URL", "https://hrms-test.scribeemr.in/api/HrmsWebApi")
        self.api_key = api_key or os.getenv("API_KEY")

    async def get_category_tasks(self, category_id: int) -> List[Task]:
        """
        Fetches tasks for a specific category using GET request.
        """
        # TEST MODE: Return mock data if configured
        if os.getenv("TEST_MODE") == "true":
            logger.info("TEST MODE: Returning mock tasks")
            return [
                Task(taskId=101, taskSubject="Fix Login Bug", taskStatus="In Progress", taskPriority="High", assigneeName="Alice"),
                Task(taskId=102, taskSubject="Update Docs", taskStatus="Pending", taskPriority="Medium", assigneeName="Bob"),
                Task(taskId=103, taskSubject="Cleanup DB", taskStatus="Done", taskPriority="Low", assigneeName="Charlie"),
            ]

        async with httpx.AsyncClient() as client:
            try:
                # Based on: curl --location '.../GetCategoryTasks?CategoryId=7'
                response = await client.get(
                    f"{self.base_url}/GetCategoryTasks",
                    params={"CategoryId": category_id},
                    headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                # Handle potential different response structures
                tasks_list = data if isinstance(data, list) else data.get("tasks", [])
                return [Task(**t) for t in tasks_list]
            except Exception as e:
                logger.error("Failed to fetch tasks", error=str(e), category_id=category_id)
                return []

    async def get_task_followup_history(self, task_id: int) -> List[str]:
        """
        Fetches last 7 days follow-up comments using POST request with JSON body.
        """
        # TEST MODE: Return mock comments
        if os.getenv("TEST_MODE") == "true":
            return [f"Update for task {task_id}: Work in progress", "Added unit tests"]

        async with httpx.AsyncClient() as client:
            try:
                # Based on: curl ... --data '{ "TaskId" : 131 }'
                response = await client.post(
                    f"{self.base_url}/GetTaskFollowUpHistoryLast7Days",
                    json={"TaskId": task_id},
                    headers={
                        "Content-Type": "application/json",
                        **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {})
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error("Failed to fetch comments", task_id=task_id, error=str(e))
                return []
