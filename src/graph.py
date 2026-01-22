from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from .models import Task, NewsletterContent, WorkflowState
from .api_client import TaskAPIClient
from .llm import NewsletterGenerator
from .email_client import EmailClient
import datetime
import structlog

logger = structlog.get_logger()

class NewsletterState(TypedDict):
    category_id: int
    category_name: str
    tasks: List[Task]
    newsletter: Optional[NewsletterContent]
    recipient_email: str
    error: Optional[str]

async def fetch_tasks_node(state: NewsletterState):
    logger.info("Fetching tasks", category_id=state["category_id"])
    client = TaskAPIClient()
    tasks = await client.get_category_tasks(state["category_id"])
    
    if not tasks:
        return {**state, "error": "No tasks found", "tasks": []}
    
    return {**state, "tasks": tasks}

async def enrich_tasks_node(state: NewsletterState):
    if state.get("error") or not state["tasks"]:
        return state
        
    logger.info("Enriching tasks with comments")
    client = TaskAPIClient()
    enriched_tasks = []
    
    for task in state["tasks"]:
        comments = await client.get_task_followup_history(task.taskId)
        task.followUpComments = comments
        enriched_tasks.append(task)
    
    # Sort by priority: High -> Medium -> Low
    priority_map = {"High": 0, "Medium": 1, "Low": 2}
    enriched_tasks.sort(key=lambda x: priority_map.get(x.taskPriority, 3))
    
    return {**state, "tasks": enriched_tasks}

async def generate_newsletter_node(state: NewsletterState):
    if state.get("error") or not state["tasks"]:
        return state
        
    logger.info("Generating newsletter with LLM")
    generator = NewsletterGenerator()
    try:
        newsletter = await generator.generate(state["category_name"], state["tasks"])
        return {**state, "newsletter": newsletter}
    except Exception as e:
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
