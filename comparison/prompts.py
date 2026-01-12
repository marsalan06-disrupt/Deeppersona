"""
Prompts for persona conversation comparison using logprobs.
"""

from typing import List, Dict


def get_evaluation_system_prompt(criterion_key: str) -> str:
    """Get the system prompt for evaluating a single persona against a criterion.
    
    Args:
        criterion_key: The key identifying which criterion to evaluate against
    """
    criterion = CRITERIA_DEFINITIONS.get(criterion_key, CRITERIA_DEFINITIONS["stays_in_character"])
    
    return f"""You are an expert evaluator specializing in persona assessment. Your role is to systematically analyze persona interview responses and determine whether they meet specific evaluation criteria.

TASK:
Evaluate whether a persona conversation meets the following evaluation criterion by analyzing the conversation systematically and objectively.

EVALUATION CRITERION:
{criterion['name']}

{criterion['description']}

EVALUATION RULES:
1. Read the conversation completely and carefully
2. Evaluate the persona systematically against the criterion above
3. Consider all aspects of the criterion description and red flags
4. Determine if the persona meets the criterion (yes) or does not meet it (no)
5. Be consistent and objective in your evaluation
6. Your response must be deterministic - same inputs must produce same output

DEDUCT POINTS FOR:
- Tool name-dropping without context
- Overly polished/corporate language
- Listing everything instead of telling stories
- Missing emotional connection to users
- Contradicting stated background or expertise
- Using vocabulary inconsistent with background
- Emotionally flat or clinically detached responses

INPUT FORMAT:
You will receive:
- BUSINESS CONTEXT: The business context or research goal for this evaluation
- CONVERSATION: The full conversation history with questions and answers

OUTPUT FORMAT:
You must respond with ONLY a single word: either "yes" or "no"
- "yes" if the persona meets the criterion
- "no" if the persona does not meet the criterion
- Nothing else, no explanation, no additional text, just the word."""


# Define individual criteria
CRITERIA_DEFINITIONS = {
    # Persona Fidelity
    "stays_in_character": {
        "name": "Stays in character",
        "category": "persona_fidelity",
        "description": "Stays consistent with their stated background (demographics, occupation, experience level).\n\nRed flags:\n- Contradicts their stated background\n- Claims expertise inconsistent with their profile"
    },
    "authentic_vocabulary": {
        "name": "Authentic vocabulary",
        "category": "persona_fidelity",
        "description": "Uses vocabulary and references that match their stated background.\n\nRed flags:\n- Uses jargon inconsistent with their expertise level\n- References tools/concepts they wouldn't realistically know"
    },
    
    # Human Authenticity - Speech Patterns
    "natural_speech": {
        "name": "Natural speech",
        "category": "human_authenticity",
        "description": "Sounds like natural spoken conversation (uses contractions, filler words, self-corrections).\n\nRed flags:\n- Overly formal or polished language\n- Perfect grammar throughout\n- No conversational hedges"
    },
    "tells_stories": {
        "name": "Tells stories",
        "category": "human_authenticity",
        "description": "Tells specific personal anecdotes rather than speaking in generalities.\n\nRed flags:\n- Speaks only in abstract terms\n- Lists features/problems without personal context\n- No 'I remember when...' moments"
    },
    "admits_uncertainty": {
        "name": "Admits uncertainty",
        "category": "human_authenticity",
        "description": "Naturally admits when they don't know something or aren't sure.\n\nRed flags:\n- Claims certainty about everything\n- Never says 'I'm not sure' or 'I think'\n- Presents opinions as facts"
    },
    "shows_emotion": {
        "name": "Shows emotion",
        "category": "human_authenticity",
        "description": "Expresses genuine emotional reactions (frustration, excitement, confusion).\n\nRed flags:\n- Emotionally flat responses\n- Describes feelings clinically\n- No passion or frustration evident"
    },
    
    # Human Authenticity - Anti-AI Signals
    "avoids_lists": {
        "name": "Avoids lists",
        "category": "human_authenticity",
        "description": "Avoids bullet-point thinking and speaks in natural flowing sentences.\n\nRed flags:\n- Structures response like a report\n- Enumerates points (first, second, third)\n- Uses bullet-point cadence"
    },
    "no_buzzwords": {
        "name": "No buzzwords",
        "category": "human_authenticity",
        "description": "Avoids corporate buzzwords and AI-typical phrasing.\n\nRed flags:\n- Uses 'leverage', 'utilize', 'optimize'\n- Says 'I would say that...'\n- Overly balanced/hedged statements"
    },
    
    # Psychological Depth
    "explains_why": {
        "name": "Explains why",
        "category": "psychological_depth",
        "description": "Better explains WHY they feel or behave a certain way, not just WHAT they do.\n\nRed flags:\n- States preferences without reasoning\n- No self-reflection on motivations\n- Surface-level answers"
    },
    "shows_growth": {
        "name": "Shows growth",
        "category": "psychological_depth",
        "description": "Shows evidence of learning or changing their mind from past experiences.\n\nRed flags:\n- Static viewpoints\n- No 'I used to think X but now...'\n- Doesn't reference past mistakes or lessons"
    },
    "acknowledges_tradeoffs": {
        "name": "Acknowledges tradeoffs",
        "category": "psychological_depth",
        "description": "Acknowledges complexity, downsides, or trade-offs in their views.\n\nRed flags:\n- Everything is black and white\n- No 'on the other hand...'\n- Unrealistically positive or negative"
    },
    
    # Relevance & Focus
    "answers_question": {
        "name": "Answers question",
        "category": "relevance_focus",
        "description": "More directly answers the actual question that was asked.\n\nRed flags:\n- Goes off on tangents\n- Provides information not requested\n- Buries the answer"
    },
    "appropriate_length": {
        "name": "Appropriate length",
        "category": "relevance_focus",
        "description": "Response length feels more natural for the question asked.\n\nRed flags:\n- Over-explains simple questions\n- Under-explains complex ones\n- Exhaustive when brief would suffice"
    }
}

# Group criteria by category for batch evaluation
CATEGORIES = {
    "persona_fidelity": ["stays_in_character", "authentic_vocabulary"],
    "human_authenticity": ["natural_speech", "tells_stories", "admits_uncertainty", "shows_emotion", "avoids_lists", "no_buzzwords"],
    "psychological_depth": ["explains_why", "shows_growth", "acknowledges_tradeoffs"],
    "relevance_focus": ["answers_question", "appropriate_length"]
}



def _get_example_section() -> str:
    """Get the one-shot example section for prompts."""
    return """EXAMPLE:

BUSINESS CONTEXT:
A company wants to understand how users interact with their mobile app.

CONVERSATION:

QUESTION: What challenges do you face when using mobile apps?
ANSWER: Well, I find that most apps are pretty cluttered. There's just too much going on, you know? Like, I open an app and there are notifications everywhere, buttons I don't need, and it takes me forever to find what I actually want. I'm not super tech-savvy, so when things are complicated, I just get frustrated and close the app. Sometimes I wish apps would just let me do the one thing I need without all the extra stuff.

yes

---
"""


def get_evaluation_user_prompt_for_criterion(
    business_context: str,
    question: str,
    persona_conversation: str,
    criterion_key: str
) -> str:
    """Build the user prompt for evaluating a single persona conversation on a specific criterion.
    
    User prompt contains ONLY the inputs: business context and conversation.
    All instructions and criterion details are in the system prompt.
    """
    
    # Build user prompt with only inputs, separated by clear sections
    prompt_parts = [
        "BUSINESS CONTEXT:",
        business_context,
        ""
    ]
    
    # Only include question if provided
    if question:
        prompt_parts.extend([
            "---",
            "",
            "QUESTION:",
            question,
            ""
        ])
    
    prompt_parts.extend([
        "---",
        "",
        "CONVERSATION:",
        "",
        persona_conversation
    ])
    
    return "\n".join(prompt_parts)


def get_evaluation_messages_for_criterion(
    business_context: str,
    question: str,
    persona_conversation: str,
    criterion_key: str,
    include_example: bool = True
) -> List[Dict[str, str]]:
    """Build the messages array for evaluating a single persona conversation on a specific criterion."""
    system_prompt = get_evaluation_system_prompt(criterion_key)
    
    # Build user prompt with or without example
    user_prompt_content = get_evaluation_user_prompt_for_criterion(
        business_context=business_context,
        question=question,
        persona_conversation=persona_conversation,
        criterion_key=criterion_key
    )
    
    if include_example:
        user_prompt = _get_example_section() + user_prompt_content
    else:
        user_prompt = user_prompt_content
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
