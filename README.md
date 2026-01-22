# Weekly Task Newsletter System

An automated system to fetch tasks, summarize updates using LLM, and send a weekly newsletter.

## Features
- Fetches tasks from a specific category.
- Enrich tasks with follow-up comments from the last 7 days.
- Prioritizes tasks (High > Medium > Low).
- Generates a professional newsletter using LangChain + LangGraph.
- Sends the newsletter via SMTP (Gmail/etc).

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
   ```bash
   python -m src.main
   ```

## Workflow Logic
The system uses LangGraph to orchestrate the following steps:
1. `fetch_tasks`: Calls `GetCategoryTasks`.
2. `enrich_tasks`: Calls `GetTaskFollowUpHistoryLast7Days` for each task.
3. `generate_newsletter`: Uses LLM to create the summary.
4. `send_email`: Dispatches the email via SMTP.

## Scheduling
To run this every Friday at 9 AM, use a cron job:
```cron
0 9 * * 5 cd /path/to/NewsLetter && /path/to/venv/bin/python -m src.main
```
