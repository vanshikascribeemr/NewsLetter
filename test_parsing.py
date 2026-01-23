import asyncio
import httpx
import os
from dotenv import load_dotenv
import json

load_dotenv()

async def test_parsing():
    client = httpx.AsyncClient()
    base_url = os.getenv('API_BASE_URL', 'https://hrms-test.scribeemr.in/api/HrmsWebApi')
    url = f"{base_url}/GetCategoryTasks"
    api_key = os.getenv('API_KEY')
    
    headers = {'Authorization': f'Bearer {api_key}'} if api_key else {}
    
    try:
        resp = await client.get(
            url,
            params={'CategoryId': 7},
            headers=headers,
            timeout=30.0
        )
        resp.raise_for_status()
        data = resp.json()
        
        print(f'Response type: {type(data)}')
        print(f'Response keys: {data.keys() if isinstance(data, dict) else "N/A"}')
        print()
        
        # Check current parsing logic
        tasks_list = data if isinstance(data, list) else data.get("tasks", [])
        print(f'Current parsing result: {len(tasks_list)} tasks')
        print()
        
        # Check if Data key exists
        if isinstance(data, dict) and 'Data' in data:
            print(f'Found "Data" key with {len(data["Data"])} items')
            print(f'First task sample: {json.dumps(data["Data"][0], indent=2)[:500]}')
        
    except Exception as e:
        print(f'Error: {type(e).__name__}: {e}')
    finally:
        await client.aclose()

if __name__ == '__main__':
    asyncio.run(test_parsing())
