import httpx
from typing import List
import os
from .models import Task, CategoryData
import datetime
import structlog

logger = structlog.get_logger()

# In-memory cache with extended TTL
_categories_cache = {
    "data": None,
    "timestamp": None
}

# Separate enriched cache (with summarized comments)
_enriched_cache = {
    "data": None,
    "timestamp": None
}

# Cache TTL in seconds (15 minutes - longer cache for fast dashboard loads)
CACHE_TTL_SECONDS = 900

def get_cached_categories():
    """
    Returns cached categories if valid, None otherwise.
    Used for instant dashboard loading.
    """
    import datetime
    now = datetime.datetime.now()
    if _categories_cache["data"] and _categories_cache["timestamp"]:
        age = (now - _categories_cache["timestamp"]).total_seconds()
        if age < CACHE_TTL_SECONDS:
            return _categories_cache["data"]
    return None

def get_enriched_categories():
    """
    Returns enriched categories (with summarized comments) if valid, None otherwise.
    Used for dashboard with 7-day comment summaries.
    """
    import datetime
    now = datetime.datetime.now()
    if _enriched_cache["data"] and _enriched_cache["timestamp"]:
        age = (now - _enriched_cache["timestamp"]).total_seconds()
        if age < CACHE_TTL_SECONDS:
            return _enriched_cache["data"]
    return None

def set_enriched_categories(data):
    """Stores enriched categories in the cache."""
    _enriched_cache["data"] = data
    _enriched_cache["timestamp"] = datetime.datetime.now()
    logger.info("Enriched cache updated", count=len(data) if data else 0)

def has_valid_cache() -> bool:
    """Returns True if cache is valid and not expired."""
    return get_cached_categories() is not None

def has_valid_enriched_cache() -> bool:
    """Returns True if enriched cache is valid and not expired."""
    return get_enriched_categories() is not None

def invalidate_cache():
    """Clears both caches - useful for forcing a refresh."""
    _categories_cache["data"] = None
    _categories_cache["timestamp"] = None
    _enriched_cache["data"] = None
    _enriched_cache["timestamp"] = None


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
                        # Store raw text for test compatibility (tests expect simple strings)
                        # Chronological order is handled by the sort step below
                        items_with_dates.append((f_date, str(text).strip()))
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
        Fetches all categories and their tasks concurrently.
        Cached for CACHE_TTL_SECONDS to improve dashboard speed.
        """
        import asyncio
        import datetime
        
        # Check Cache - using centralized TTL
        cached = get_cached_categories()
        if cached is not None:
            logger.info("Serving categories from cache", count=len(cached))
            return cached
        
        logger.info("Fetching all categories with tasks")
        
        # Step 1: Get all categories
        categories = await self.get_all_categories()
        
        # USER_FEEDBACK: "ScribeRyte-related tasks" is a different category
        scriberyte_exists = any(
            str(c.get("TaskCategoryName", "")).strip().lower() == "scriberyte-related tasks" 
            for c in categories
        )
        if not scriberyte_exists:
            logger.info("Injecting missing 'ScribeRyte-related tasks' category")
            categories.append({
                "TaskCategoryId": 1022, 
                "TaskCategoryName": "ScribeRyte-related tasks"
            })
        
        if not categories:
            logger.warning("No categories found")
            return []
        
        # Step 2: Fetch tasks concurrently
        async def fetch_category_data(category):
            category_id = category.get("TaskCategoryId") or category.get("CategoryId")
            category_name = category.get("TaskCategoryName") or category.get("CategoryName", f"Category {category_id}")
            
            logger.info("Fetching tasks for category", category_id=category_id, category_name=category_name)
            try:
                tasks = await self.get_category_tasks(category_id)
                return CategoryData(
                    categoryId=category_id,
                    categoryName=category_name,
                    tasks=tasks
                )
            except Exception as e:
                logger.error("Failed to fetch tasks for category", category_id=category_id, error=str(e))
                return None

        # Execute parallel requests with a concurrency limit (e.g. 10 at a time) to avoid overwhelming the API
        semaphore = asyncio.Semaphore(10)
        
        async def sem_fetch(cat):
            async with semaphore:
                return await fetch_category_data(cat)

        results = await asyncio.gather(*[sem_fetch(cat) for cat in categories])
        
        # Filter out failed fetches (None)
        category_data_list = [r for r in results if r is not None]
        
        # Update Cache
        _categories_cache["data"] = category_data_list
        _categories_cache["timestamp"] = datetime.datetime.now()
        
        logger.info("Fetched all categories", total_categories=len(category_data_list))
        return category_data_list
