from bs4 import BeautifulSoup
import httpx
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import modal
from modal import Image, App, web_endpoint, Secret, Mount
from fastapi.responses import StreamingResponse
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.WARNING)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.propagate = True

app_image = (
    Image.debian_slim(python_version="3.10")
    .pip_install(
        "requests",
        "anthropic",
        "bs4"
    )
)

app = App(name="read-svc", image=app_image, secrets=[Secret.from_name("my-anthropic-secret")])

class ArticleData(BaseModel):
    url: str
    accessed_date: datetime
    title: str
    keywords: List[str]
    description: str
    content: str
    article_urls: List[str]
    status: str

class ReadRequest(BaseModel):
    urls: List[str]

class ReadResponse(BaseModel):
    articles: List[ArticleData]

# class ReadRequest(BaseModel):
#     urls: List[str]

# class ReadResponse(BaseModel):
#     articles: List[ArticleData]

router = APIRouter()

@app.function()
@web_endpoint(method="POST")
async def read(request: ReadRequest):
    async def article_stream():
        for url in request.urls:
            try:
                article = await fetch_and_parse_url(url)
                yield article.json().encode() + b"\n\n"
            except Exception as e:
                yield f"Error fetching {url}: {str(e)}\n\n".encode()
                continue  # or break, depending on desired behavior
    return StreamingResponse(article_stream(), media_type="text/event-stream")

async def fetch_and_parse_url(url: str) -> ArticleData:
    logging.debug(f"Initiating parsing for URL: {url}")
    raw_content = await fetch_content(url)
    try:
        # Assuming the content is a JSON string embedded within the stream
        content_data = json.loads(raw_content.split("data: ")[1])
        content = content_data['content']
    except (IndexError, json.JSONDecodeError) as e:
        logging.error(f"Error parsing JSON content for URL {url}: {str(e)}")
        content = "Content could not be parsed"

    metadata = await fetch_metadata(url)
    return ArticleData(
        url=url,
        accessed_date=datetime.now(),
        title=metadata['title'],
        keywords=metadata['keywords'],
        description=metadata['description'],
        content=content,
        article_urls=[],  # Placeholder for future enhancement
        status='read' if content else 'error'
    )

async def fetch_metadata(url: str) -> dict:
    logging.debug(f"Fetching metadata for URL: {url}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract title
            title = soup.find('title').text if soup.find('title') else 'No title found'
            og_title = soup.find('meta', attrs={'property': 'og:title', 'content': True})
            title = og_title['content'] if og_title else title

            # Extract description
            meta_description = soup.find('meta', attrs={'name': 'description', 'content': True})
            og_description = soup.find('meta', attrs={'property': 'og:description', 'content': True})
            description = og_description['content'] if og_description else (meta_description['content'] if meta_description else 'No description found')

            # Extract keywords
            meta_keywords = soup.find('meta', attrs={'name': 'keywords', 'content': True})
            keywords = meta_keywords['content'].split(',') if meta_keywords and meta_keywords['content'] else []

            return {
                'title': title,
                'description': description,
                'keywords': keywords
            }
        except Exception as e:
            logging.error(f"Failed to fetch metadata for {url}: {str(e)}")
            return {'title': '', 'description': '', 'keywords': []}

async def fetch_content(url: str) -> str:
    logging.debug(f"Initiating content fetch for URL: {url}")
    full_url = f"https://r.jina.ai/{url}"  # Construct the full URL
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            logging.debug(f"Sending HTTP GET request to stream: {full_url}")
            async with client.stream("GET", full_url, headers={"Accept": "text/event-stream"}) as response:
                logging.debug(f"HTTP stream opened for URL: {full_url}")
                content = ""
                line_count = 0
                async for line in response.aiter_lines():
                    line_count += 1
                    content += line + "\n"
                    if line_count % 250 == 0:  # Log every 250 lines
                        logging.debug(f"Received {line_count} lines so far from URL: {url}")
                logging.info(f"Completed fetching content from URL: {full_url}. Total lines received: {line_count}")
                return content
        except Exception as e:
            logging.error(f"Failed to fetch content for {url}: {str(e)}")
            return ""
