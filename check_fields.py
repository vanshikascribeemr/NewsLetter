import asyncio
import httpx
import os
from dotenv import load_dotenv
import json

load_dotenv()

async def check_fields():
    client = httpx.AsyncClient()
    base_url = os.getenv('API_BASE_URL', 'https://hrms-test.scribeemr.in/api/HrmsWebApi')
    url = f"{base_url}/GetCategoryTasks"
    api_key = os.getenv('API_KEY')
    
    headers = {'Authorization': f'Bearer {api_key}'} if api_key else {}
    
    try:
        resp = await client.get(url, params={'CategoryId': 7}, headers=headers, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        
        if isinstance(data, dict) and 'Data' in data and len(data['Data']) > 0:
            first_task = data['Data'][0]
            print('Field names in API response:')
            for key in first_task.keys():
                print(f'  - {key}')
            print()
            print('Sample task data:')
            print(json.dumps(first_task, indent=2)[:1500])
        
    except Exception as e:
        print(f'Error: {e}')
    finally:
        await client.aclose()

if __name__ == '__main__':
    asyncio.run(check_fields())
