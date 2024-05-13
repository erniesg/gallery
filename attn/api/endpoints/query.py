from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
from typing import List, Optional
import modal
from modal import Image, App, web_endpoint, Secret, Mount
import os
from fastapi.responses import StreamingResponse
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the Docker image with necessary dependencies
app_image = (
    Image.debian_slim(python_version="3.10")
    .pip_install(
        "requests",
        "anthropic"
    )
)

app = App(name="query-svc", image=app_image, secrets=[Secret.from_name("my-anthropic-secret")])

class UserProfile(BaseModel):
    preferred_name: str = "Default Name"
    country_of_residence: str = "Default Country"
    age: int = 30
    job_title: str = "Default Job Title"
    job_function: str = "Default Job Function"
    interests: List[str] = ["technology", "science"]
    goals: str = "learn and explore"

class QueryRequest(BaseModel):
    query: str
    user_profile: Optional[UserProfile] = None
    models: List[str] = ["claude-3-opus-20240229"]
    num_urls: int = 20

    @validator('query')
    def ensure_string(cls, value):
        if not isinstance(value, str):
            raise ValueError('Query must be a string')
        return value

@app.function(mounts=[
    Mount.from_local_dir(
        local_path="/Users/erniesg/code/erniesg/shareshare/attn/api/endpoints",
        remote_path="/app/endpoints",
        condition=lambda pth: "query.py" not in pth,
        recursive=True
    )
])
@web_endpoint(method="POST")
async def query(request: QueryRequest):
    import sys
    import os
    import json
    from fastapi.responses import StreamingResponse
    from fastapi import HTTPException
    import logging

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # List files in the current directory and /app directory
    logger.info(f"Files in the current directory: {os.listdir('.')}")
    logger.info(f"Files at root directory: {os.listdir('/')}")
    logger.info(f"Files in the /app directory: {os.listdir('/app')}")
    logger.info(f"Files in the /app/endpoints directory: {os.listdir('/app/endpoints')}")
    logger.info(f"Current working directory: {os.getcwd()}")

    sys.path.insert(0, '/app/endpoints')
    sys.path.insert(0, '/app')
    logger.info(f"Current sys.path: {sys.path}")

    # Importing modules from endpoints
    try:
        from llm_handler import LLMHandler
        from prompts import get_prompts
    except ImportError as e:
        logger.error(f"Failed to import modules from endpoints: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to import required modules")

    try:
        llm_handler = LLMHandler()
        system_prompt, message_prompt = get_prompts("generate_urls", request)
        response_text = llm_handler.call_llm("generate_urls", request)
        urls = parse_urls_from_response(response_text, request.num_urls)

        async def stream_urls():
            yield f"Query received: {request.query}\n"
            yield f"User profile: {json.dumps(request.user_profile.dict())}\n"
            for url in urls:
                yield f"{url}\n"
        return StreamingResponse(stream_urls(), media_type="text/plain")
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def parse_urls_from_response(text: str, num_urls: int) -> List[str]:
    try:
        data = json.loads(text)
        urls = [item['url'] for item in data['urls'][:num_urls]]
        logger.info(f"URLs parsed from response: {urls}")
        return urls
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error parsing URLs from response: {str(e)}")
        # Try to extract URLs using a fallback approach
        urls = extract_urls_fallback(text, num_urls)
        logger.info(f"URLs parsed using fallback approach: {urls}")
        return urls

def extract_urls_fallback(text: str, num_urls: int) -> List[str]:
    # Implement a fallback approach to extract URLs from the text
    # This could involve using regular expressions or other string manipulation techniques
    # to extract the URLs even if the JSON is not properly formatted
    # Example implementation:
    import re
    urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', text)
    return urls[:num_urls]
