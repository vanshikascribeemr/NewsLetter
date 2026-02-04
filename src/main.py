import asyncio
import os
from dotenv import load_dotenv
from .graph import create_newsletter_graph
import structlog

load_dotenv()
logger = structlog.get_logger()

async def main():
    # Configuration from env or defaults
    recipient_email = os.getenv("RECIPIENT_EMAIL", "team@example.com")
    
    logger.info("Starting Weekly Newsletter Workflow - Multi-Category Mode")
    
    app = create_newsletter_graph()
    
    initial_state = {
        "categories": [],  # Will be populated by fetch_tasks_node
        "newsletter": None,
        "recipient_email": recipient_email,
        "error": None
    }
    
    final_state = await app.ainvoke(initial_state)
    
    if final_state.get("error"):
        logger.error("Workflow finished with error", error=final_state["error"])
    else:
        total_categories = len(final_state["categories"])
        total_tasks = sum(len(cat.tasks) for cat in final_state["categories"])
        logger.info("Workflow completed successfully", total_categories=total_categories, total_tasks=total_tasks)
        if final_state.get("newsletter"):
            print("\nGenerated Newsletter Preview:")
            print("="*30)
            content = final_state["newsletter"].content
            print(f"HTML Content generated ({len(content)} bytes).")
            print("="*30)

if __name__ == "__main__":
    asyncio.run(main())
