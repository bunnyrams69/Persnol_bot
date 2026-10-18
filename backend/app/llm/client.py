import json
import logging
import httpx
from app.database.connection import settings

logger = logging.getLogger("life_os.llm")

def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Sends a request to the LLM / MiniMax API (OpenAI compatible endpoint).
    If the API key is set to a placeholder, returns mock JSON responses to allow offline testing.
    """
    api_key = settings.MINIMAX_API_KEY
    is_placeholder = (
        not api_key or
        api_key == "your_minimax_api_key_here" or
        "your_" in api_key
    )
    
def _generate_mock_response(system_prompt: str, user_prompt: str) -> str:
    """Generates intelligent offline mock responses matching system instructions."""
    sys_lower = system_prompt.lower()
    
    if "task extractor" in sys_lower:
        return json.dumps({
            "title": user_prompt.strip()[:50],
            "description": f"Extracted from: '{user_prompt}'",
            "priority": "high" if any(x in user_prompt.lower() for x in ["urgent", "deadline", "soon", "by"]) else "medium",
            "suggested_type": "deadline" if "reel" in user_prompt.lower() or "client" in user_prompt.lower() else "dsa" if "dsa" in user_prompt.lower() else "agency" if "agency" in user_prompt.lower() else "personal"
        })
        
    elif "weekly review" in sys_lower:
        return json.dumps({
            "type": "weekly_review",
            "wins": ["Gym streak 7/7", "AI Agency outreach completed (80% score)"],
            "losses": ["DSA practice skipped 3 times due to client reel stress"],
            "coach_feedback": "[MOCK COACH] You're putting off DSA. It's a priority issue. Solve it by scheduling DSA in the mornings when your energy is 5.",
            "new_patterns": [
                {
                    "pattern": "Skips DSA practice after heavy client work",
                    "confidence": 0.85,
                    "evidence": "Skipped DSA on Tue and Thu immediately following editing sessions."
                }
            ]
        })
        
    elif "long-term memory manager" in sys_lower:
        return json.dumps({
            "profile_updates": [],
            "new_beliefs": [],
            "new_patterns": []
        })
        
    else:
        # Mock night review conversation
        user_lower = user_prompt.lower()
        if "approve" in user_lower or "looks good" in user_lower:
            return json.dumps({
              "type": "coach_response",
              "coach_message": "[MOCK COACH] Perfect. Schedule approved. Let's make tomorrow count.",
              "actions": [],
              "negotiation_complete": True
            })
        else:
            pattern_challenge = ""
            if "historically skips" in sys_lower or "pattern alert" in sys_lower:
                pattern_challenge = " I noticed from your history that you repeatedly skip key sessions on this weekday. Let's not make the same mistake tomorrow."
            else:
                pattern_challenge = " But you've skipped priority sessions before."

            return json.dumps({
              "type": "coach_response",
              "coach_message": f"[MOCK COACH] I hear your suggestion: '{user_prompt}'.{pattern_challenge} I recommend moving DSA to 8 AM to guarantee you execute before fatigue hits. Approve?",
              "actions": [
                {
                  "action": "move",
                  "block_title": "📘 DSA Practice",
                  "planned_start": "08:00:00",
                  "planned_end": "09:00:00",
                  "reason": "Moved to morning slot by coach recommendation to prevent skipping"
                }
              ],
              "negotiation_complete": False
            })


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Sends a request to the LLM / MiniMax API (OpenAI compatible endpoint).
    If the API key is a placeholder or returns errors (no credits / offline),
    returns intelligent structured mock responses to ensure zero-downtime demos.
    """
    api_key = settings.MINIMAX_API_KEY
    is_placeholder = (
        not api_key or
        api_key == "your_minimax_api_key_here" or
        "your_" in api_key
    )
    
    if is_placeholder:
        logger.warning("MINIMAX_API_KEY is placeholder. Running in MOCK Mode.")
        return _generate_mock_response(system_prompt, user_prompt)

    # Actual MiniMax API call (OpenAI compatible format)
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": settings.MODEL_NAME or "abab6.5g-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1
        }
        
        logger.info(f"Calling MiniMax API (Model: {payload['model']})...")
        
        with httpx.Client() as client:
            response = client.post(
                "https://api.minimax.io/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            raise ValueError(f"HTTP {response.status_code}: {response.text}")
            
    except Exception as e:
        logger.warning(f"MiniMax API unavailable ({e}). Falling back to intelligent mock response.")
        return _generate_mock_response(system_prompt, user_prompt)

# Backwards compatibility alias
call_claude = call_llm

