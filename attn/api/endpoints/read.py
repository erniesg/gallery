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
import backoff
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("hpack").setLevel(logging.WARNING)

app_image = (
    Image.debian_slim(python_version="3.10")
    .pip_install(
        "requests",
        "anthropic",
        "bs4",
        "lxml",
        "backoff"
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
    logging.info(f"Initiating parsing for URL: {url}")
    try:
        raw_content = await fetch_content(url)
        logging.info(f"Received raw content: {raw_content} of {type(raw_content)}")

        # Split the content into lines and filter for lines starting with 'data:'
        json_str = next(line for line in raw_content.split('\n') if line.startswith('data:')).strip()[5:]
        # Join the filtered lines and parse as JSON
        content_data = json.loads(json_str)
        content = content_data['content']

        metadata = await fetch_metadata(url)
        title = metadata['title']
        keywords = metadata['keywords']
        description = metadata['description']

        # Check if both title and content are not empty
        if title != 'No title found' and content.strip():
            status = 'read'
        else:
            status = 'error'
            logging.error(f"Insufficient data for URL {url}: Title or content missing.")

    except Exception as e:
        logging.error(f"Error processing URL {url}: {str(e)}")
        title = 'No title found'
        description = 'No description found'
        keywords = []
        content = "Content could not be parsed"
        status = 'error'

    return ArticleData(
        url=url,
        accessed_date=datetime.now(),
        title=title,
        keywords=keywords,
        description=description,
        content=content,
        article_urls=[],  # Placeholder for future enhancement
        status=status
    )

async def fetch_metadata(url: str) -> dict:
    logging.info(f"Fetching metadata for URL: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        "Referer": "https://www.google.com/"
    }
    async with httpx.AsyncClient(follow_redirects=True, headers=headers) as client:
        try:
            response = await client.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'lxml')

            # Extract title
            title_tag = soup.find('title')
            title = title_tag.text if title_tag else 'No title found'
            logging.info(f"Extracted title: {title}")

            # Extract description
            meta_description = soup.find('meta', attrs={'name': 'description', 'content': True})
            description = meta_description['content'].strip() if meta_description else 'No description found'
            if description == 'No description found':
                og_description = soup.find('meta', attrs={'property': 'og:description', 'content': True})
                description = og_description['content'].strip() if og_description else description
            logging.info(f"Extracted description: {description}")

            # Extract keywords
            meta_keywords = soup.find('meta', attrs={'name': 'keywords', 'content': True})
            keywords = meta_keywords['content'].split(',') if meta_keywords and meta_keywords['content'] else []
            logging.info(f"Keywords: {keywords}")

            # Return a structured dictionary that matches the ArticleData fields
            return {
                'title': title,
                'description': description,
                'keywords': keywords
            }
        except Exception as e:
            logging.error(f"Failed to fetch metadata for {url}: {str(e)}")
            return {
                'title': 'No title found',
                'description': 'No description found',
                'keywords': []
            }

@backoff.on_exception(backoff.expo, httpx.HTTPError, max_tries=3)
async def fetch_content(url: str) -> str:
    logging.info(f"Initiating content fetch for URL: {url}")
    full_url = f"https://r.jina.ai/{url}"  # Construct the full URL
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            logging.info(f"Sending HTTP GET request to stream: {full_url}")
            async with client.stream("GET", full_url, headers={"Accept": "text/event-stream"}) as response:
                logging.info(f"HTTP stream opened for URL: {full_url}")
                content = ""
                line_count = 0
                async for line in response.aiter_lines():
                    line_count += 1
                    content += line + "\n"
                    if line_count % 250 == 0:  # Log every 250 lines
                        logging.info(f"Received {line_count} lines so far from URL: {url}")
                logging.info(f"Completed fetching content from URL: {full_url}. Total lines received: {line_count}")
                return content
        except Exception as e:
            logging.error(f"Failed to fetch content for {url}: {str(e)}")
            return ""
