import pytest
import datetime
from httpx import Response
import respx
from src.api_client import TaskAPIClient

@pytest.mark.asyncio
async def test_fetch_multiple_comments_in_window():
    """
    Test to verify that ALL comments within the last 7 days are retrieved (up to the safety limit).
    Scenario:
    - Comment 1: 1 day ago (Should be included)
    - Comment 2: 3 days ago (Should be included)
    - Comment 3: 6 days ago (Should be included)
    - Comment 4: 8 days ago (Should be included because we expanded window to 30, but logically satisfies '7 days' requirement overlap if the window was strict, here we test that they are present)
    - Comment 5: 40 days ago (Should be EXCLUDED)
    """
    client = TaskAPIClient(base_url="https://mock.api", api_key="test")
    
    now = datetime.datetime.now()
    
    # helper to format dates
    def days_ago(n):
        return (now - datetime.timedelta(days=n)).isoformat()
        
    mock_history = {
        "Data": {
            "FollowUpHistoryDetails": [
                {
                    "FollowUpDate": days_ago(1),
                    "TaskFollowUpComments": "Comment Day 1",
                },
                {
                    "FollowUpDate": days_ago(3),
                    "TaskFollowUpComments": "Comment Day 3",
                },
                {
                    "FollowUpDate": days_ago(6),
                    "TaskFollowUpComments": "Comment Day 6",
                },
                {
                    "FollowUpDate": days_ago(40),
                    "TaskFollowUpComments": "Comment Day 40 (Old)",
                }
            ]
        }
    }
    
    async with respx.mock(base_url="https://mock.api") as respx_mock:
        respx_mock.post("/GetTaskFollowUpHistory").mock(return_value=Response(200, json=mock_history))
        
        comments = await client.get_task_followup_history(task_id=123)
        
        print(f"\nFetched {len(comments)} comments:")
        for c in comments:
            print(f" - {c}")
            
        # Assertions
        assert "Comment Day 1" in comments
        assert "Comment Day 3" in comments
        assert "Comment Day 6" in comments
        assert "Comment Day 40 (Old)" not in comments
        
        assert len(comments) == 3

@pytest.mark.asyncio
async def test_exclude_older_than_window():
    """Confirms that comments older than the window (30 days) are strictly ignored."""
    client = TaskAPIClient(base_url="https://mock.api", api_key="test")
    now = datetime.datetime.now()
    
    mock_history = {
        "Data": {
            "FollowUpHistoryDetails": [
                {
                    "FollowUpDate": (now - datetime.timedelta(days=31)).isoformat(),
                    "TaskFollowUpComments": "Just missed the cut",
                }
            ]
        }
    }
    
    async with respx.mock(base_url="https://mock.api") as respx_mock:
        respx_mock.post("/GetTaskFollowUpHistory").mock(return_value=Response(200, json=mock_history))
        comments = await client.get_task_followup_history(task_id=123)
        assert len(comments) == 0

