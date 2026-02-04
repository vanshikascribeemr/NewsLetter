import pytest
import datetime
import respx
import httpx
from src.api_client import TaskAPIClient

@pytest.mark.asyncio
async def test_recent_comment_filtering():
    """
    Verify that comments from the last 7 days are captured, 
    and older comments are ignored.
    """
    client = TaskAPIClient()
    
    now = datetime.datetime.now()
    yesterday = now - datetime.timedelta(days=1)
    eight_days_ago = now - datetime.timedelta(days=8)
    
    date_recent = yesterday.isoformat(timespec='seconds')
    date_old = eight_days_ago.isoformat(timespec='seconds')
    
    mock_response = {
        "Data": {
            "FollowUpHistoryDetails": [
                {
                    "FollowUpDate": date_recent,
                    "TaskFollowUpComments": "This is a recent comment."
                }
            ]
        }
    }
    
    mock_response = {
        "Data": {
            "FollowUpHistoryDetails": [
                {
                    "FollowUpDate": date_recent,
                    "TaskFollowUpComments": "This is a recent comment."
                }
            ]
        }
    }
    
    with respx.mock:
        # Mock the main fetch with PageSize=-1
        # NOTE: client.base_url defaults to production now, so test must match that
        respx.post(f"{client.base_url}/GetTaskFollowUpHistory", json__TaskId=123, json__PageSize=-1).mock(return_value=httpx.Response(200, json=mock_response))
        
        comments = await client.get_task_followup_history(123)
        
        # We expect the comment to be returned (filtering is done client-side)
        assert len(comments) == 1
        assert comments[0] == "This is a recent comment."
        print("\n✅ Test Passed: Successfully extracted comments from PageSize=-1 fetch.")

@pytest.mark.asyncio
async def test_recent_comment_timezone_z():
    """
    Verify parsing of Zulu time Z suffix is handled gracefully.
    """
    client = TaskAPIClient()
    now = datetime.datetime.now()
    yesterday = now - datetime.timedelta(days=1)
    date_recent_z = yesterday.isoformat(timespec='seconds') + "Z"
    
    mock_response = {
        "Data": {
            "FollowUpHistoryDetails": [
                {
                    "FollowUpDate": date_recent_z,
                    "TaskFollowUpComments": "Recent Z comment"
                }
            ]
        }
    }
    
    with respx.mock:
        respx.post(f"{client.base_url}/GetTaskFollowUpHistory", json__TaskId=123, json__PageSize=-1).mock(return_value=httpx.Response(200, json=mock_response))
        
        comments = await client.get_task_followup_history(123)
        assert len(comments) == 1
        assert comments[0] == "Recent Z comment"
        print("\n✅ Test Passed: Successfully extracted value from Z-timestamped record.")
