import pytest
import os
import httpx
from dotenv import load_dotenv

# Load real environment variables
load_dotenv()

@pytest.mark.asyncio
async def test_api_readiness():
    """
    Integration Test (2):
    - Endpoint reachable
    - Auth works
    """
    base_url = os.getenv("API_BASE_URL", "https://hrms-test.scribeemr.in/api/HrmsWebApi")
    api_key = os.getenv("API_KEY")
    
    if not api_key:
        pytest.skip("No API_KEY provided, skipping integration test")

    headers = {"Authorization": f"Bearer {api_key}"}
    
    async with httpx.AsyncClient() as client:
        # 1. Check GetAllCategories (simple GET)
        resp = await client.get(f"{base_url}/GetAllCategories", headers=headers, timeout=10)
        assert resp.status_code == 200, f"Failed to reach GetAllCategories: {resp.text}"
        
        data = resp.json()
        assert isinstance(data, (list, dict)), "Response is not a list or dict"
        
        # Normalize data
        categories = data if isinstance(data, list) else data.get("Data", [])
        assert len(categories) > 0, "No categories found in integration test"
        
        # 2. Check GetCategoryTasks for the first category
        first_cat = categories[0]
        cat_id = first_cat.get("CategoryId") or first_cat.get("TaskCategoryId")
        assert cat_id is not None
        
        resp_tasks = await client.get(
            f"{base_url}/GetCategoryTasks", 
            params={"CategoryId": cat_id}, 
            headers=headers, 
            timeout=10
        )
        assert resp_tasks.status_code == 200
        
        tasks_data = resp_tasks.json()
        tasks = tasks_data if isinstance(tasks_data, list) else tasks_data.get("Data", [])
        
        # Warnings if list is empty, but not necessarily a failure if the category just has no tasks
        if not tasks:
            print(f"Warning: Category {cat_id} has no tasks, but endpoint worked.")
            
        # 3. Check Task History (Comment Endpoint) if tasks exist
        if tasks:
            task_id = tasks[0].get("TaskId")
            resp_hist = await client.post(
                f"{base_url}/GetTaskFollowUpHistory",
                json={"TaskId": task_id, "Page": 1, "PageSize": 5},
                headers=headers,
                timeout=10
            )
            assert resp_hist.status_code == 200
            # Just verify structure
            hist_data = resp_hist.json()
            assert "Data" in hist_data or isinstance(hist_data, list), "Unexpected history response format"
