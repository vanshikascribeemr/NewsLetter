import asyncio
import os
import httpx
import structlog
from dotenv import load_dotenv

# Configure logging
structlog.configure()
logger = structlog.get_logger()

async def pre_cache_worker():
    """
    Worker script to wake up the web service and trigger cache enrichment.
    This should be run as a Render Cron Job (e.g., every 15-30 minutes).
    """
    load_dotenv()
    base_url = os.getenv("BASE_API_URL")
    
    if not base_url:
        logger.error("BASE_API_URL environment variable is missing")
        return

    # Normalize URL (remove trailing slash)
    base_url = base_url.rstrip('/')
    
    logger.info("Worker: Starting pre-cache cycle", target=base_url)

    async with httpx.AsyncClient() as client:
        try:
            # 1. Wake Up Call
            # Ping the root dashboard to trigger the 'lifespan' startup logic
            logger.info("Worker: Pinging root to wake service...")
            wake_resp = await client.get(f"{base_url}/dashboard", timeout=60.0)
            logger.info("Worker: Wake-up response", status=wake_resp.status_code)

            # 2. Trigger Fresh Enrichment
            # Explicitly call the refresh endpoint to ensure summaries are recalculated
            refresh_url = f"{base_url}/api/refresh-cache"
            logger.info("Worker: Triggering async cache enrichment...", url=refresh_url)
            refresh_resp = await client.get(refresh_url, timeout=30.0)
            
            if refresh_resp.status_code == 200:
                logger.info("Worker: Successfully initiated enrichment", message=refresh_resp.json())
            else:
                logger.warning("Worker: Refresh endpoint returned non-200", status=refresh_resp.status_code)

        except httpx.ConnectError:
            logger.error("Worker: Could not connect to service. Is it deployed?")
        except httpx.TimeoutException:
            logger.warning("Worker: Timeout during wake-up (this is normal if service was sleeping)")
        except Exception as e:
            logger.error("Worker: Unexpected error", error=str(e))

if __name__ == "__main__":
    asyncio.run(pre_cache_worker())
