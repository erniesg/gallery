import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
import os
print("Current directory:", os.getcwd())
print("Directory contents:", os.listdir('.'))
import sys
sys.path.insert(0, '/Users/erniesg/code/erniesg/shareshare/attn/api')
logger.info(f"Current sys.path: {sys.path}")

from fastapi import FastAPI
from endpoints.query_v2 import router as query_v2_router
from endpoints.read import router as read_router
from modal import App, Image, Secret, Mount


# Define the Docker image with necessary dependencies
app_image = Image.debian_slim(python_version="3.10").pip_install("requests", "anthropic")

# Create the Modal app instance
modal_app = App(name="query-app", image=app_image, secrets=[Secret.from_name("my-anthropic-secret")])

@modal_app.function(mounts=[
    Mount.from_local_dir(
        local_path="/Users/erniesg/code/erniesg/shareshare/attn/api/endpoints",
        remote_path="/app/endpoints",
        condition=lambda pth: "app.py" not in pth,
        recursive=True
    )
])

# @modal_app.function
# logger.info(f"Files in the current directory: {os.listdir('.')}")
# logger.info(f"Files at root directory: {os.listdir('/')}")
# logger.info(f"Files in the /app directory: {os.listdir('/app')}")
# logger.info(f"Files in the /app/endpoints directory: {os.listdir('/app/endpoints')}")
# logger.info(f"Current working directory: {os.getcwd()}")

# sys.path.insert(0, '/app/endpoints')
# sys.path.insert(0, '/app')
# logger.info(f"Current sys.path: {sys.path}")

@modal_app.local_entrypoint()
def main():
    import uvicorn
    # Create the FastAPI instance
    app = FastAPI()

    # Include routers
    app.include_router(query_v2_router)
    app.include_router(read_router)
    uvicorn.run(app, host="0.0.0.0", port=8000)
