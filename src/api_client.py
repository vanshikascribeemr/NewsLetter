import httpx
from typing import List
import os
from .models import Task, CategoryData
import datetime
import structlog

logger = structlog.get_logger()

class TaskAPIClient:
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or os.getenv("API_BASE_URL", "https://hrms.scribeemr.com/api/HrmsWebApi")
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
                tasks_list = []
                # Attempt standard fetch
                try:
                    response = await client.get(
                        f"{self.base_url}/GetCategoryTasks",
                        params={"CategoryId": category_id},
                        headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
                        timeout=300.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list):
                            tasks_list = data
                        elif isinstance(data, dict):
                            tasks_list = data.get("Data") or data.get("tasks") or data.get("tasksList") or []
                            if not isinstance(tasks_list, list): tasks_list = []
                except Exception as e:
                    logger.warning("GetCategoryTasks failed", error=str(e), category_id=category_id)

                # Fallback: If empty and looks like a department ID
                if not tasks_list and category_id > 1000:
                     try:
                        resp_dept = await client.get(
                            f"{self.base_url}/GetDepartmentTasks",
                            params={"DepartmentId": category_id},
                             headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
                             timeout=60.0
                        )
                        if resp_dept.status_code == 200:
                             d_data = resp_dept.json()
                             dept_tasks = []
                             if isinstance(d_data, list): dept_tasks = d_data
                             elif isinstance(d_data, dict): dept_tasks = d_data.get("Data", [])
                             
                             if dept_tasks:
                                 logger.info("Fallback: Fetched tasks as Department", category_id=category_id, count=len(dept_tasks))
                                 tasks_list = dept_tasks
                     except Exception as ex: 
                         logger.warning("Dept fallback failed", error=str(ex), category_id=category_id)

                return [Task(**t) for t in tasks_list]
            except Exception as e:
                logger.error("Critical error in get_category_tasks", error=str(e), category_id=category_id)
                return []

    async def get_task_followup_history(self, task_id: int) -> List[str]:
        """
        Fetches last activity comments from the last 7 days.
        Returns them in CHRONOLOGICAL order (oldest first) to structure the summary as a timeline.
        """
        if os.getenv("TEST_MODE") == "true":
            # Mock timeline: Action A -> Action B -> Action C
            return [
                f"[2026-01-22 09:00]: Task {task_id} was initiated.",
                f"[2026-01-24 14:00]: Development in progress, unit tests added.",
                f"[2026-01-26 11:00]: Finalizing documentation and preparing for review."
            ]

        async with httpx.AsyncClient() as client:
            history = []
            try:
                # Primary method: Fetch all history (PageSize=-1)
                response = await client.post(
                    f"{self.base_url}/GetTaskFollowUpHistory",
                    json={"TaskId": task_id, "PageSize": -1},
                    headers={"Content-Type": "application/json", **self._get_auth_header()},
                    timeout=60.0
                )
                response.raise_for_status()
                history = self._extract_history(response.json())
            except Exception as e:
                logger.warning("Large fetch failed, trying small page fallback", task_id=task_id, error=str(e))
                try:
                    response = await client.post(
                        f"{self.base_url}/GetTaskFollowUpHistory",
                        json={"TaskId": task_id, "PageSize": 20},
                        headers={"Content-Type": "application/json", **self._get_auth_header()},
                        timeout=30.0
                    )
                    history = self._extract_history(response.json())
                except Exception as ex2:
                    logger.error("History fallback fetch also failed", task_id=task_id, error=str(ex2))
                    return []

            return self._filter_and_sort_comments(history)

    def _get_auth_header(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def _filter_and_sort_comments(self, history: List[dict]) -> List[str]:
        """
        Filters history for the last 7 days, sorts chronologically, and adds date prefixes.
        """
        items_with_dates = []
        now = datetime.datetime.now()
        threshold = now - datetime.timedelta(days=7)

        for item in history:
            f_date_str = item.get("FollowUpDate")
            if not f_date_str: continue

            try:
                # Normalize date string for isoformat
                date_str = f_date_str.replace("Z", "")
                if "." in date_str:
                    main, frac = date_str.split(".", 1)
                    date_str = f"{main}.{frac[:6]}"
                
                f_date = datetime.datetime.fromisoformat(date_str)
                
                if f_date >= threshold:
                    text = item.get("TaskFollowUpComments") or item.get("FollowUpComment") or \
                           item.get("Comment") or item.get("Description") or item.get("Note")
                    
                    if text and str(text).strip():
                        # We store f_date for sorting, and formatted string for the LLM
                        formatted = f"[{f_date.strftime('%Y-%m-%d %H:%M')}]: {str(text).strip()}"
                        items_with_dates.append((f_date, formatted))
            except Exception:
                continue

        # Sort by date: Oldest -> Newest (Timeline structure)
        items_with_dates.sort(key=lambda x: x[0])
        return [txt for date, txt in items_with_dates]

    def _extract_history(self, data) -> List[dict]:
        history = []
        if isinstance(data, dict):
            inner_data = data.get("Data", {})
            if isinstance(inner_data, dict):
                history = inner_data.get("FollowUpHistoryDetails", [])
            elif isinstance(inner_data, list):
                history = inner_data
            else:
                history = data.get("FollowUpHistoryDetails", [])
        return history if isinstance(history, list) else []


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
                    timeout=300.0
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
        
        # USER_FEEDBACK: "ScribeRyte-related tasks" is a different category
        # It seems the API might not be returning it in GetAllCategories, or it's a Department-based view
        # We manually inject it to ensure it's checked. We use a distinct ID range or the discovered Dept ID (1022)
        scriberyte_exists = any(
            str(c.get("TaskCategoryName", "")).strip().lower() == "scriberyte-related tasks" 
            for c in categories
        )
        if not scriberyte_exists:
            logger.info("Injecting missing 'ScribeRyte-related tasks' category")
            categories.append({
                "TaskCategoryId": 1022, # Using Dept ID as likely mapped Category ID
                "TaskCategoryName": "ScribeRyte-related tasks"
            })
        
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
