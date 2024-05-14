import logging
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import torch

logger = logging.getLogger(__name__)

class EmbeddingHandler:
    def __init__(self, default_model="Alibaba-NLP/gte-large-en-v1.5", huggingface_token=None):
        self.default_model = default_model
        self.huggingface_token = huggingface_token

    def generate_embedding(self, text, model=None, task=None):
        model = model or self.default_model
        device = "cuda" if torch.cuda.is_available() else "cpu"
        embed_model = HuggingFaceEmbedding(model_name=model, token=self.huggingface_token, device=device, trust_remote_code=True)

        if task:
            text = f"Instruct: {task}\nQuery: {text}"

        try:
            embedding = embed_model.get_text_embedding(text)
            logger.info(f"Generated embedding for text: {text[:30]}... with model: {model} on device: {device}")  # Log the first 30 characters
            return embedding, model
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise Exception(f"Embedding generation failed: {str(e)}")
