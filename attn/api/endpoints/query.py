from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
from typing import List, Optional
import modal
from modal import Image, App, web_endpoint, Secret
from fastapi.responses import StreamingResponse
import requests
import os
import logging
import anthropic
import json

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

app = App(name="query-app", image=app_image, secrets=[Secret.from_name("my-anthropic-secret")])

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
    models: List[str] = ["claude-3-opus-20240229"]  # Default to Claude Opus model
    num_urls: int = 20
    custom_prompt: Optional[str] = None

    @validator('query')
    def ensure_string(cls, value):
        if not isinstance(value, str):
            raise ValueError('Query must be a string')
        return value

@app.function()
@web_endpoint(method="POST")
async def query(request: QueryRequest):
    try:
        query_text = request.query
        user_profile = request.user_profile or UserProfile()
        urls_response = generate_urls.remote(request)
        return {
            "response": f"Query received: {query_text}",
            "user_profile": user_profile.dict(),
            "urls": urls_response['urls']
        }
    except Exception as e:
        # Log the exception or handle it appropriately
        print(f"Error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.function()
async def generate_urls(request: QueryRequest):
    logger.info(f"Incoming request: {request}")

    prompt = request.custom_prompt or construct_prompt(request)

    logger.info(f"Constructed prompt: {prompt}")

    urls = []
    for model in request.models:
        try:
            response_text = call_llm_api.remote(prompt, model)
            urls.extend(parse_urls_from_response(response_text, request.num_urls))
        except Exception as e:
            logger.error(f"Error calling LLM API with model {model}: {str(e)}")
            continue

    return {"urls": urls}

def construct_prompt(request: QueryRequest) -> str:
    prompt = f"""
Please provide a response in the following structured JSON format:

{{
  "urls": [
    {{
      "url": "https://masterdomain.com"
    }},
    ...
  ]
}}

The "urls" array should contain objects with a single "url" property, representing the master domain URL only. Do not include any other properties like title or source.

Return a list of {request.num_urls} URLs relevant to the query '{request.query}' for a user with the following profile:
- Preferred Name: {request.user_profile.preferred_name if request.user_profile else 'Default Name'}
- Country of Residence: {request.user_profile.country_of_residence if request.user_profile else 'Default Country'}
- Age: {request.user_profile.age if request.user_profile else 30}
- Job Title: {request.user_profile.job_title if request.user_profile else 'Default Job Title'}
- Job Function: {request.user_profile.job_function if request.user_profile else 'Default Job Function'}
- Interests: {request.user_profile.interests if request.user_profile else ['technology', 'science']}
- Goals: {request.user_profile.goals if request.user_profile else 'learn and explore'}

The URLs should be relevant for a personalized news digest based on the user's profile and query.

Always respond with a structured, valid JSON, adhering strictly to the provided example format. Do not include any other text or explanations outside of the JSON structure.
"""
    logger.info(f"Constructed prompt: {prompt}")
    return prompt

@app.function(secrets=[modal.Secret.from_name("my-anthropic-secret")])
async def call_llm_api(prompt: str, model: str):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    try:
        # Use the streaming API
        with client.messages.stream(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            content = []
            for text in stream.text_stream:
                content.append(text)
                logger.info(f"Streaming text: {text}")

        full_content = ''.join(content)
        logger.info(f"LLM API request completed with completed response: {full_content}")
        logger.info(f"Type of response from LLM: {type(full_content)}")  # Log the type of the response
        return full_content
    except Exception as e:
        logger.error(f"LLM API call failed: {str(e)}")
        raise HTTPException(status_code=500, detail="LLM API call failed")

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
