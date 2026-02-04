import pytest
from src.html_generator import HTMLGenerator
from src.models import Task, CategoryData, NewsletterContent

def test_html_row_has_update_section():
    """
    Verify that EVERY task row is followed by an update row (summary row).
    The design requires a table row for the task, followed immediately by a row for the update.
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
        tasks=[task_with_summary, task_without_summary, task_with_no_activity]
    )
    
    # 2. Generate HTML
    generator = HTMLGenerator()
    html_output = generator.generate([category])
    
    # 3. Assertions
    
    # Check all tasks are present
    assert "Task with Summary" in html_output
    assert "Task without Summary" in html_output
    assert "Task with No Activity" in html_output
    
    # Check that the real summary is present
    assert "This is a summary of the last 7 days" in html_output
    
    # Check that fallback text is present for tasks without summaries
    assert "No recent activity reported" in html_output
    
    # CRITICAL: Count Update labels - should equal number of tasks (3)
    update_label_count = html_output.count("Update:")
    assert update_label_count == 3, f"Expected 3 'Update:' labels but found {update_label_count}"
    
    print("\nHTML Test Passed: Every task has an Update row.")

if __name__ == "__main__":
    test_html_row_has_update_section()
