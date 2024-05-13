import sys
sys.path.insert(0, '../')
sys.path.insert(0, '.')
sys.path.insert(0, '/Users/erniesg/code/erniesg/shareshare/attn/api')

from fastapi import FastAPI
from endpoints.query_v2 import router as query_v2_router
from endpoints.read import router as read_router
from modal import App, Image, Secret

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the Docker image with necessary dependencies
app_image = Image.debian_slim(python_version="3.10").pip_install("requests", "anthropic")

# Create the Modal app instance
modal_app = App(name="query-app", image=app_image, secrets=[Secret.from_name("my-anthropic-secret")])

# Create the FastAPI instance
app = FastAPI()

# Include routers
app.include_router(query_v2_router)
app.include_router(read_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
