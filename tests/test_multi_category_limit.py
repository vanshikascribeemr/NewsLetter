import pytest
from src.html_generator import HTMLGenerator
from src.models import Task, CategoryData

def test_twelve_categories_in_email():
    """Verify that if a user is subscribed to 12 categories, all appear in the email."""
    # Create 12 categories, each with one task
    categories = []
    for i in range(1, 13):
        task = Task(
            TaskId=i,
            SubjectLine=f"Task {i}",
            LastStatusCode="Open",
            TaskPriority="Normal",
            TaskAssignedtoName=f"Assignee {i}"
        )
        cat = CategoryData(
            CategoryId=i,
            CategoryName=f"Category {i}",
            categorySummary=f"Summary for Category {i}",
            tasks=[task]
        )
        categories.append(cat)
    
    gen = HTMLGenerator()
    html_output = gen.generate(categories)
    
    # Check that every category name is in the output
    for i in range(1, 13):
        assert f"Category {i}" in html_output, f"Category {i} missing from email"
        assert f"Summary for Category {i}" in html_output, f"Summary for Category {i} missing from email"
        assert f"href=\"#cat-{i}\"" in html_output, f"Nav link for Category {i} missing"

if __name__ == "__main__":
    test_twelve_categories_in_email()
    print("Test passed: All 12 categories are present in the email body.")
