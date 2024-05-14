from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import logging
import json
from datetime import datetime
import sys
import os
from modal import Image, App, web_endpoint, Secret, Mount

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app_image = (
    Image.debian_slim(python_version="3.10")
    .pip_install(
        "requests",
        "anthropic"
    )
)

app = App(name="score-svc", image=app_image, secrets=[Secret.from_name("my-anthropic-secret")])

class ArticleData(BaseModel):
    url: str
    accessed_date: datetime
    title: str
    keywords: List[str]
    description: str
    content: str
    article_urls: List[str]
    status: str

class ScoreRequest(BaseModel):
    articles: List[ArticleData]
    schema_name: str = "default-schema"  # Default schema to use for scoring

class ScoreResponse(BaseModel):
    url: str
    scores: Dict[str, int]

def load_schema(schema_path: str) -> Dict:
    try:
        with open(schema_path, 'r') as file:
            logger.info(f"Schema loaded from {schema_path}")
            schema = json.load(file)
            return schema
    except Exception as e:
        logger.error(f"Error loading schema from {schema_path}: {str(e)}")
        raise HTTPException(status_code=500, detail="Schema loading error")

@app.function(mounts=[
    Mount.from_local_dir(
        local_path="/Users/erniesg/code/erniesg/shareshare/attn/api/endpoints",
        remote_path="/app/endpoints",
        condition=lambda pth: "score.py" not in pth,
        recursive=True
    )
])
@web_endpoint(method="POST")
async def score(request: ScoreRequest):
    sys.path.insert(0, '/app')
    sys.path.insert(0, '/app/endpoints')
    logger.info(f"Current sys.path: {sys.path}")
    logger.info(f"Files in the /app/endpoints directory: {os.listdir('/app/endpoints')}")
    logger.info(f"Files and directories in the current working directory: {os.listdir('.')}")

    scores = await score_articles(request)
    return {"scores": scores}

async def score_articles(request: ScoreRequest, model_name: str = "claude-3-haiku-20240307"):
    from llm_handler import LLMHandler
    from prompts import get_prompts
    llm_handler = LLMHandler()

    if not request.articles:
        raise HTTPException(status_code=400, detail="No articles provided")

    schema = load_schema('/app/endpoints/schema.json')
    topics = schema.get("topics", [])
    logger.info(f"score.py - Topics loaded: {topics}")

    all_scores = []  # List to collect scores from all articles

    # Iterate over each article in the request
    for article in request.articles:
        logger.info(f"Scoring article with URL: {article.url}")
        try:
            system_prompt, message_prompt = get_prompts(
                "score_article", request,
                url=article.url,
                title=article.title,
                keywords=article.keywords,
                description=article.description,
                content=article.content,
                topics=topics
            )
            logger.debug(f"System prompt: {system_prompt}")
            logger.debug(f"Message prompt: {message_prompt}")
        except KeyError:
            logger.error("Prompt configuration for 'score_article' not found.")
            raise HTTPException(status_code=500, detail="Configuration error")

        # Call the LLM and handle the response for each article
        try:
            logger.info(f"score.py - Preparing to call LLM for article with URL: {article.url}")
            response_text = llm_handler.call_llm(
                "score_article",
                request,
                model_name=model_name,
                url=article.url,
                title=article.title,
                keywords=",".join(article.keywords),
                description=article.description,
                content=article.content,
                topics=topics  # Add topics here
            )
            score_data = parse_scores_from_response(response_text)
            all_scores.append(ScoreResponse(url=article.url, scores=score_data))
        except Exception as e:
            logger.error(f"LLM call failed for article {article.url}: {str(e)}")
            # Optionally continue to the next article or raise an HTTPException
            continue  # Continue processing next articles even if one fails

    return all_scores  # Return the collected scores from all articles

def parse_scores_from_response(text: str) -> Dict[str, int]:
    try:
        data = json.loads(text)
        logger.info(f"Scores parsed from response: {data}")
        return data['scores']  # Return only the scores dictionary
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error parsing scores from response: {str(e)}")
        return {}
