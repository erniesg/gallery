import httpx
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime
import modal
from modal import Image, App, web_endpoint, Secret, Mount
from fastapi.responses import StreamingResponse
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.propagate = True

# app_image = (
#     Image.debian_slim(python_version="3.10")
#     .pip_install(
#         "requests",
#         "anthropic"
#     )
# )

# app = App(name="query-app", image=app_image, secrets=[Secret.from_name("my-anthropic-secret")])

class ArticleData(BaseModel):
    response_content: str

class ReadRequest(BaseModel):
    urls: List[str]

class ReadResponse(BaseModel):
    articles: List[ArticleData]

# class ArticleData(BaseModel):
#     uuid: str
#     url: str
#     accessed_date: datetime
#     title: str
#     keywords: List[str]
#     description: str
#     contents: str
#     status: str
#     article_urls: List[str]

# class ReadRequest(BaseModel):
#     urls: List[str]

# class ReadResponse(BaseModel):
#     articles: List[ArticleData]

router = APIRouter()
app = App(name="query-app")

# @router.post("/read", response_model=ReadResponse)
@app.function()
@web_endpoint(method="GET")  # Adjust method as needed
async def read_urls(request: ReadRequest):
    async def article_stream():
        for url in request.urls:
            try:
                article = await fetch_and_parse_url(url)
                if article is not None:
                    yield article.response_content.encode() + b"\n\n"
                else:
                    yield f"Error fetching {url}: Article data is None\n\n".encode()
            except Exception as e:
                yield f"Error fetching {url}: {str(e)}\n\n".encode()
                continue  # or break, depending on desired behavior
    return StreamingResponse(article_stream(), media_type="text/event-stream")

async def fetch_and_parse_url(url: str) -> ArticleData:
    logging.debug(f"Initiating connection to fetch URL: {url}")
    async with httpx.AsyncClient() as client:
        try:
            # Correctly initiate the stream
            full_url = f"https://r.jina.ai/{url}"
            logging.debug(f"Sending HTTP GET request to stream: {full_url}")

            async with client.stream("GET", full_url, headers={"Accept": "text/event-stream"}) as response:
                logging.debug(f"HTTP stream opened for URL: {full_url}")
                content = ""
                # Iterate over the lines in the response
                line_count = 0
                async for line in response.aiter_lines():
                    line_count += 1
                    content += line + "\n"
                    if line_count % 250 == 0:  # Log every 250 lines
                        logging.debug(f"Received {line_count} lines so far from URL: {url}")
                logging.info(f"Completed fetching content from URL: {full_url}. Total lines received: {line_count}")
                # Process the content as needed
                return ArticleData(response_content=content)
        except Exception as e:
            logging.error(f"Failed to fetch {url}: {str(e)}")
            return None

async def article_stream():
    for url in request.urls:
        article = await fetch_and_parse_url(url)
        if article is None:
            yield b"Error occurred\n\n"
        else:
            yield article.response_content.encode() + b"\n\n"
