# Weekly Task Newsletter System

An automated system to fetch tasks, summarize updates using LLM, and send a weekly newsletter.

## Features
- Fetches tasks from multiple categories dynamically.
- Enrich tasks with follow-up comments from the last 7 days using LLM summaries.
- **Phase 2: Admin & Subscription Management**:
    - **Password-Protected Admin Dashboard**: Manage your recipient distribution list at `/admin`.
    - **Registry Database**: Add or remove recipients instantly without touching `.env`.
    - **Personalized Subscriptions**: Secure, tokenized links in every email for user-specific filtering.
    - **Automated Discovery Mode**: New users automatically see all categories until they choose their preferences.
- Prioritizes tasks (High > Medium > Low).
- Generates a professional newsletter using LangChain + LangGraph.
- Sends the newsletter via SMTP (Gmail/etc) and updates a local Dashboard (`index.html`).

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration**:
   Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```

   **Configuration Note:**
   To send to multiple people, separate emails with a comma:
   ```env
   RECIPIENT_EMAIL=manager@example.com, stakeholder@example.com
   ```

3. **Running the System**:
   
   **Step A: Start the Subscription API** (Required for the links to work):
   ```bash
   python -m src.api
   ```
   
   **Step B: Run the Newsletter Workflow**:
   ```bash
   python -m src.main
   ```

## Workflow Logic
The system uses LangGraph to orchestrate the following steps:
1. `sync_categories`: Synchronizes categories from the HRMS API to the local database.
2. `fetch_tasks`: Fetches all tasks across all categories.
3. `enrich_tasks`: Summarizes the last 7 days of comments for active tasks using AI.
4. `broadcast_newsletter`: 
    - Fetches the subscription list for each recipient.
    - Filters the content based on their preferences.
    - Generates personalized HTML with tokenized subscription management links.
    - Delivers individual emails.

## Scheduling

### Weekly Email Blast
To run the newsletter every Friday at 9 AM, use a cron job:
```cron
0 9 * * 5 cd /path/to/NewsLetter && /path/to/venv/bin/python -m src.main
```

### Performance Optimization: Pre-Cache Worker
Render's Free tier puts the web service to sleep during inactivity. To ensure the dashboard loads instantly for your team:
1. Create a **New Cron Job** on Render.
2. Command: `python -m src.worker`
3. Schedule: `*/15 * * * *` (Every 15 minutes).
This will keep the service awake and ensure AI summaries are always pre-calculated and ready.
