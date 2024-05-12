from fastapi import FastAPI, HTTPException, Body, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import asyncio

app = FastAPI()

class QueryInput(BaseModel):
    query: str
    user_profile: Optional[dict] = None
    num_urls: Optional[int] = 20
    custom_prompt: Optional[str] = None

@app.post("/api/query")
async def process_query(input: QueryInput):
    async def event_stream():
        prompt = input.custom_prompt if input.custom_prompt else f"Generate a list of {input.num_urls} URLs related to: {input.query}"
        # Simulate interaction with an LLM
        for i in range(input.num_urls):
            yield f"http://example.com/article{i}\n"
            await asyncio.sleep(0.1)  # Simulate delay

    return StreamingResponse(event_stream(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
