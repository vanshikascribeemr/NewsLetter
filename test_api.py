import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def test_api():
    client = httpx.AsyncClient()
    base_url = os.getenv('API_BASE_URL', 'https://hrms-test.scribeemr.in/api/HrmsWebApi')
    url = f"{base_url}/GetCategoryTasks"
    api_key = os.getenv('API_KEY')
    
    headers = {'Authorization': f'Bearer {api_key}'} if api_key else {}
    
    print(f'Testing: {url}?CategoryId=7')
    print(f'API Key present: {bool(api_key)}')
    print(f'Headers: {headers}')
    print()
    
    try:
        resp = await client.get(
            url,
            params={'CategoryId': 7},
            headers=headers,
            timeout=30.0
        )
        print(f'Status Code: {resp.status_code}')
        print(f'Response Headers: {dict(resp.headers)}')
        print(f'Response Body: {resp.text[:1000]}')
    except Exception as e:
        print(f'Error: {type(e).__name__}: {e}')
    finally:
        await client.aclose()

if __name__ == '__main__':
    asyncio.run(test_api())
