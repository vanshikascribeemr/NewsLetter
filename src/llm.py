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
