import pytest
import pytest_asyncio
import datetime
import json
import respx
from httpx import Response
from src.api_client import TaskAPIClient
from src.models import Task, CategoryData

# --- FIXTURES ---

@pytest.fixture
def mock_api_client():
    return TaskAPIClient(base_url="https://mock.api", api_key="mock_key")

@pytest.fixture
def sample_task_response():
    return {
        "Status": True,
        "Data": [
            {
                "TaskId": 101,
                "SubjectLine": "Fix Login Bug",
                "LastStatusCode": "In Progress",
                "TaskPriority": "High",
                "TaskAssignedtoName": "Alice"
            },
            {
                "TaskId": 102,
                "SubjectLine": "Update Docs",
                "LastStatusCode": "Pending",
                "TaskPriority": "Medium",
                "TaskAssignedtoName": "Bob"
            }
        ]
    }

@pytest.fixture
def sample_history_response():
    # Make dates relative to NOW to pass the 30-day filter
    now = datetime.datetime.now()
    
    recent_date = (now - datetime.timedelta(days=2)).isoformat()
    old_date = (now - datetime.timedelta(days=40)).isoformat()
    
    return {
        "Data": {
            "FollowUpHistoryDetails": [
                {
                    "FollowUpDate": recent_date, 
                    "TaskFollowUpComments": "Recent update",
                    "FollowUpComment": "Recent update" # fallback
                },
                {
                    "FollowUpDate": old_date, 
                    "TaskFollowUpComments": "Old update",
                    "FollowUpComment": "Old update"
                }
            ]
        }
    }

# --- UNIT TESTS ---

@pytest.mark.asyncio
async def test_fetch_category_tasks(mock_api_client, sample_task_response):
    """
    Test Tasks Fetching Logic (A):
    - Endpoint called correct params
    - Response parsed correctly
    - Fields extracted
    """
    async with respx.mock(base_url="https://mock.api") as respx_mock:
        route = respx_mock.get("/GetCategoryTasks").mock(return_value=Response(200, json=sample_task_response))
        
        tasks = await mock_api_client.get_category_tasks(category_id=7)
        
        # Verify Request
        assert route.called
        assert route.calls.last.request.url.params["CategoryId"] == "7"
        assert route.calls.last.request.headers["Authorization"] == "Bearer mock_key"
        
        # Verify Response Parsing
        assert len(tasks) == 2
        assert tasks[0].taskId == 101
        assert tasks[0].taskSubject == "Fix Login Bug"
        assert tasks[0].assigneeName == "Alice"
        assert tasks[0].taskPriority == "High"
        assert tasks[0].taskStatus == "In Progress"

@pytest.mark.asyncio
async def test_comment_filtering(mock_api_client, sample_history_response):
    """
    Test Comments Filtering Logic (B):
    - Filter comments (current logic is 30 days)
    - Old comments excluded
    - Recent comments included
    """
    async with respx.mock(base_url="https://mock.api") as respx_mock:
        respx_mock.post("/GetTaskFollowUpHistory").mock(return_value=Response(200, json=sample_history_response))
        
        comments = await mock_api_client.get_task_followup_history(task_id=101)
        
        # Should only contain the recent comment
        assert len(comments) == 1
        assert comments[0] == "Recent update"

@pytest.mark.asyncio
async def test_comment_filtering_empty(mock_api_client):
    """Test no comments returns empty list"""
    empty_history = {"Data": {"FollowUpHistoryDetails": []}}
    
    async with respx.mock(base_url="https://mock.api") as respx_mock:
        respx_mock.post("/GetTaskFollowUpHistory").mock(return_value=Response(200, json=empty_history))
        
        comments = await mock_api_client.get_task_followup_history(task_id=101)
        assert comments == []

@pytest.mark.asyncio
async def test_category_grouping():
    """
    Test Category Grouping (C & D):
    Verifying CategoryData model structure (simulating 'graph.py' logic usually, but here testing the model/client output)
    """
    tasks = [
        Task(taskId=1, taskSubject="A", taskStatus="Open", taskPriority="High", assigneeName="User"),
        Task(taskId=2, taskSubject="B", taskStatus="Open", taskPriority="High", assigneeName="User")
    ]
    
    cat_data = CategoryData(
        categoryId=10,
        categoryName="Bug Fixes",
        tasks=tasks
    )
    
    assert cat_data.categoryId == 10
    assert cat_data.categoryName == "Bug Fixes"
    assert len(cat_data.tasks) == 2
    assert cat_data.tasks[0].taskId == 1
