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
    }
}

def get_prompts(function_name, request, **kwargs):
    logger.info(f"Get Prompts - Received kwargs in get_prompts: {kwargs}")  # Log the contents of kwargs

    system_prompt = prompts[function_name].get("system_prompt", "")
    logger.info(f"Formatting message_prompt with: num_urls={request.num_urls}, query={request.query}, preferred_name={request.user_profile.preferred_name}, country_of_residence={request.user_profile.country_of_residence}, age={request.user_profile.age}, job_title={request.user_profile.job_title}, job_function={request.user_profile.job_function}, interests={request.user_profile.interests}, goals={request.user_profile.goals}")
    message_prompt = prompts[function_name]["message_prompt"].format(
        num_urls=request.num_urls,
        query=request.query,
        preferred_name=request.user_profile.preferred_name,
        country_of_residence=request.user_profile.country_of_residence,
        age=request.user_profile.age,
        job_title=request.user_profile.job_title,
        job_function=request.user_profile.job_function,
        interests=request.user_profile.interests,
        goals=request.user_profile.goals,
        **kwargs  # This will unpack any additional keyword arguments into the format string
    )
    return system_prompt, message_prompt
