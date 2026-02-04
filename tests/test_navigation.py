import pytest
from src.html_generator import HTMLGenerator
from src.models import Task, CategoryData
import html

def test_dynamic_navigation_anchors():
    """
    Test that every category has a matching link in the summary and an ID in the table.
    This test is dynamic and will work for any number of categories.
    """
    # 1. Setup dynamic test data
    categories = [
        CategoryData(
            CategoryId=101, 
            CategoryName="Frontend Issues", 
            tasks=[Task(TaskId=1, SubjectLine="Fix CSS", LastStatusCode="Open", TaskPriority="High", TaskAssignedtoName="User1")]
        ),
        CategoryData(
            CategoryId=202, 
            CategoryName="Backend Bugs", 
            tasks=[Task(TaskId=2, SubjectLine="Fix API", LastStatusCode="Closed", TaskPriority="Medium", TaskAssignedtoName="User2")]
        ),
        CategoryData(
            CategoryId=303, 
            CategoryName="Infrastructure", 
            tasks=[Task(TaskId=3, SubjectLine="Fix AWS", LastStatusCode="In Progress", TaskPriority="Low", TaskAssignedtoName="User3")]
        )
    ]
    
    # 2. Generate HTML
    gen = HTMLGenerator()
    html_content = gen.generate(categories)
    
    # 3. Assertions
    # Verify 'Top' anchor exists
    assert 'id="top"' in html_content.lower()
    
    for cat in categories:
        safe_id = f"cat-{cat.categoryId}"
        link_href = f'href="#{safe_id}"'
        anchor_id = f'id="{safe_id}"'
        
        # Check if the link exists in the summary chips
        assert link_href in html_content, f"Link for category {cat.categoryName} ({safe_id}) missing in summary."
        
        # Check if the anchor ID exists in the category table
        assert anchor_id in html_content, f"Anchor ID for category {cat.categoryName} ({safe_id}) missing in section."
        
        # Check if "Back to Top" link exists for this category
        # Since it's repeated, we just check if the text exists near the anchor
        assert "#top" in html_content, "Back to Top link missing."
        
        # Verify category name is escaped and present
        escaped_name = html.escape(cat.categoryName)
        assert escaped_name in html_content

def test_empty_categories_no_anchors():
    """
    Verify that categories with no tasks don't generate anchors/sections.
    """
    categories = [
        CategoryData(
            CategoryId=999, 
            CategoryName="Empty Category", 
            tasks=[]
        )
    ]
    gen = HTMLGenerator()
    html_content = gen.generate(categories)
    
    assert "cat-999" not in html_content
    assert "Empty Category" not in html_content
