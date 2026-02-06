from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import secrets
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from .database import get_db, User, Category, init_db, SessionLocal, sync_categories
from .security import verify_token
from .models import CategoryData
import structlog
from contextlib import asynccontextmanager
import asyncio

logger = structlog.get_logger()

async def prewarm_cache():
    """Pre-warms the category cache AND enriches with 7-day comment summaries for instant dashboard loads."""
    try:
        from .api_client import TaskAPIClient, get_cached_categories, get_enriched_categories, set_enriched_categories
        from .llm import NewsletterGenerator
        
        # Step 1: Pre-warm basic category cache
        if get_cached_categories() is None:
            logger.info("Pre-warming category cache in background...")
            client = TaskAPIClient()
            categories = await client.get_all_categories_with_tasks()
            
            # Sync to DB to ensure "My Streams" matches API categories
            db = SessionLocal()
            try:
                sync_categories(db, [c.model_dump(by_alias=True) for c in categories])
                logger.info("Categories synced to database during pre-warm", count=len(categories))
            finally:
                db.close()
                
            logger.info("Basic cache pre-warmed", count=len(categories) if categories else 0)
        
            # Step 2: Enrich with 7-day comment summaries (for dashboard)
            if get_enriched_categories() is None:
                logger.info("Enriching categories with 7-day comment summaries...")
                client = TaskAPIClient()
                llm_gen = NewsletterGenerator()
                
                # Get categories from cache
                categories = get_cached_categories()
                if not categories:
                    categories = await client.get_all_categories_with_tasks()
                
                # Deep copy to avoid modifying cached data
                import copy
                enriched_categories = copy.deepcopy(categories)
                
                async def enrich_category(category):
                    # Filter out "Done" tasks
                    category.tasks = [t for t in category.tasks if (t.taskStatus or "").lower() != "done"]
                    
                    if not category.tasks:
                        category.categorySummary = "No active work items recorded in this workstream for the current period."
                        return category
                    
                    logger.info("Enriching category", category_id=category.categoryId, category_name=category.categoryName)
                    
                    async def enrich_task(t):
                        try:
                            comments = await client.get_task_followup_history(t.taskId)
                            t.followUpComments = comments
                            if comments:
                                t.summarizedComments = await llm_gen.summarize_comments(comments)
                            else:
                                t.summarizedComments = "No recent activity recorded in the last 7 days."
                        except Exception as e:
                            logger.error("Error enriching task", task_id=t.taskId, error=str(e))
                            t.summarizedComments = "Update retrieval error."
                        return t
                    
                    # Process tasks in parallel for this category
                    enriched_tasks = await asyncio.gather(*[enrich_task(task) for task in category.tasks])
                    category.tasks = list(enriched_tasks)
                    
                    # Generate category-level synthesis
                    try:
                        category.categorySummary = await llm_gen.generate_category_summary(category.categoryName, category.tasks)
                    except Exception as e:
                        logger.error("Failed to generate category summary", category=category.categoryName, error=str(e))
                        category.categorySummary = "Summary generation failed."
                    
                    return category

                # Process ALL categories in parallel
                enriched_categories = await asyncio.gather(*[enrich_category(cat) for cat in enriched_categories])
                
                # Store enriched data
                set_enriched_categories(list(enriched_categories))
                logger.info("Enriched cache pre-warmed successfully", count=len(enriched_categories))
            
    except Exception as e:
        logger.error("Failed to pre-warm cache", error=str(e))

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Pre-warm cache on startup (non-blocking)
    asyncio.create_task(prewarm_cache())
    yield

app = FastAPI(title="Newsletter Subscription API", lifespan=lifespan)

@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")

@app.get("/api/refresh-cache")
async def refresh_cache(background_tasks: BackgroundTasks):
    """
    Endpoint to trigger a cache refresh in the background.
    Returns immediately while cache updates happen asynchronously.
    """
    from .api_client import invalidate_cache
    invalidate_cache()
    background_tasks.add_task(prewarm_cache)
    return JSONResponse({"status": "Cache refresh initiated", "message": "Dashboard will be updated shortly"})

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(token: str = None, db: Session = Depends(get_db)):
    from .dashboard_generator import DashboardGenerator
    from .api_client import TaskAPIClient, get_enriched_categories, get_cached_categories
    
    # 1. Identify user subscriptions first (fast DB query)
    subscribed_ids = []
    if token:
        payload = verify_token(token)
        if payload:
            email = payload.get("email")
            user = db.query(User).filter(User.email == email).first()
            if user:
                subscribed_ids = [c.id for c in user.subscriptions]
    
    # 2. Prefer enriched cache (with 7-day comment summaries)
    categories = get_enriched_categories()
    
    if categories is not None:
        # Enriched cache hit - serve immediately with full summaries
        logger.info("Dashboard: Serving from ENRICHED cache (with summaries)", count=len(categories))
    else:
        # Fall back to basic cache (without summaries)
        categories = get_cached_categories()
        if categories is not None:
            logger.info("Dashboard: Serving from basic cache (summaries pending)", count=len(categories))
        else:
            # Cache miss - need to fetch (slow path, first load only)
            logger.info("Dashboard: Cache miss, fetching from API...")
            client = TaskAPIClient()
            categories = await client.get_all_categories_with_tasks()
            
            # Sync to DB during slow path
            sync_db = SessionLocal()
            try:
                sync_categories(sync_db, [c.model_dump(by_alias=True) for c in categories])
                logger.info("Categories synced to database during slow-path fetch", count=len(categories))
            finally:
                sync_db.close()
    
    # 3. Generate personalized dashboard
    dash_gen = DashboardGenerator()
    
    # Ensure categories is a list we can safely manipulate (not the cache reference)
    categories_to_render = list(categories) if categories else []
    
    if token:
        payload = verify_token(token)
        if payload:
            email = payload.get("email")
            user = db.query(User).filter(User.email == email).first()
            if user:
                # Injection Logic: If user has subscriptions not in the API categories, inject placeholders
                existing_ids = {c.categoryId for c in categories_to_render}
                existing_names = {c.categoryName.lower().strip() for c in categories_to_render}
                
                for sub in user.subscriptions:
                    sub_name_norm = sub.name.lower().strip()
                    if sub.id not in existing_ids and sub_name_norm not in existing_names:
                        logger.info("Injecting placeholder subscription for dashboard", category_id=sub.id, category_name=sub.name)
                        categories_to_render.append(CategoryData(
                            categoryId=sub.id,
                            categoryName=sub.name,
                            categorySummary="This department stream is currently unavailable or has been archived in the central system.",
                            tasks=[]
                        ))

    # Pass both IDs and Names for robust matching
    subscribed_names = []
    if token:
        payload = verify_token(token)
        if payload:
            email = payload.get("email")
            user = db.query(User).filter(User.email == email).first()
            if user:
                subscribed_names = [c.name.lower().strip() for c in user.subscriptions]

    html_content = await dash_gen.generate(
        categories_to_render, 
        subscribed_ids=subscribed_ids, 
        subscribed_names=subscribed_names
    )
    return HTMLResponse(content=html_content)


@app.get("/subscribe/{token}", response_class=HTMLResponse)
async def subscribe(token: str, db: Session = Depends(get_db)):
    payload = verify_token(token)
    if not payload or payload.get("action") != "subscribe":
        return HTMLResponse(content="<h1>Invalid or expired token</h1>", status_code=400)
    
    email = payload.get("email")
    category_id = payload.get("category_id")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
        
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        # Category should ideally exist, but we can create it if not
        return HTMLResponse(content="<h1>Category not found</h1>", status_code=404)
    
    if category not in user.subscriptions:
        user.subscriptions.append(category)
        db.commit()
        logger.info("User subscribed", email=email, category=category.name)
    
    return f"""
    <html>
        <body style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #4CAF50;">Subscription Confirmed!</h1>
            <p>You have successfully subscribed to <b>{category.name}</b>.</p>
            <p>You will receive updates for this category in the next newsletter.</p>
        </body>
    </html>
    """

@app.get("/unsubscribe/{token}", response_class=HTMLResponse)
async def unsubscribe(token: str, db: Session = Depends(get_db)):
    payload = verify_token(token)
    if not payload or payload.get("action") != "unsubscribe":
        return HTMLResponse(content="<h1>Invalid or expired token</h1>", status_code=400)
    
    email = payload.get("email")
    category_id = payload.get("category_id")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return HTMLResponse(content="<h1>User not found</h1>", status_code=404)
        
    category = db.query(Category).filter(Category.id == category_id).first()
    if category and category in user.subscriptions:
        user.subscriptions.remove(category)
        db.commit()
        logger.info("User unsubscribed", email=email, category=category.name)
    
    return f"""
    <html>
        <body style="font-family: sans-serif; text-align: center; padding: 50px; background-color: #f3f4f6;">
            <div style="background: white; padding: 40px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <h1 style="color: #f44336; margin-top: 0;">Unsubscribed</h1>
                <p style="color: #4b5563; font-size: 18px;">You have been unsubscribed from <b>{category.name if category else 'the category'}</b>.</p>
                <p style="color: #6b7280;">You can manage all your subscriptions <a href="/manage/{token}" style="color: #3b82f6; text-decoration: none; font-weight: 600;">here</a>.</p>
            </div>
        </body>
    </html>
    """

@app.get("/manage/{token}", response_class=HTMLResponse)
async def manage_subscriptions(token: str, db: Session = Depends(get_db)):
    payload = verify_token(token)
    if not payload or payload.get("action") not in ["manage", "subscribe", "unsubscribe"]:
        return HTMLResponse(content="<h1>Invalid or expired token</h1>", status_code=400)
    
    email = payload.get("email")
    
    # Block access for system sender email, unless it's the host
    sender_email = os.getenv("SENDER_EMAIL", os.getenv("SMTP_USER"))
    host_email = os.getenv("HOST_EMAIL")
    if email == sender_email and (not host_email or email != host_email):
        return HTMLResponse(content="<h1>Access Denied</h1><p>The system sender account cannot manage subscriptions.</p>", status_code=403)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    categories = db.query(Category).all()
    subscribed_ids = [c.id for c in user.subscriptions]
    
    category_items = ""
    for cat in categories:
        checked = "checked" if cat.id in subscribed_ids else ""
        category_items += f"""
        <div class="category-item">
            <input type="checkbox" name="category_{cat.id}" id="cat_{cat.id}" {checked} style="width: 20px; height: 20px; cursor: pointer; accent-color: #FCA311;">
            <label for="cat_{cat.id}" class="category-label">{cat.name}</label>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Subscription Intelligence | The Sync</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
        <style>
            :root {{
                --accent: #5c8ca3;
                --accent-light: #dae5ed;
                --ink: #1a202c;
                --ink-muted: #718096;
                --border: #edf2f7;
            }}

            body {{ 
                font-family: 'Inter', sans-serif; 
                background: #f7fafc; 
                margin: 0; 
                padding: 0; 
                color: var(--ink); 
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}

            .envelope {{ 
                max-width: 540px; 
                width: 90%;
                background: white; 
                padding: 60px 48px; 
                border-radius: 12px; 
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.05);
                border: 1px solid var(--border);
                position: relative;
                overflow: hidden;
            }}

            .brand-bar {{
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 6px;
                background: var(--accent);
            }}

            h1 {{ 
                font-size: 32px; 
                font-weight: 900; 
                margin: 0 0 12px 0; 
                color: var(--accent); 
                letter-spacing: -0.03em;
                text-transform: uppercase;
            }}

            p {{ 
                color: var(--ink-muted); 
                margin-bottom: 40px; 
                font-size: 16px; 
                line-height: 1.6; 
                font-weight: 500;
            }}

            .toggle-btn {{ 
                display: block;
                background: transparent;
                border: 2px solid var(--accent);
                color: var(--accent);
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 13px;
                font-weight: 800;
                cursor: pointer;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                transition: all 0.2s;
                margin-bottom: 30px;
                width: fit-content;
            }}

            .toggle-btn:hover {{
                background: var(--accent);
                color: white;
            }}

            .category-list {{
                display: flex;
                flex-direction: column;
                gap: 12px;
                margin-bottom: 40px;
            }}

            .category-item {{ 
                display: flex; 
                align-items: center; 
                padding: 16px 20px; 
                background: #ffffff; 
                border: 1px solid var(--border); 
                border-radius: 10px; 
                transition: 0.2s; 
                cursor: pointer;
            }}

            .category-item:hover {{ 
                border-color: var(--accent); 
                background: #fdfdfd; 
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            }}

            .category-item input[type="checkbox"] {{
                width: 22px;
                height: 22px;
                cursor: pointer;
                accent-color: var(--accent);
                margin: 0;
            }}

            .category-label {{
                margin-left: 16px; 
                cursor: pointer; 
                font-size: 16px; 
                color: var(--ink); 
                font-weight: 700; 
                flex-grow: 1;
            }}

            .save-btn {{ 
                background: var(--accent); 
                color: white; 
                border: none; 
                padding: 20px; 
                width: 100%; 
                border-radius: 10px; 
                font-size: 16px; 
                font-weight: 900; 
                cursor: pointer; 
                text-transform: uppercase;
                letter-spacing: 0.1em;
                transition: all 0.2s;
                box-shadow: 0 10px 20px rgba(92, 140, 163, 0.2);
            }}

            .save-btn:hover {{ 
                background: #4a7c9d;
                transform: translateY(-2px);
                box-shadow: 0 15px 30px rgba(92, 140, 163, 0.3);
            }}

            .save-btn:active {{ transform: translateY(0); }}

            .footer-info {{
                margin-top: 32px; 
                text-align: center; 
                font-size: 12px; 
                color: var(--ink-muted);
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}

            .footer-info b {{
                color: var(--ink);
            }}
        </style>
    </head>
    <body>
        <div class="envelope">
            <div class="brand-bar"></div>
            <h1>The Sync</h1>
            <p>Tailor your intelligence briefing by selecting the departmental streams you wish to follow. Your preferences define the scope of your newsletter.</p>
            
            <button type="button" id="toggle-all" class="toggle-btn">SELECT ALL STREAMS</button>

            <form action="/save-subscriptions" method="post">
                <input type="hidden" name="token" value="{token}">
                <div class="category-list">
                    {category_items}
                </div>
                <button type="submit" class="save-btn">CONFIRM PREFERENCES</button>
            </form>
            
            <div class="footer-info">
                AUTHENTICATED AS: <b>{email}</b>
            </div>
        </div>

        <script>
            const toggleBtn = document.getElementById('toggle-all');
            const checkboxes = document.querySelectorAll('input[type="checkbox"]');

            function updateBtnText() {{
                const allChecked = Array.from(checkboxes).every(cb => cb.checked);
                toggleBtn.textContent = allChecked ? "Deselect all category" : "Select all category";
            }}

            toggleBtn.addEventListener('click', () => {{
                const allChecked = Array.from(checkboxes).every(cb => cb.checked);
                checkboxes.forEach(cb => cb.checked = !allChecked);
                updateBtnText();
            }});

            checkboxes.forEach(cb => cb.addEventListener('change', updateBtnText));

            // Initial check
            updateBtnText();
        </script>
    </body>
    </html>
    """

from fastapi import Form

@app.post("/save-subscriptions", response_class=HTMLResponse)
async def save_subscriptions(request: Request, token: str = Form(...), db: Session = Depends(get_db)):
    payload = verify_token(token)
    if not payload or payload.get("action") not in ["manage", "subscribe", "unsubscribe"]:
        return HTMLResponse(content="<h1>Authentication failed</h1>", status_code=400)
    
    email = payload.get("email")
    
    # Block save for system sender email, unless it's the host
    sender_email = os.getenv("SENDER_EMAIL", os.getenv("SMTP_USER"))
    host_email = os.getenv("HOST_EMAIL")
    if email == sender_email and (not host_email or email != host_email):
        return HTMLResponse(content="<h1>Access Denied</h1>", status_code=403)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return HTMLResponse(content="<h1>User not found</h1>", status_code=404)
    
    # Get all categories
    all_categories = db.query(Category).all()
    
    # Process form data
    form_data = await request.form()
    
    # Clear current subscriptions and rebuild
    user.subscriptions = []
    for cat in all_categories:
        if form_data.get(f"category_{cat.id}") == "on":
            user.subscriptions.append(cat)
    
    db.commit()
    logger.info("Subscriptions updated", email=email, count=len(user.subscriptions))
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Preferences Saved | The Sync</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
        <style>
            :root {{
                --accent: #5c8ca3;
                --ink: #1a202c;
                --ink-muted: #718096;
                --border: #edf2f7;
            }}
            body {{ 
                font-family: 'Inter', sans-serif; 
                text-align: center; 
                padding: 0; 
                margin: 0;
                background-color: #f7fafc; 
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .envelope {{ 
                background: white; 
                padding: 60px 40px; 
                border-radius: 12px; 
                display: inline-block; 
                box-shadow: 0 20px 40px rgba(0,0,0,0.05); 
                max-width: 440px; 
                width: 90%;
                border: 1px solid var(--border);
                position: relative;
            }}
            .brand-bar {{
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 6px;
                background: var(--accent);
            }}
            .icon-box {{
                width: 80px;
                height: 80px;
                background: #f0fdf4;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 30px;
            }}
            h1 {{ color: #059669; font-size: 28px; font-weight: 900; margin-bottom: 16px; letter-spacing: -0.02em; }}
            p {{ color: var(--ink-muted); line-height: 1.6; font-size: 16px; font-weight: 500; margin-bottom: 10px; }}
            .sub-text {{ font-size: 14px; color: #9ca3af; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="envelope">
            <div class="brand-bar"></div>
            <div class="icon-box">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
            </div>
            <h1>Intelligence Tuned</h1>
            <p>Your subscription preferences have been successfully updated in our operations database.</p>
            <p>You will receive the next briefing according to your new filter criteria.</p>
            <div class="sub-text">You may now close this window safely.</div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

# --- ADMIN SECURITY ---

security = HTTPBasic()

def authenticate_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, ":f(m6Y^{2a]K4y6L")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# --- ADMIN ROUTES ---

class UserCreate(BaseModel):
    email: str

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(db: Session = Depends(get_db), admin: str = Depends(authenticate_admin)):
    from .admin_generator import AdminGenerator
    users = db.query(User).all()
    gen = AdminGenerator()
    return HTMLResponse(content=gen.generate(users))

@app.post("/admin/users")
async def add_user(user_data: UserCreate, db: Session = Depends(get_db), admin: str = Depends(authenticate_admin)):
    from .database import get_user_by_email
    email = user_data.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    # Check if exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already in registry")
        
    user = User(email=email)
    db.add(user)
    db.commit()
    return {"message": "User added successfully"}

@app.delete("/admin/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db), admin: str = Depends(authenticate_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    db.delete(user)
    db.commit()
    return {"message": "User removed successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
