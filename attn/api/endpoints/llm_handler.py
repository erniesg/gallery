import sys
sys.path.append('/Users/erniesg/code/erniesg/shareshare/attn/api/')
from endpoints.prompts import get_prompts
import anthropic
import os
import logging

logger = logging.getLogger(__name__)

class LLMHandler:
    def __init__(self, api_key=None):
        self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    def call_llm(self, function_name, request, model_name=None, **kwargs):
        logger.info(f"LLM Handler - Received kwargs in call_llm: {kwargs}")  # Log the contents of kwargs

        system_prompt, message_prompt = get_prompts(function_name, request, **kwargs)
        # Log the prompts being sent to the LLM
        logger.info(f"System Prompt: {system_prompt}")
        logger.info(f"Message Prompt: {message_prompt}")
        model_to_use = model_name if model_name else request.models[0]

        try:
            # Always use the streaming API
            with self.client.messages.stream(
                model=model_to_use,
                max_tokens=1000,
                messages=[{"role": "user", "content": message_prompt}],
                system=system_prompt if system_prompt else None  # Pass system prompt if available
            ) as stream:
                content = []
                for text in stream.text_stream:
                    content.append(text)
                    logger.info(f"Streaming text: {text}")
            full_content = ''.join(content)
            logger.info(
                f"LLM API request completed with completed response: {full_content}"
                f"\nResponse type: {type(full_content)}"
            )
            return full_content
        except Exception as e:
            logger.error(f"LLM API call failed: {str(e)}")
            raise Exception(f"LLM API call failed: {str(e)}")
