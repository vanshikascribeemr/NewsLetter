"""
Unit tests to verify the email newsletter structure.
The email now shows:
- Category header with clickable task count linking to web dashboard
- Category summary with bold category name and task titles
- NO task tables in email (tables are on web dashboard only)
"""
import pytest
import re
from src.html_generator import HTMLGenerator
from src.models import CategoryData, Task


class TestEmailStructure:
    """Test suite to verify email structure without task tables."""

    @pytest.fixture
    def generator(self):
        """Create a HTMLGenerator instance."""
        return HTMLGenerator()

    @pytest.fixture
    def sample_categories(self):
        """Create sample category data for testing."""
        return [
            CategoryData(
                categoryId=1,
                categoryName="Engineering",
                categorySummary="Engineering tasks are progressing well.",
                tasks=[
                    Task(taskId=101, taskSubject="Fix Bug", taskStatus="In Progress", 
                         taskPriority="High", assigneeName="Alice"),
                    Task(taskId=102, taskSubject="Add Feature", taskStatus="Pending", 
                         taskPriority="Medium", assigneeName="Bob"),
                ]
            ),
            CategoryData(
                categoryId=2,
                categoryName="Design",
                categorySummary="Design work is on track.",
                tasks=[
                    Task(taskId=201, taskSubject="UI Redesign", taskStatus="Done", 
                         taskPriority="Low", assigneeName="Charlie"),
                ]
            ),
        ]

    def test_clickable_task_count_exists(self, generator, sample_categories):
        """
        Test that the task count is a clickable link to the web dashboard.
        """
        html = generator.generate(sample_categories)
        
        for category in sample_categories:
            # Check for clickable task count with dashboard URL
            dashboard_url = f"#cat-{category.categoryId}"
            assert dashboard_url in html, \
                f"Dashboard URL '{dashboard_url}' should exist for category '{category.categoryName}'"
            
            # Check for task count text
            task_count_text = f"{len(category.tasks)} tasks"
            assert task_count_text in html, \
                f"Task count '{task_count_text}' should exist for category '{category.categoryName}'"

    def test_no_task_tables_in_email(self, generator, sample_categories):
        """
        Test that task tables are NOT included in the email (moved to web dashboard).
        """
        html = generator.generate(sample_categories)
        
        # Should NOT have task-toggle checkboxes (removed)
        assert 'class="task-toggle"' not in html, \
            "Email should NOT contain task-toggle checkboxes"
        
        # Should NOT have task-content class (removed)
        assert 'class="task-content"' not in html, \
            "Email should NOT contain task-content class"
        
        # Should NOT have task-rows class (removed)
        assert 'class="task-rows"' not in html, \
            "Email should NOT contain task-rows class"
        
        # Should NOT have View Details button (removed)
        assert 'class="view-btn"' not in html, \
            "Email should NOT contain view-btn class"

    def test_category_summary_exists(self, generator, sample_categories):
        """
        Test that category summaries are included in the email.
        """
        html = generator.generate(sample_categories)
        
        for category in sample_categories:
            if category.categorySummary:
                # Category name should be bold in summary
                assert f"<strong>{category.categoryName}</strong>" in html, \
                    f"Category name '{category.categoryName}' should be bold in summary"

    def test_category_headers_exist(self, generator, sample_categories):
        """
        Test that category headers are present in the email.
        """
        html = generator.generate(sample_categories)
        
        for category in sample_categories:
            # Category name should exist as a header
            assert category.categoryName in html, \
                f"Category name '{category.categoryName}' should be in the email"

    def test_back_to_top_link_exists(self, generator, sample_categories):
        """
        Test that 'Back to Top' link exists for navigation.
        """
        html = generator.generate(sample_categories)
        
        assert "Back to Top" in html, "Email should contain 'Back to Top' link"
        assert "#top" in html, "Email should contain anchor link to top"


class TestEmailIntegration:
    """Integration tests for the email newsletter."""

    def test_full_newsletter_generation(self):
        """
        Integration test: Generate a full newsletter and verify structure.
        """
        generator = HTMLGenerator()
        
        categories = [
            CategoryData(
                categoryId=i,
                categoryName=f"Category {i}",
                categorySummary=f"Summary for category {i}",
                tasks=[
                    Task(taskId=i*100+j, taskSubject=f"Task {j}", 
                         taskStatus="Pending", taskPriority="Medium", 
                         assigneeName="Tester")
                    for j in range(1, 4)  # 3 tasks per category
                ]
            )
            for i in range(1, 6)  # 5 categories
        ]
        
        html = generator.generate(categories)
        
        # Verify overall HTML structure
        assert "<!DOCTYPE html>" in html, "Should be valid HTML document"
        
        # Verify all categories are present
        for i in range(1, 6):
            assert f"Category {i}" in html, f"Category {i} should be in the email"
            
        # Verify dashboard links exist for all categories
        for i in range(1, 6):
            dashboard_url = f"#cat-{i}"
            assert dashboard_url in html, f"Dashboard link for category {i} should exist"
        
        # Verify NO task tables in email
        assert 'class="task-toggle"' not in html, "Should NOT have task toggles"
        assert 'class="task-content"' not in html, "Should NOT have task content"

    def test_task_titles_bold_in_summary(self):
        """
        Test that task titles are made bold when they appear in the summary.
        """
        generator = HTMLGenerator()
        
        # Create a category where the summary mentions a task title
        category = CategoryData(
            categoryId=1,
            categoryName="TestCategory",
            categorySummary="The Fix Bug task is critical and needs attention.",
            tasks=[
                Task(taskId=101, taskSubject="Fix Bug", taskStatus="In Progress", 
                     taskPriority="High", assigneeName="Alice"),
            ]
        )
        
        html = generator.generate([category])
        
        # The task title "Fix Bug" should be bold in the summary
        assert "<strong>Fix Bug</strong>" in html, \
            "Task title 'Fix Bug' should be bold in the summary"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
