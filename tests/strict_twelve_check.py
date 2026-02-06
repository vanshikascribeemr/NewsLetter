import pytest
from src.html_generator import HTMLGenerator
from src.models import Task, CategoryData

def test_strictly_all_categories_present():
    """STRICT CHECK: Verify that all categories (even empty ones) are present in the email body."""
    # Create 12 categories: 6 with tasks, 6 without
    categories = []
    for i in range(1, 13):
        tasks = []
        if i <= 6:
            tasks = [Task(TaskId=i, SubjectLine=f"Task {i}", LastStatusCode="Open", TaskPriority="Normal", AssigneeName="User")]
        
        cat = CategoryData(
            CategoryId=i,
            CategoryName=f"Category {i}",
            categorySummary=f"Summary {i}" if i <= 6 else "No active work items recorded in this workstream for the current period.",
            tasks=tasks
        )
        categories.append(cat)
    
    gen = HTMLGenerator()
    html_output = gen.generate(categories)
    
    # Check that every single category name is in the output
    for i in range(1, 13):
        assert f"Category {i}" in html_output, f"Category {i} missing from email"
        if i > 6:
            assert "0 Tasks" in html_output
            assert "No active work items recorded" in html_output

    print("STRICT CHECK PASSED: All 12 categories are present in the email body.")

if __name__ == "__main__":
    test_strictly_all_categories_present()
