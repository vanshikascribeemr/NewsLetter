import httpx
from typing import List
import os
from .models import Task, CategoryData
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
                # API returns {"Status": true, "Data": [...]} format
                if isinstance(data, list):
                    tasks_list = data
                elif isinstance(data, dict):
                    tasks_list = data.get("Data", data.get("tasks", []))
                else:
                    tasks_list = []
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
                response.raise_for_status()
                data = response.json()
                
                # Extract inner list from Data.FollowUpHistoryDetails
                history = []
                if isinstance(data, dict):
                    inner_data = data.get("Data", {})
                    # Handle case where Data might be the list itself or inside
                    if isinstance(inner_data, dict):
                        history = inner_data.get("FollowUpHistoryDetails", [])
                    elif isinstance(inner_data, list):
                        history = inner_data
                    # Fallback to direct list if valid
                    elif isinstance(data, list):
                        history = data
                elif isinstance(data, list):
                    history = data
                    
                # Extract string comment from history items
                comments = []
                for item in history:
                    if isinstance(item, str):
                        comments.append(item)
                    elif isinstance(item, dict):
                        # Try common field names
                        text = item.get("FollowUpComment") or item.get("Comment") or item.get("Description") or item.get("Note")
                        if text:
                            comments.append(str(text))
                        else:
                            # Fallback: join all values
                            comments.append(" | ".join(str(v) for v in item.values() if v))
                return comments
            except Exception as e:
                logger.error("Failed to fetch comments", task_id=task_id, error=str(e))
                return []

    async def get_all_categories(self) -> List[dict]:
        """
        Fetches all categories from GetAllCategories endpoint.
        """
        # TEST MODE: Return mock categories
        if os.getenv("TEST_MODE") == "true":
            logger.info("TEST MODE: Returning mock categories")
            return [
                {"CategoryId": 7, "CategoryName": "ScribeRyte Issues"},
                {"CategoryId": 12, "CategoryName": "Bug Fixes"},
                {"CategoryId": 15, "CategoryName": "Feature Requests"},
            ]

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/GetAllCategories",
                    headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                # Handle potential different response structures
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("Data", data.get("categories", []))
                else:
                    return []
            except Exception as e:
                logger.error("Failed to fetch categories", error=str(e))
                return []

    async def get_all_categories_with_tasks(self) -> List[CategoryData]:
        """
        Fetches all categories and their tasks.
        Orchestrates: get_all_categories() + get_category_tasks() for each.
        """
        logger.info("Fetching all categories with tasks")
        
        # Step 1: Get all categories
        categories = await self.get_all_categories()
        
        if not categories:
            logger.warning("No categories found")
            return []
        
        # Step 2: Fetch tasks for each category
        category_data_list = []
        for category in categories:
            # API returns TaskCategoryId/TaskCategoryName (not CategoryId/CategoryName)
            category_id = category.get("TaskCategoryId") or category.get("CategoryId")
            category_name = category.get("TaskCategoryName") or category.get("CategoryName", f"Category {category_id}")
            
            logger.info("Fetching tasks for category", category_id=category_id, category_name=category_name)
            tasks = await self.get_category_tasks(category_id)
            
            # Create CategoryData object
            category_data = CategoryData(
                categoryId=category_id,
                categoryName=category_name,
                tasks=tasks
            )
            category_data_list.append(category_data)
        
        logger.info("Fetched all categories", total_categories=len(category_data_list))
        return category_data_list
