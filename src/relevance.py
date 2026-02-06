import math
import re
from typing import List, Dict
from .models import Task, CategoryData

def tokenize(text: str) -> List[str]:
    """Simple tokenizer that converts text to lower case and removes non-alphanumeric chars."""
    if not text:
        return []
    # Lowercase and split by non-word characters
    tokens = re.findall(r'\w+', text.lower())
    return [t for t in tokens if len(t) > 2] # Ignore very short words

def compute_tfidf(category: CategoryData):
    """
    Computes TF-IDF scores for all tasks within a category.
    Treats each task as a 'document'.
    """
    if not category.tasks:
        return

    # 1. Prepare documents: Subject + Comments
    documents = []
    for task in category.tasks:
        text = f"{task.taskSubject} {' '.join(task.followUpComments)}"
        documents.append(tokenize(text))

    num_docs = len(documents)
    
    # 2. Compute Document Frequency (DF)
    all_words = set(word for doc in documents for word in doc)
    df = {}
    for word in all_words:
        count = sum(1 for doc in documents if word in doc)
        df[word] = count

    # 3. Compute TF-IDF for each task
    for i, task in enumerate(category.tasks):
        doc = documents[i]
        if not doc:
            task.importanceScore = 0.0
            continue
            
        tf = {}
        for word in doc:
            tf[word] = tf.get(word, 0) + 1
            
        score = 0.0
        for word, count in tf.items():
            # Standard TF-IDF formula
            # tf_norm = count / len(doc)
            # idf = log(N / df)
            # Using a simplified version for small sets
            tf_val = count
            idf_val = math.log(num_docs / df[word]) if df[word] > 0 else 0
            score += tf_val * idf_val
        
        # Normalize by doc length to avoid penalizing short/long but relevant tasks
        task.importanceScore = round(score / len(doc), 4) if doc else 0.0

def rank_tasks(category: CategoryData):
    """Ranks tasks by importance score (Highest first)."""
    compute_tfidf(category)
    # Sort tasks: importanceScore DESC
    category.tasks.sort(key=lambda x: x.importanceScore, reverse=True)
