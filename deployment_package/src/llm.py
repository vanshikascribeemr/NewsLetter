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
            prompt_cards.append(f"Step {i+1}: {c}")
            
        comments_text = "\n".join(prompt_cards)
        
        system_prompt = (
            "You are a high-impact tech journalist writing a dramatic recap of weekly task progression. "
            "Summarize the provided task comments into a concise narrative paragraph of EXACTLY 2 to 4 lines. "
            "Use a dramatic, storytelling tone. Example: 'The task has officially sprung to life. Development is underway, fortified by newly added unit tests. Documentation has now reached its final form, and the work advances toward its defining moment — review. All eyes are on the next phase, where the task will be validated for full alignment with project objectives.' "
            "Focus on: achievements, milestones, and the momentum of the work. "
            "Avoid dry corporate speech; favor cinematic and active language. "
            "Do NOT exceed 4 lines. "
            "The summary MUST follow a chronological timeline of the last 7 days. "
            "Structure it like a news report: start with the spark of action, move through development intensity, and conclude with the high stakes of the upcoming phase."
            "IMPORTANT: If comments are provided (even if brief), you MUST summarize them with this dramatic flair. "
            "Do NOT return 'No changes reported' if there is input data."
        )
        human_prompt = f"Recent Activity Timeline:\n{comments_text}\n\nWrite a 2-3 line narrative story of this week's progression:"
        
        chain = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", human_prompt)
        ]) | self.llm
        
        try:
            response = await chain.ainvoke({})
            return response.content.strip()
        except Exception as e:
            return f"Failed to generate summary: {str(e)}"

    async def generate_category_summary(self, category_name: str, tasks: List[Task]) -> str:
        """
        Orchestrates the 6-stage summarization pipeline:
        Rules Engine -> Priority Filtering -> Embeddings -> Clustering -> TF-IDF -> LLM
        """
        if not tasks:
            return ""

        # 1. & 2. Rules Engine & Priority Filtering
        high_tasks = [t for t in tasks if (t.taskPriority or "").lower() == "high"]
        blocked_tasks = [t for t in tasks if (t.taskStatus or "").lower() == "blocked"]
        in_progress = [t for t in tasks if (t.taskStatus or "").lower() == "in progress"]
        
        # 3. & 4. Embeddings & Clustering (Simulated via LLM Theme Detection)
        themes = await self._detect_semantic_themes(tasks)
        
        # 5. TF-IDF (Keyphrase Extraction)
        keywords = self._extract_tfidf_keywords(tasks)
        
        # 6. LLM (Final Narrative Summary)
        return await self._synthesize_narrative(
            category_name, 
            high_tasks, 
            blocked_tasks, 
            in_progress, 
            themes, 
            keywords
        )

    async def _detect_semantic_themes(self, tasks: List[Task]) -> List[str]:
        """Simulates semantic clustering by asking the LLM to group tasks into themes."""
        if not tasks or not os.getenv("OPENAI_API_KEY"):
            return ["General Development"]
            
        task_list = "\n".join([f"- {t.taskSubject}: {t.summarizedComments or ''}" for t in tasks[:15]])
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a technical analyst. Group the following tasks into 2-3 high-level semantic themes. Return ONLY a comma-separated list of themes."),
            ("human", f"Tasks:\n{task_list}")
        ])
        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({})
            return [t.strip() for t in response.content.split(",")]
        except:
            return ["Core Infrastructure", "Functional Updates"]

    def _extract_tfidf_keywords(self, tasks: List[Task]) -> List[str]:
        """Simple pure-Python TF-IDF inspired keyphrase extraction."""
        import math
        from collections import Counter
        
        documents = [f"{t.taskSubject} {(t.summarizedComments or '')}".lower().split() for t in tasks]
        if not documents: return []
        
        # Term Frequency
        tfs = [Counter(doc) for doc in documents]
        
        # Document Frequency
        df = Counter()
        for doc in documents:
            df.update(set(doc))
            
        # Calculate TF-IDF
        num_docs = len(documents)
        scores = Counter()
        stop_words = {"the", "and", "is", "of", "to", "in", "a", "with", "for", "on", "was", "not", "tasks", "task"}
        
        for tf_map in tfs:
            for term, val in tf_map.items():
                if term in stop_words or len(term) < 3: continue
                idf = math.log(num_docs / (1 + df[term]))
                scores[term] += val * idf
                
        return [word for word, score in scores.most_common(8)]

    async def _synthesize_narrative(self, category, high, blocked, progress, themes, keywords) -> str:
        """Final stage: Narrative Synthesis using all pipeline outputs."""
        system_prompt = (
            "You are an executive technical news writer. "
            "Your task is to generate a concise, professional, news-style summary for a single task category. "
            "Style & Tone: "
            "- Corporate, authoritative, and clear "
            "- 5–6 sentences maximum "
            "- No bullet points "
            "- No emojis "
            "- Emphasize risks, momentum, and priority. "
            "Focus Rules: "
            "1. Start with overall momentum or health. "
            "2. Highlight blocked and high-risk items. "
            "3. Reference detected semantic themes. "
            "4. Infuse identified technical keywords. "
            "5. End with an overall assessment."
        )
        
        human_prompt = (
            f"Category: {category}\n"
            f"Momentum: {len(progress)} in progress, {len(blocked)} blocked.\n"
            f"High Priority Items: {len(high)} active.\n"
            f"Detected Themes: {', '.join(themes)}\n"
            f"Technical Keyphrases: {', '.join(keywords)}\n"
            f"Generate the paragraph summary:"
        )

        try:
            chain = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", human_prompt)
            ]) | self.llm
            response = await chain.ainvoke({})
            return response.content.strip()
        except Exception as e:
            return f"Final synthesis failed: {str(e)}"
