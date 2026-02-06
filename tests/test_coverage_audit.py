import pytest
import respx
from httpx import Response
from src.api_client import TaskAPIClient
from src.llm import NewsletterGenerator
from src.models import Task, CategoryData
from src.graph import sync_categories_node, fetch_tasks_node
import unittest.mock as mock

# --- API CLIENT COVERAGE ---

@pytest.mark.asyncio
async def test_get_all_categories_normalization():
    """Verify that categories are normalized regardless of key casing/naming."""
    client = TaskAPIClient(base_url="https://mock.api")
    mock_resp = {
        "Data": [
            {"CategoryId": 1, "CategoryName": "Cat 1"},
            {"TaskCategoryId": 2, "TaskCategoryName": "Cat 2"}
        ]
    }
    
    async with respx.mock(base_url="https://mock.api") as respx_mock:
        respx_mock.get("/GetAllCategories").mock(return_value=Response(200, json=mock_resp))
        cats = await client.get_all_categories()
        assert len(cats) == 2
        # Verify normalization (keys are kept raw but content exists)
        assert cats[0]["CategoryId"] == 1
        assert cats[1]["TaskCategoryId"] == 2

# --- LLM COVERAGE ---

@pytest.mark.asyncio
async def test_newsletter_generator_json_parsing():
    """Ensure generate() correctly handles LLM markdown blocks and parsing."""
    with mock.patch("langchain_openai.ChatOpenAI.__init__", return_value=None):
        gen = NewsletterGenerator()
        
        # Simulate LLM returning JSON inside a markdown block
        mock_resp = mock.Mock()
        mock_resp.content = '```json\n{"content": "LLM Result", "totalTasks": 1}\n```'
        
        with mock.patch("langchain_openai.ChatOpenAI.ainvoke", return_value=mock_resp):
            with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
                result = await gen.generate("Test Cat", [Task(taskId=1, taskSubject="S", taskStatus="O", taskPriority="H", assigneeName="N")])
                assert result.content == "LLM Result"
                assert result.totalTasks == 1

# --- GRAPH NODE COVERAGE ---

@pytest.mark.asyncio
async def test_sync_categories_node_calls_db():
    """Verify the graph node correctly bridges the client and database."""
    state = {"categories": [], "recipient_email": "test@test.com", "error": None}
    
    with mock.patch("src.api_client.TaskAPIClient.get_all_categories") as mock_get:
        mock_get.return_value = [{"CategoryId": 10, "CategoryName": "Test"}]
        
        with mock.patch("src.graph.sync_categories") as mock_sync:
            with mock.patch("src.graph.SessionLocal") as mock_session:
                await sync_categories_node(state)
                assert mock_get.called
                assert mock_sync.called

@pytest.mark.asyncio
async def test_fetch_tasks_node_error_handling():
    """Test fetch_tasks_node edge cases (empty results)."""
    state = {"categories": [], "recipient_email": "test@test.com", "error": None}
    
    with mock.patch("src.api_client.TaskAPIClient.get_all_categories_with_tasks") as mock_get:
        mock_get.return_value = [] # No tasks found
        
        result = await fetch_tasks_node(state)
        assert result["error"] == "No categories found"
        assert result["categories"] == []

# --- MODEL VALIDATION ---

def test_task_model_edge_cases():
    """Ensure Pydantic models handle missing or null fields gracefully."""
    # Test with minimal data
    t = Task(taskId=1, taskSubject="Sub", taskStatus="S", taskPriority="P", assigneeName="A")
    assert t.summarizedComments is None # Pydantic default
    
    # Test with None for fields that might be null from API
    t_null = Task(taskId=2, taskSubject="Sub", taskStatus="S", taskPriority="P", assigneeName="A", summarizedComments=None)
    assert t_null.summarizedComments is None
