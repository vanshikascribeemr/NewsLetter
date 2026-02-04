import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .models import Task, NewsletterContent
from typing import List
import os
from .prompts import SYSTEM_PROMPT, HUMAN_PROMPT_TEMPLATE

class NewsletterGenerator:
    def __init__(self, model_name: str = "gpt-4o", openai_api_key: str = None):
        self.llm = ChatOpenAI(
            model=model_name,
            api_key=openai_api_key or os.getenv("OPENAI_API_KEY"),
            temperature=0
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", HUMAN_PROMPT_TEMPLATE)
        ])

    async def generate(self, category_name: str, tasks: List[Task]) -> NewsletterContent:
        if not os.getenv("OPENAI_API_KEY"):
            return NewsletterContent(
                content=f"DRY RUN: Weekly Newsletter - {category_name}\n\nSummary for {len(tasks)} tasks.",
                totalTasks=len(tasks)
            )

        tasks_data = [t.model_dump() for t in tasks]
        chain = self.prompt | self.llm
        
        response = await chain.ainvoke({
            "category_name": category_name,
            "total_tasks": len(tasks),
            "tasks_json": json.dumps(tasks_data, indent=2)
        })
        
        # Parse the JSON response
        try:
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            data = json.loads(content.strip())
            return NewsletterContent(**data)
        except Exception as e:
            # Fallback or error handling
            raise ValueError(f"Failed to parse LLM response: {e}\nContent was: {response.content}")

    async def summarize_comments(self, comments: List[str]) -> str:
        """
        Summarizes a list of comments into a single narrative paragraph.
        """
        if not comments:
            return "No changes reported over the last 7 days."
            
        if not os.getenv("OPENAI_API_KEY"):
            return f"[MOCK SUMMARY] Summarized {len(comments)} comments: " + " | ".join(comments[:2]) + "..."

        prompt_cards = []
        for i, c in enumerate(comments):
            prompt_cards.append(f"Comment {i+1}: {c}")
            
        comments_text = "\n".join(prompt_cards)
        
        # Prompt for detailed, narrative summary (strictly 2-3 lines)
        system_prompt = (
            "You are a senior project manager writing weekly status updates for executive stakeholders. "
            "Summarize the provided task comments into a concise narrative paragraph of EXACTLY 2 to 3 lines. "
            "Focus on: what was done, key blockers, and next steps. "
            "Use a professional, executive tone. "
            "Do NOT exceed 3 lines under any circumstances. "
            "IMPORTANT: If comments are provided (even if brief like 'Task Created'), you MUST summarize them. "
            "Do NOT return 'No changes reported' if there is input data. "
            "If the comment is just 'Task Created', state that the task was initiated and is pending review."
        )
        human_prompt = f"Recent Activity Comments:\n{comments_text}\n\nWrite a 2-3 line summary:"
        
        chain = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", human_prompt)
        ]) | self.llm
        
        try:
            response = await chain.ainvoke({})
            return response.content.strip()
        except Exception as e:
            return f"Failed to generate summary: {str(e)}"
