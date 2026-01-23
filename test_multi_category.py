import asyncio
import os
from dotenv import load_dotenv
from src.api_client import TaskAPIClient

load_dotenv()

async def test_multi_category():
    """
    Test multi-category fetching in TEST_MODE.
    This verifies that the new get_all_categories_with_tasks() method works correctly.
    """
    # Ensure TEST_MODE is enabled
    os.environ["TEST_MODE"] = "true"
    
    print("=" * 60)
    print("Testing Multi-Category Support")
    print("=" * 60)
    print()
    
    client = TaskAPIClient()
    
    # Test 1: Get all categories
    print("Test 1: Fetching all categories...")
    categories = await client.get_all_categories()
    print(f"[OK] Found {len(categories)} categories")
    for cat in categories:
        print(f"  - Category {cat['CategoryId']}: {cat['CategoryName']}")
    print()
    
    # Test 2: Get all categories with tasks
    print("Test 2: Fetching all categories with tasks...")
    category_data_list = await client.get_all_categories_with_tasks()
    print(f"[OK] Found {len(category_data_list)} categories with tasks")
    print()
    
    # Test 3: Display summary
    print("Test 3: Category Summary")
    print("-" * 60)
    total_tasks = 0
    for cat_data in category_data_list:
        task_count = len(cat_data.tasks)
        total_tasks += task_count
        print(f"Category: {cat_data.categoryName} (ID: {cat_data.categoryId})")
        print(f"  Tasks: {task_count}")
        if cat_data.tasks:
            print(f"  Sample Task: {cat_data.tasks[0].taskSubject}")
        print()
    
    print("-" * 60)
    print(f"Total Categories: {len(category_data_list)}")
    print(f"Total Tasks: {total_tasks}")
    print()
    
    print("[OK] All tests passed!")
    print("=" * 60)

if __name__ == '__main__':
    asyncio.run(test_multi_category())
