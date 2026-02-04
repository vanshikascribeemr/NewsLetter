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
    """Verify that every task in the model is rendered in the newsletter HTML."""
    gen = HTMLGenerator()
    html = gen.generate([mock_category_data])
    
    # In newsletter, each task should have an ID starting with #TaskId
    for task in mock_category_data.tasks:
        # Check if the task ID text exists in the HTML
        assert f"#{task.taskId}" in html
        # Check if the subject exists
        assert task.taskSubject in html

def test_dashboard_captures_all_tasks(mock_category_data):
    """Verify that every task in the model is rendered in the dashboard HTML."""
    gen = DashboardGenerator()
    html = gen.generate([mock_category_data])
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find the category section
    cat_section = soup.find(id=f"cat-{mock_category_data.categoryId}")
    assert cat_section is not None
    
    # Each task is in a div with class 'task-card'
    task_cards = cat_section.find_all(class_='task-card')
    assert len(task_cards) == len(mock_category_data.tasks)
    
    # Verify IDs and subjects within the cards
    card_texts = [card.get_text() for card in task_cards]
    for task in mock_category_data.tasks:
        found = any(f"#{task.taskId}" in text and task.taskSubject in text for text in card_texts)
        assert found, f"Task {task.taskId} not found in its category cards"

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
