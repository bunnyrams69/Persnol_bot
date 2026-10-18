import json
import os
import logging
from app.llm.client import call_llm

logger = logging.getLogger("life_os.llm")

# Resolve prompts directory
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")

def get_prompt_content(filename: str) -> str:
    """Helper to read prompt files."""
    filepath = os.path.join(PROMPTS_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def extract_inbox_item(raw_message: str) -> dict:
    """
    Extracts structured task details (title, description, priority, suggested_type)
    from a raw message string using Claude.
    """
    try:
        system_prompt = get_prompt_content("task_extraction.md")
    except Exception as e:
        logger.error(f"Failed to read task_extraction.md: {e}")
        system_prompt = "You are the Task Extractor. Output JSON with title, description, priority, and suggested_type."
        
    response_text = call_llm(system_prompt, raw_message)
    
    # Strip any markdown json formatting if Claude accidentally added it
    response_text = response_text.replace("```json", "").replace("```", "").strip()
    
    try:
        data = json.loads(response_text)
        return {
            "title": data.get("title", raw_message[:50]),
            "description": data.get("description", raw_message),
            "priority": data.get("priority", "medium").lower(),
            "suggested_type": data.get("suggested_type", "personal").lower(),
            "raw_response": response_text
        }
    except Exception as e:
        logger.error(f"Failed to parse Claude extraction JSON: {e}. Raw response: {response_text}")
        return {
            "title": raw_message[:50],
            "description": raw_message,
            "priority": "medium",
            "suggested_type": "personal",
            "raw_response": response_text
        }
