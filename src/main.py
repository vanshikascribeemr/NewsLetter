import asyncio
import os
from dotenv import load_dotenv
from .graph import create_newsletter_graph
import structlog

load_dotenv()
logger = structlog.get_logger()

async def main():
    # Configuration from env or defaults
    category_id = int(os.getenv("CATEGORY_ID", "7"))
    category_name = os.getenv("CATEGORY_NAME", "ScribeRyte Issues")
    recipient_email = os.getenv("RECIPIENT_EMAIL", "team@example.com")
    
    logger.info("Starting Weekly Newsletter Workflow", category_id=category_id)
    
    app = create_newsletter_graph()
    
    initial_state = {
        "category_id": category_id,
        "category_name": category_name,
        "tasks": [],
        "newsletter": None,
        "recipient_email": recipient_email,
        "error": None
    }
    
    final_state = await app.ainvoke(initial_state)
    
    if final_state.get("error"):
        logger.error("Workflow finished with error", error=final_state["error"])
    else:
        logger.info("Workflow completed successfully", total_tasks=len(final_state["tasks"]))
        if final_state.get("newsletter"):
            print("\nGenerated Newsletter Preview:")
            print("="*30)
            print(final_state["newsletter"].content)
            print("="*30)

if __name__ == "__main__":
    asyncio.run(main())
