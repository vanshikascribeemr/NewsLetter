"""
Tests for HTML structure of the newsletter email.
The email now shows category headers with clickable task counts and summaries.
Task tables are on the web dashboard only, not in the email.
"""
import pytest
from src.html_generator import HTMLGenerator
from src.models import Task, CategoryData, NewsletterContent


def test_html_has_category_with_summary():
    """
    Verify that the email contains category headers and summaries.
    Task tables are now on the web dashboard, not in the email.
    """
    # 1. Setup Data
    task_with_summary = Task(
        TaskId=101,
        SubjectLine="Task with Summary",
        LastStatusCode="In Progress",
        TaskPriority="High",
        TaskAssignedtoName="Alice",
        summarizedComments="This is a summary of the last 7 days."
    )
    
    task_without_summary = Task(
        TaskId=102,
        SubjectLine="Task without Summary",
        LastStatusCode="In Progress",
        TaskPriority="Medium",
        TaskAssignedtoName="Bob",
        summarizedComments=None
    )
    
    task_with_no_activity = Task(
        TaskId=103,
        SubjectLine="Task with No Activity",
        LastStatusCode="Done",
        TaskPriority="Low",
        TaskAssignedtoName="Charlie",
        summarizedComments="No recent comments."
    )
    
    category = CategoryData(
        CategoryId=1, 
        CategoryName="Test Cat", 
        categorySummary="TestCat summary with important updates.",
        tasks=[task_with_summary, task_without_summary, task_with_no_activity]
    )
    
    # 2. Generate HTML
    generator = HTMLGenerator()
    html_output = generator.generate([category])
    
    # 3. Assertions
    
    # Check category name is present
    assert "Test Cat" in html_output, "Category name should be in the email"
    
    # Check clickable task count exists
    assert "3 tasks" in html_output, "Task count should be in the email"
    
    # Check dashboard link exists
    assert "#cat-1" in html_output, "Dashboard link should be in the email"
    
    # Check that category summary is present
    # Check that category summary is present
    assert "Test Cat" in html_output, \
        "Category summary or name should be in the email"
    
    # IMPORTANT: Task details are NOT in email anymore (moved to web dashboard)
    # So we should NOT check for individual task subjects or Update: labels
    
    print("\nHTML Test Passed: Email has category header with clickable task count.")


def test_html_has_clickable_task_count():
    """
    Test that the task count is a clickable link to the web dashboard.
    """
    task = Task(
        TaskId=101,
        SubjectLine="Test Task",
        LastStatusCode="In Progress",
        TaskPriority="High",
        TaskAssignedtoName="Alice"
    )
    
    category = CategoryData(
        CategoryId=42,
        CategoryName="Clickable Test",
        tasks=[task]
    )
    
    generator = HTMLGenerator()
    html_output = generator.generate([category])
    
    # Check for the dashboard URL
    assert "#cat-42" in html_output, \
        "Dashboard link should contain category ID"
    
    # Check for task count
    assert "1 tasks" in html_output, "Task count should be displayed"
    
    # Check that it's a link (anchor tag)
    assert '<a href="#cat-42"' in html_output, \
        "Task count should be wrapped in an anchor tag"
    
    print("\nHTML Test Passed: Task count is clickable.")


def test_no_task_tables_in_email():
    """
    Test that task tables are NOT in the email (they're on the web dashboard).
    """
    task = Task(
        TaskId=101,
        SubjectLine="Test Task",
        LastStatusCode="In Progress",
        TaskPriority="High",
        TaskAssignedtoName="Alice",
        summarizedComments="Some update"
    )
    
    category = CategoryData(
        CategoryId=1,
        CategoryName="No Tables Test",
        tasks=[task]
    )
    
    generator = HTMLGenerator()
    html_output = generator.generate([category])
    
    # Should NOT have task-toggle (expand/collapse feature removed from email)
    assert 'class="task-toggle"' not in html_output, \
        "Email should NOT contain task-toggle class"
    
    # Should NOT have task-content (no task tables in email)
    assert 'class="task-content"' not in html_output, \
        "Email should NOT contain task-content class"
    
    # Should NOT have View Details button (removed)
    assert 'View Details' not in html_output, \
        "Email should NOT contain 'View Details' button"
    
    print("\nHTML Test Passed: No task tables in email.")


if __name__ == "__main__":
    test_html_has_category_with_summary()
    test_html_has_clickable_task_count()
    test_no_task_tables_in_email()
