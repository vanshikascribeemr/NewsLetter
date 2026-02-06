from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from .models import Task, NewsletterContent, WorkflowState, CategoryData
from .api_client import TaskAPIClient
from .llm import NewsletterGenerator
from .email_client import EmailClient
import datetime
import structlog
import os
import asyncio
from .database import SessionLocal, User, Category, sync_categories, get_user_by_email
from .security import create_subscription_token, create_manage_token
from .relevance import rank_tasks

logger = structlog.get_logger()

class NewsletterState(TypedDict):
    categories: List[CategoryData]
    newsletter: Optional[NewsletterContent]
    recipient_email: str
    error: Optional[str]

async def sync_categories_node(state: NewsletterState):
    logger.info("Syncing categories to database")
    client = TaskAPIClient()
    categories = await client.get_all_categories()
    
    db = SessionLocal()
    try:
        sync_categories(db, categories)
    finally:
        db.close()
    return state

async def fetch_tasks_node(state: NewsletterState):
    logger.info("Fetching all categories with tasks")
    client = TaskAPIClient()
    # We fetch ALL categories with tasks once
    categories = await client.get_all_categories_with_tasks()
    
    if not categories:
        return {**state, "error": "No categories found", "categories": []}
    
    logger.info("Fetched categories", total_categories=len(categories))
    return {**state, "categories": categories}

async def enrich_tasks_node(state: NewsletterState):
    if state.get("error") or not state["categories"]:
        return state
        
    logger.info("Enriching tasks with comments for all categories")
    client = TaskAPIClient()
    llm_gen = NewsletterGenerator()
    enriched_categories = []
    
    # Priority map for sorting
    priority_map = {"High": 0, "Medium": 1, "Low": 2}
    
    for category in state["categories"]:
        # Filter out "Done" tasks immediately
        category.tasks = [t for t in category.tasks if (t.taskStatus or "").lower() != "done"]
        
        if not category.tasks:
            category.categorySummary = "No active work items recorded in this workstream for the current period."
            enriched_categories.append(category)
            continue
            
        logger.info("Enriching category", category_id=category.categoryId, category_name=category.categoryName)

        
        async def enrich_task(t):
            try:
                comments = await client.get_task_followup_history(t.taskId)
                t.followUpComments = comments
                t.summarizedComments = await llm_gen.summarize_comments(comments)
            except Exception as e:
                logger.error("Error enriching task", task_id=t.taskId, error=str(e))
                t.summarizedComments = "Update retrieval error."
            return t

        # Process tasks in parallel for this category
        enriched_tasks = await asyncio.gather(*[enrich_task(task) for task in category.tasks])
        
        # Sort tasks by priority: High -> Medium -> Low
        enriched_tasks.sort(key=lambda x: priority_map.get(x.taskPriority, 3))
        
        # Update category with enriched tasks
        category.tasks = list(enriched_tasks)
        
        # PHASE 3: Rank tasks by TF-IDF relevance
        rank_tasks(category)
        
        # PHASE 3: Generate Category-Level Synthesis
        logger.info("Generating category synthesis", category_name=category.categoryName)
        category.categorySummary = await llm_gen.generate_category_summary(category.categoryName, category.tasks)
        
        enriched_categories.append(category)
    
    return {**state, "categories": enriched_categories}

async def broadcast_newsletter_node(state: NewsletterState):
    if state.get("error") or not state["categories"]:
        return state
    
    db = SessionLocal()
    try:
        # 1. Global Filter (Host Influence) - REMOVED
        # Users should receive whatever they subscribe to, regardless of the host's preferences.
        # host_email = os.getenv("HOST_EMAIL")
        # if host_email:
        #     host = db.query(User).filter(User.email == host_email).first()
        #     if host:
        #         host_sub_ids = [c.id for c in host.subscriptions]
        #         logger.info("Applying host master filter", host=host_email, allowed_categories=len(host_sub_ids))
        #         state["categories"] = [cat for cat in state["categories"] if cat.categoryId in host_sub_ids]


        # 2. Determine recipients
        # Combine .env/state recipients with all users found in the database
        recipient_str = state.get("recipient_email", "")
        env_emails = {e.strip().lower() for e in recipient_str.split(",") if e.strip()}
        
        # Pull all users from DB
        db_users = db.query(User).all()
        db_emails = {u.email.lower().strip() for u in db_users}
        
        # Final set of unique emails to broadcast to
        emails = list(env_emails.union(db_emails))
        
        # Ensure recipients exist in DB (auto-provisioning for any new env emails)
        for email in emails:
            get_user_by_email(db, email)
        
        # Get all categories for the subscription manager
        all_db_categories = db.query(Category).all()
        
        from .html_generator import HTMLGenerator
        from .email_client import EmailClient
        html_gen = HTMLGenerator()
        email_client = EmailClient()
        base_url = os.getenv("BASE_API_URL", "http://localhost:8000")
        
        logger.info("Starting personalized broadcast", total_recipients=len(emails), db_count=len(db_emails), env_count=len(env_emails))
        
        sender_email = (os.getenv("SENDER_EMAIL") or os.getenv("SMTP_USER", "")).lower().strip()
        
        for email in emails:
            email_clean = email.lower().strip()
            # Skip personalized broadcast for the sender email
            if email_clean == sender_email:
                logger.info("Skipping personalized broadcast for sender email", email=email_clean)
                continue
                
            user = db.query(User).filter(User.email == email).first()
            if not user: continue
            
            # 3. Strictly Match Subscriptions
            # Intersection of user subs and API categories
            found_ids = set()
            user_categories = []
            
            sub_ids = {c.id for c in user.subscriptions}
            sub_names = {c.name.lower().strip() for c in user.subscriptions}

            # CHANGE: If user has 0 subscriptions, they get EVERYTHING (Discovery Mode)
            if not sub_ids:
                logger.info("User has no subscriptions - Validating 'Discovery Mode' (Sending all categories)", email=email)
                user_categories = list(state["categories"])
            else:
                # Regular subscription matching
                # First, pick up categories found in the API
                for cat in state["categories"]:
                    if cat.categoryId in sub_ids or cat.categoryName.lower().strip() in sub_names:
                        user_categories.append(cat)
                        found_ids.add(cat.categoryId)
            
            # Second, inject placeholders for missed subscriptions
            for sub in user.subscriptions:
                # Check if this sub was already accounted for (by ID or Name match)
                matched_already = any(
                    cat.categoryId == sub.id or cat.categoryName.lower().strip() == sub.name.lower().strip()
                    for cat in user_categories
                )
                
                if not matched_already:
                    logger.info("Injecting placeholder for missing subscription", category_id=sub.id, category_name=sub.name)
                    user_categories.append(CategoryData(
                        categoryId=sub.id,
                        categoryName=sub.name,
                        categorySummary="This department stream is currently unavailable or has been archived in the central system.",
                        tasks=[]
                    ))

            
            # Generate Management and Dashboard Links
            manage_token = create_manage_token(email)
            manage_link = f"{base_url}/manage/{manage_token}"
            dashboard_link = f"{base_url}/dashboard?token={manage_token}"

            
            # Generate HTML
            user_html = html_gen.generate(
                user_categories, 
                subscriptions={
                    "manage_link": manage_link,
                    "dashboard_link": dashboard_link
                }
            )
            
            # Send Email
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            subject = f"📰 My Bulletin – {date_str}"
            if not user_categories:
                subject = f"📰 Manage Your Subscriptions – {date_str}"
            
            logger.info("Sending personalized email", email=email, sub_count=len(user_categories))
            email_client.send_newsletter(
                recipients=email,
                content=user_html,
                subject=subject
            )

            # In Test Mode, save the email artifact for inspection
            if os.environ.get("TEST_MODE") == "true":
                try:
                    os.makedirs("output", exist_ok=True)
                    with open("output/email.html", "w", encoding="utf-8") as f:
                        f.write(user_html)
                    logger.info("Saved email artifact to output/email.html")
                except Exception as e:
                    logger.error("Failed to save email artifact", error=str(e))
            
        # Also update dynamic dashboard with ALL categories (admin view)
        try:
            from .dashboard_generator import DashboardGenerator
            dash_gen = DashboardGenerator()
            dashboard_html = await dash_gen.generate(state["categories"])
            os.makedirs("output", exist_ok=True)
            with open("output/index.html", "w", encoding="utf-8") as f:
                f.write(dashboard_html)
        except Exception as dash_err:
            logger.error("Dashboard update failed", error=str(dash_err))

    finally:
        db.close()
        
    return state

def create_newsletter_graph():
    workflow = StateGraph(NewsletterState)
    
    workflow.add_node("sync_categories", sync_categories_node)
    workflow.add_node("fetch_tasks", fetch_tasks_node)
    workflow.add_node("enrich_tasks", enrich_tasks_node)
    workflow.add_node("broadcast_newsletter", broadcast_newsletter_node)
    
    workflow.set_entry_point("sync_categories")
    workflow.add_edge("sync_categories", "fetch_tasks")
    workflow.add_edge("fetch_tasks", "enrich_tasks")
    workflow.add_edge("enrich_tasks", "broadcast_newsletter")
    workflow.add_edge("broadcast_newsletter", END)
    
    return workflow.compile()
