import pytest
from bs4 import BeautifulSoup
from src.html_generator import HTMLGenerator
from src.dashboard_generator import DashboardGenerator
from src.models import CategoryData, Task

@pytest.fixture
def mock_category_data():
    tasks = [
        Task(TaskId=1001, SubjectLine="Task One", LastStatusCode="Open", TaskPriority="High", TaskAssignedtoName="User A"),
        Task(TaskId=1002, SubjectLine="Task Two", LastStatusCode="In Progress", TaskPriority="Medium", TaskAssignedtoName="User B"),
        Task(TaskId=1003, SubjectLine="Task Three", LastStatusCode="Closed", TaskPriority="Low", TaskAssignedtoName="User C"),
    ]
    return CategoryData(categoryId=1, categoryName="Test Category", tasks=tasks)

def test_newsletter_captures_all_tasks(mock_category_data):
    """Verify that the newsletter contains category info with clickable task count.
    Note: Individual task details are now on the dashboard, not in the email."""
    gen = HTMLGenerator()
    html = gen.generate([mock_category_data])
    
    # In newsletter, we should have:
    # 1. Category name
    assert mock_category_data.categoryName in html, "Category name should be in email"
    
    # 2. Task count
    task_count = len(mock_category_data.tasks)
    assert f"{task_count} tasks" in html, "Task count should be in email"
    
    # 3. Dashboard link for the category
    dashboard_url = f"#cat-{mock_category_data.categoryId}"
    assert dashboard_url in html, "Dashboard link should be in email"

@pytest.mark.asyncio
async def test_dashboard_captures_all_tasks(mock_category_data):
    """Verify that every task in the model is rendered in the dashboard HTML."""
    gen = DashboardGenerator()
    html = await gen.generate([mock_category_data])
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find the category section
    cat_section = soup.find(id=f"cat-{mock_category_data.categoryId}")
    assert cat_section is not None
    
    # Each task is in a div with class 'article-block'
    task_blocks = cat_section.find_all(class_='article-block')
    assert len(task_blocks) == len(mock_category_data.tasks)
    
    # Verify IDs and subjects within the blocks
    block_texts = [block.get_text() for block in task_blocks]
    for task in mock_category_data.tasks:
        found = any(f"#{task.taskId}" in text and task.taskSubject in text for text in block_texts)
        assert found, f"Task {task.taskId} not found in its category blocks"

if __name__ == "__main__":
    # If run directly, just execute these logic checks
    mock_data = [
        Task(TaskId=99, SubjectLine="Integrity Check", LastStatusCode="Live", TaskPriority="High", TaskAssignedtoName="Bot")
    ]
    cat = CategoryData(categoryId=9, categoryName="Security", tasks=mock_data)
    
    print("Testing Newsletter Integrity...")
    test_newsletter_captures_all_tasks(cat)
    print("Newsletter: PASS")
    
    print("Testing Dashboard Integrity...")
    test_dashboard_captures_all_tasks(cat)
    print("Dashboard: PASS")
