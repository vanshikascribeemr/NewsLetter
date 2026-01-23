from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from .models import Task, NewsletterContent, WorkflowState, CategoryData
from .api_client import TaskAPIClient
from .llm import NewsletterGenerator
from .email_client import EmailClient
import datetime
import structlog
import os

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
    enriched_categories = []
    
    # Priority map for sorting
    priority_map = {"High": 0, "Medium": 1, "Low": 2}
    
    for category in state["categories"]:
        enriched_tasks = []
        
        logger.info("Enriching category", category_id=category.categoryId, category_name=category.categoryName)
        
        for task in category.tasks:
            comments = await client.get_task_followup_history(task.taskId)
            task.followUpComments = comments
            enriched_tasks.append(task)
        
        # Sort tasks by priority: High -> Medium -> Low
        enriched_tasks.sort(key=lambda x: priority_map.get(x.taskPriority, 3))
        
        # Update category with enriched tasks
        category.tasks = enriched_tasks
        enriched_categories.append(category)
    
    return {**state, "categories": enriched_categories}

async def generate_newsletter_node(state: NewsletterState):
    if state.get("error") or not state["categories"]:
        return state
        
    logger.info("Generating newsletter with LLM for all categories")
    generator = NewsletterGenerator()
    
    try:
        category_summaries = []
        total_tasks_count = 0
        
        # Generate summary for each category
        for category in state["categories"]:
            # Skip categories with no tasks
            if not category.tasks:
                logger.info("Skipping empty category", category_name=category.categoryName)
                continue
            
            logger.info("Generating summary for category", category_name=category.categoryName, task_count=len(category.tasks))
            
            # Generate newsletter for this category
            category_newsletter = await generator.generate(category.categoryName, category.tasks)
            category_summaries.append(category_newsletter.content)
            total_tasks_count += category_newsletter.totalTasks
        
        # Consolidate all category summaries with separator lines
        if not category_summaries:
            consolidated_content = "No task activity occurred this week across all categories."
        else:
            # Join with separator lines
            consolidated_content = "\n\n---\n\n".join(category_summaries)
        
        newsletter = NewsletterContent(
            content=consolidated_content,
            totalTasks=total_tasks_count
        )
        
        logger.info("Newsletter generated successfully", total_categories=len(category_summaries), total_tasks=total_tasks_count)
        return {**state, "newsletter": newsletter}
        
    except Exception as e:
        logger.error("LLM Generation failed", error=str(e))
        return {**state, "error": f"LLM Generation failed: {e}"}

async def send_email_node(state: NewsletterState):
    if state.get("error") or not state.get("newsletter"):
        logger.warning("Skipping email send due to error or missing content", error=state.get("error"))
        return state
        
    logger.info("Sending email")
    client = EmailClient()
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    subject = f"📰 Weekly Task Newsletter – {date_str}"
    
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
