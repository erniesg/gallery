# This module manages different types of prompts.
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
prompts = {
    "generate_urls": {
        "system_prompt": "Always respond with a structured, valid JSON, adhering strictly to the provided example format. Do not include any other text or explanations outside of the JSON structure.",
        "message_prompt": """
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

        Return a list of {num_urls} news and publications URLs relevant to the query '{query}' for a user with the following profile:
        - Preferred Name: {preferred_name}
        - Country of Residence: {country_of_residence}
        - Age: {age}
        - Job Title: {job_title}
        - Job Function: {job_function}
        - Interests: {interests}
        - Goals: {goals}

        The URLs should be relevant for a personalized news digest based on the user's profile and query.

        """
    },
    "extract_article_urls": {
        "system_prompt": "Always respond with a structured, valid JSON, adhering strictly to the provided example format. Do not include any other text or explanations outside of the JSON structure.",
        "message_prompt": """
        Analyze the following article metadata and content to extract relevant article URLs:

        URL: {url}
        Title: {title}
        Keywords: {keywords}
        Description: {description}
        Content: {content}

        Return a list of {num_urls} article URLs from the content that is relevant to the topics '{query}' for a user with the following profile:
        - Preferred Name: {preferred_name}
        - Country of Residence: {country_of_residence}
        - Age: {age}
        - Job Title: {job_title}
        - Job Function: {job_function}
        - Interests: {interests}
        - Goals: {goals}

        Please provide a response in the following structured JSON format:

        {{
          "parent_url": {url},
          "article_urls": [
            {{
              "url": "https://masterdomain.com/section/article1link"
            }},
            ...
          ]
        }}

        The URLs should be relevant for a personalized news digest based on the user's profile and the topics of interest.
        """
    },
    "extract_structure": {
        "system_prompt": "Always respond with a structured, valid JSON, adhering strictly to the provided example format. Do not include any other text or explanations outside of the JSON structure.",
        "message_prompt": """
        Extract the following structured information from the article content:

        URL: {url}
        Title: {title}
        Keywords: {keywords}
        Description: {description}
        Content: {content}

        Use the `extract_structure` tool to extract the following information:
        - Author: Extract the author of the article.
        - Published Date: Extract the published date of the article.
        - Entities: Extract entities mentioned in the article, categorized by type and value.
        - Location: Extract locations mentioned in the article using ISO3 codes.
        - Main Idea: Extract the main idea of the article.
        - Assertions: Extract assertions made in the article, categorized by type and value.
        - Summary: Provide a brief summary of the article.

        Provide the response in the following structured JSON format:

        {{
          "author": "",
          "published_date": "",
          "entities": [
            {{
              "type": "",
              "value": ""
            }},
            ...
          ],
          "location": "",
          "main_idea": "",
          "assertions": [
            {{
              "type": "",
              "value": ""
            }},
            ...
          ],
          "summary": ""
        }}
        """
    },
    "score_article": {
        "system_prompt": "Always respond with a structured, valid JSON, adhering strictly to the provided example format. Do not include any other text or explanations outside of the JSON structure.",
        "message_prompt": """
        Use the `score_article` tool to score the following article content based on the provided topics on a scale of 0-1:

        URL: {url}
        Title: {title}
        Keywords: {keywords}
        Description: {description}
        Content: {content}

        Topics to score:
        {topics}

        Provide the response in the following structured JSON format:

        {{
        "url": "{url}",
        "scores": {{
        }}
        }}
        """
    }
}

def get_prompts(function_name, request, **kwargs):
    logger.info(f"Get Prompts - Received request {request} with kwargs: {kwargs}")  # Log the contents of kwargs

    system_prompt = prompts[function_name].get("system_prompt", "")

    # List of possible attributes to check
    possible_attributes = [
        "num_urls", "query", "preferred_name", "country_of_residence", "age",
        "job_title", "job_function", "interests", "goals", "topics"
    ]

    # Prepare a dictionary with all possible parameters
    params = {}
    for attr in possible_attributes:
        if hasattr(request, attr):
            params[attr] = getattr(request, attr)
        elif hasattr(request, "user_profile") and hasattr(request.user_profile, attr):
            params[attr] = getattr(request.user_profile, attr)

    # Include additional keyword arguments
    params.update(kwargs)

    # Filter out None values
    params = {k: v for k, v in params.items() if v is not None}

    logger.debug(f"Formatted parameters for prompt: {params}")

    try:
        message_prompt = prompts[function_name]["message_prompt"].format(**params)
    except KeyError as e:
        logger.error(f"Missing key in parameters for formatting: {e}")
        raise
    except Exception as e:
        logger.error(f"Error formatting message prompt: {e}")
        raise

    return system_prompt, message_prompt
