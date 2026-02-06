import pytest
import asyncio
from src.dashboard_generator import DashboardGenerator
from src.models import CategoryData, Task

@pytest.mark.asyncio
async def test_dashboard_personalization():
    """Confirms that the dashboard generator applies the correct styling to subscribed categories."""
    
    # 1. Setup Mock Data
    cat1 = CategoryData(CategoryId=1, CategoryName="Subscribed Cat", tasks=[Task(TaskId=101, SubjectLine="Task A", LastStatusCode="Open", TaskPriority="High", AssigneeName="User")])
    cat2 = CategoryData(CategoryId=2, CategoryName="Unsubscribed Cat", tasks=[Task(TaskId=102, SubjectLine="Task B", LastStatusCode="Open", TaskPriority="Low", AssigneeName="User")])
    
    cats = [cat1, cat2]
    subscribed_ids = [1] # Only Category 1 is subscribed
    
    # 2. Generate Dashboard
    gen = DashboardGenerator()
    html = await gen.generate(cats, subscribed_ids=subscribed_ids)
    
    # 3. Check for specific styling on Category 1 (Subscribed)
    # Expected: font-weight: 800; color: #5c8ca3;
    style_check_1 = 'style="font-weight: 800; color: #5c8ca3;"'
    
    # Check if this style is applied to the link for cat-1
    # We look for a substring that generally matches the link construction
    # <a href="#cat-1" class="nav-item" style="font-weight: 800; color: #5c8ca3;" onclick="...">Subscribed Cat</a>
    
    assert f'href="#cat-1" class="nav-item" {style_check_1}' in html, "Subscribed category should be bold and colored #5c8ca3"
    
    # 4. Check that Category 2 (Unsubscribed) DOES NOT have this style
    assert f'href="#cat-2" class="nav-item" {style_check_1}' not in html, "Unsubscribed category should NOT have special styling"
    
    # 5. Check Content Presence
    assert "Subscribed Cat" in html
    assert "Unsubscribed Cat" in html
    assert "Task A" in html
    assert "Task B" in html
    
    print("Dashboard Personalization Test Passed!")

if __name__ == "__main__":
    asyncio.run(test_dashboard_personalization())
