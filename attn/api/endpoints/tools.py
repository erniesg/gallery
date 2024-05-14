# tools.py

tools = [
    {
        "name": "extract_structure",
        "description": "Extracts structured information from the article content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "author": {"type": "string", "description": "Name of the article author"},
                "published_date": {"type": "string", "description": "Published date of the article"},
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "description": "Type of entity"},
                            "value": {"type": "string", "description": "Entity value"}
                        }
                    },
                    "description": "Array of entities with type and value"
                },
                "location": {"type": "string", "description": "Location in ISO3 code"},
                "main_idea": {"type": "string", "description": "Main idea of the article"},
                "assertions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "description": "Type of assertion"},
                            "value": {"type": "string", "description": "Assertion value"}
                        }
                    },
                    "description": "Array of assertions with type and value"
                },
                "summary": {"type": "string", "description": "Summary of the article"}
            },
            "required": ["author", "published_date", "entities", "location", "main_idea", "assertions", "summary"]
        }
    },
    {
        "name": "score_article",
        "description": "Scores the article content based on predefined topics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL of the article"},
                "title": {"type": "string", "description": "Title of the article"},
                "keywords": {"type": "array", "items": {"type": "string"}, "description": "Keywords associated with the article"},
                "description": {"type": "string", "description": "Description of the article"},
                "content": {"type": "string", "description": "Content of the article"},
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of topics to score the article on"
                }
            },
            "required": ["url", "title", "keywords", "description", "content", "topics"]
        }
    }
]
