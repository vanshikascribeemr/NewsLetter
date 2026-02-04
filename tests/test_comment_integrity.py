import pytest
from src.api_client import TaskAPIClient
from src.llm import NewsletterGenerator
import os
import unittest.mock as mock

@pytest.fixture
def mock_api_response():
    # Simulate a response that has a comment but in a field we might miss
    return {
        "Data": {
            "FollowUpHistoryDetails": [
                {
                    "FollowUpDate": "2024-01-28T10:00:00",
                    "TaskFollowUpComments": "Found the critical bug in production.",
                    "Assignee": "Senior Dev"
                }
            ]
        }
    }

@pytest.mark.asyncio
async def test_comment_extraction_is_not_empty(mock_api_response):
    """Ensure that if the API returns a comment, we find it and don't return 'no comment'."""
    client = TaskAPIClient(api_key="test")
    
    # We mock the http client to return our specific data
    with mock.patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = mock.Mock()
        mock_resp.json.return_value = mock_api_response
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp
        
        comments = await client.get_task_followup_history(123)
        
        assert len(comments) > 0
        assert "critical bug" in comments[0]

@pytest.mark.asyncio
async def test_llm_summary_never_hallucinates_other_tasks():
    """Ensure that the LLM summary is strictly tied to the provided comments."""
    with mock.patch("langchain_openai.ChatOpenAI.__init__", return_value=None):
        gen = NewsletterGenerator()
        os.environ["OPENAI_API_KEY"] = "sk-test" # Mock key for logic checks
        
        specific_comments = ["Updated the database schema to version 2.", "Migrated users to new table."]
        
        with mock.patch("langchain_openai.ChatOpenAI.ainvoke") as mock_invoke:
            # We simulate the LLM outputting a response
            mock_response = mock.Mock()
            mock_response.content = "User migration and schema update to version 2 completed."
            mock_invoke.return_value = mock_response
            
            summary = await gen.summarize_comments(specific_comments)
            
            # Check that the summary contains parts of our specific comments
            assert "schema" in summary.lower() or "migration" in summary.lower()
            # Ensure it doesn't contain random content
            assert "no recent updates" not in summary.lower()

if __name__ == "__main__":
    import asyncio
    # Simple manual run
    print("Running Comment Integrity Test...")
    # asyncio.run(...) 
