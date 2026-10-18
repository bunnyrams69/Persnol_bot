import json
import logging
from sqlalchemy.orm import Session
from app.database.models import MemoryProfile, MemoryBelief, MemoryPattern, MemoryGoal
from app.llm.client import call_llm
from app.llm.extractor import get_prompt_content

logger = logging.getLogger("life_os.llm")

def get_user_memory_context(db: Session, user_id: int) -> str:
    """
    Fetches all memory records for a user and formats them into a text block
    to inject into Claude's system prompt.
    """
    profiles = db.query(MemoryProfile).filter(MemoryProfile.user_id == user_id).all()
    beliefs = db.query(MemoryBelief).filter(MemoryBelief.user_id == user_id, MemoryBelief.status == "active").all()
    patterns = db.query(MemoryPattern).filter(MemoryPattern.user_id == user_id).all()
    goals = db.query(MemoryGoal).filter(MemoryGoal.user_id == user_id, MemoryGoal.status == "active").all()
    
    lines = []
    
    # 1. Profile
    lines.append("### Persistent Profile Facts:")
    if profiles:
        for p in profiles:
            lines.append(f"- {p.key}: {p.value}")
    else:
        lines.append("- No profile facts recorded yet.")
        
    # 2. Beliefs
    lines.append("\n### Stated Beliefs & Mindsets:")
    if beliefs:
        for b in beliefs:
            lines.append(f"- {b.belief}")
    else:
        lines.append("- No core beliefs recorded yet.")
        
    # 3. Patterns
    lines.append("\n### Detected Behavioral Patterns:")
    if patterns:
        for pat in patterns:
            lines.append(f"- {pat.pattern} (Confidence: {pat.confidence*100:.0f}%, Evidence: {pat.evidence})")
    else:
        lines.append("- No patterns detected yet.")
        
    # 4. Goals
    lines.append("\n### Long-Term Goals:")
    if goals:
        for g in goals:
            deadline_str = f" (Deadline: {g.deadline.strftime('%Y-%m-%d')})" if g.deadline else ""
            lines.append(f"- {g.goal}{deadline_str} [Priority: {g.priority}]")
    else:
        lines.append("- No active goals recorded.")
        
    return "\n".join(lines)


def process_memory_updates(db: Session, user_id: int, source_text: str):
    """
    Sends the source text (e.g. weekly review or coaching summary) to Claude,
    extracts memory updates, and commits them to the database.
    """
    try:
        system_prompt = get_prompt_content("memory_update.md")
    except Exception as e:
        logger.error(f"Failed to read memory_update.md: {e}")
        return
        
    response_text = call_llm(system_prompt, source_text)
    response_text = response_text.replace("```json", "").replace("```", "").strip()
    
    try:
        updates = json.loads(response_text)
        
        # 1. Profile updates
        for prof in updates.get("profile_updates", []):
            key = prof.get("key")
            value = prof.get("value")
            if key and value:
                # Upsert key
                record = db.query(MemoryProfile).filter(
                    MemoryProfile.user_id == user_id,
                    MemoryProfile.key == key
                ).first()
                if record:
                    record.value = value
                else:
                    record = MemoryProfile(user_id=user_id, key=key, value=value)
                    db.add(record)
                    
        # 2. Belief updates
        for belief_text in updates.get("new_beliefs", []):
            # Avoid duplicating active identical beliefs
            exists = db.query(MemoryBelief).filter(
                MemoryBelief.user_id == user_id,
                MemoryBelief.belief == belief_text,
                MemoryBelief.status == "active"
            ).first()
            if not exists:
                new_b = MemoryBelief(user_id=user_id, belief=belief_text, status="active")
                db.add(new_b)
                
        # 3. Pattern updates
        for pat in updates.get("new_patterns", []):
            pattern_text = pat.get("pattern")
            confidence = pat.get("confidence", 0.5)
            evidence = pat.get("evidence", "")
            
            if pattern_text:
                # Check if pattern already noted, update confidence and evidence
                exists = db.query(MemoryPattern).filter(
                    MemoryPattern.user_id == user_id,
                    MemoryPattern.pattern == pattern_text
                ).first()
                if exists:
                    # Keep the higher confidence or average them
                    exists.confidence = max(exists.confidence, confidence)
                    if evidence:
                        exists.evidence = (exists.evidence or "") + " | " + evidence
                else:
                    new_pat = MemoryPattern(
                        user_id=user_id,
                        pattern=pattern_text,
                        confidence=confidence,
                        evidence=evidence
                    )
                    db.add(new_pat)
                    
        db.commit()
        logger.info("Long-term memory successfully updated in database.")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to process and save memory updates: {e}. Raw response was: {response_text}")
