# This module manages different types of prompts.

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
    "other_function": {
        "message_prompt": "Some other prompt without a system prompt."
    }
}

def get_prompts(function_name, request):
    system_prompt = prompts[function_name].get("system_prompt", "")
    message_prompt = prompts[function_name]["message_prompt"].format(
        num_urls=request.num_urls,
        query=request.query,
        preferred_name=request.user_profile.preferred_name,
        country_of_residence=request.user_profile.country_of_residence,
        age=request.user_profile.age,
        job_title=request.user_profile.job_title,
        job_function=request.user_profile.job_function,
        interests=request.user_profile.interests,
        goals=request.user_profile.goals
    )
    return system_prompt, message_prompt
