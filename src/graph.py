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

logger = structlog.get_logger()

class NewsletterState(TypedDict):
    categories: List[CategoryData]
    newsletter: Optional[NewsletterContent]
    recipient_email: str
    error: Optional[str]

async def fetch_tasks_node(state: NewsletterState):
    logger.info("Fetching all categories with tasks")
    client = TaskAPIClient()
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
        enriched_categories.append(category)
    
    return {**state, "categories": enriched_categories}

async def generate_newsletter_node(state: NewsletterState):
    if state.get("error") or not state["categories"]:
        return state
        
    logger.info("Generating Phase 3 Anchor-Based Newsletter")
    
    try:
        from .html_generator import HTMLGenerator
        html_gen = HTMLGenerator()
        
        # Generates the single HTML string with anchors/tables
        full_html = html_gen.generate(state["categories"])
        
        # 2. ALSO GENERATE DYNAMIC DASHBOARD (index.html)
        try:
            from .dashboard_generator import DashboardGenerator
            dash_gen = DashboardGenerator()
            dashboard_html = dash_gen.generate(state["categories"])
            
            # Save to root directory
            with open("index.html", "w", encoding="utf-8") as f:
                f.write(dashboard_html)
            logger.info("Dynamic Dashboard (index.html) updated.")
        except Exception as dash_err:
            logger.error("Dashboard generation failed", error=str(dash_err))
            # Don't fail the whole workflow if only dashboard fails
            
        # Calculate stats for logging
        total_tasks = sum(len(c.tasks) for c in state["categories"])
        
        newsletter = NewsletterContent(
            content=full_html,
            totalTasks=total_tasks
        )
        
        logger.info("Newsletter HTML generated successfully", size_bytes=len(full_html))
        return {**state, "newsletter": newsletter}
        
    except Exception as e:
        logger.error("HTML Generation failed", error=str(e))
        return {**state, "error": f"HTML Generation failed: {e}"}

async def send_email_node(state: NewsletterState):
    if state.get("error") or not state.get("newsletter"):
        logger.warning("Skipping email send due to error or missing content", error=state.get("error"))
        return state
        
    logger.info("Sending email")
    client = EmailClient()
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    subject = f"📰 Weekly Bulletin – {date_str}"
    
    success = client.send_newsletter(
        recipients=state["recipient_email"],
        content=state["newsletter"].content,
        subject=subject
    )
    
    if not success:
        return {**state, "error": "Email delivery failed"}
        
    return state

def create_newsletter_graph():
    workflow = StateGraph(NewsletterState)
    
    workflow.add_node("fetch_tasks", fetch_tasks_node)
    workflow.add_node("enrich_tasks", enrich_tasks_node)
    workflow.add_node("generate_newsletter", generate_newsletter_node)
    workflow.add_node("send_email", send_email_node)
    
    workflow.set_entry_point("fetch_tasks")
    workflow.add_edge("fetch_tasks", "enrich_tasks")
    workflow.add_edge("enrich_tasks", "generate_newsletter")
    workflow.add_edge("generate_newsletter", "send_email")
    workflow.add_edge("send_email", END)
    
    return workflow.compile()
