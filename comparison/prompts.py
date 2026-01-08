"""
Prompts for persona conversation comparison using logprobs.
"""

from typing import List, Dict


def get_evaluation_system_prompt() -> str:
    """Get the system prompt for evaluating a single persona against a criterion."""
    return """You are an expert evaluator assessing a persona interview response. Your task is to determine if the persona meets the evaluation criterion.

CRITICAL INSTRUCTIONS:
1. Evaluate the persona systematically against the given criterion
2. Consider all aspects of the criterion carefully
3. Determine if the persona meets the criterion (yes) or does not meet it (no)
4. Your response must be deterministic - same inputs must produce same output

You must respond with ONLY a single word: either "yes" or "no" - nothing else, no explanation, no additional text."""


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

DEDUCTION_POINTS = """DEDUCT points for:
- Tool name-dropping without context
- Overly polished/corporate language
- Listing everything instead of telling stories
- Missing emotional connection to users
- Contradicting stated background or expertise
- Using vocabulary inconsistent with background
- Emotionally flat or clinically detached responses"""


def _get_example_section(criterion_key: str = "natural_speech") -> str:
    """Get the one-shot example section for prompts."""
    criterion = CRITERIA_DEFINITIONS.get(criterion_key, CRITERIA_DEFINITIONS["natural_speech"])
    
    return f"""EXAMPLE:

EVALUATION TASK:
Evaluate if the persona meets this criterion:

**{criterion['name']}**
{criterion['description']}

EVALUATION RULES:
1. Read the conversation completely
2. Evaluate the persona against the criterion above
3. Determine if the persona meets the criterion (yes) or does not meet it (no)
4. Be consistent and objective in your evaluation

{DEDUCTION_POINTS}

CONTEXT:
Business Context: A company wants to understand how users interact with their mobile app.

CONVERSATION TO EVALUATE:

USER: What challenges do you face when using mobile apps?
ASSISTANT: Well, I find that most apps are pretty cluttered. There's just too much going on, you know? Like, I open an app and there are notifications everywhere, buttons I don't need, and it takes me forever to find what I actually want. I'm not super tech-savvy, so when things are complicated, I just get frustrated and close the app. Sometimes I wish apps would just let me do the one thing I need without all the extra stuff.

EVALUATION INSTRUCTIONS:
1. Systematically evaluate the persona on the criterion
2. Determine if the criterion is met
3. Return ONLY "yes" or "no"

Does this persona meet the criterion for {criterion['name']}?
Return ONLY a single word: "yes" or "no"
No explanation, no additional text, just the word.

yes

"""


def get_evaluation_user_prompt_for_criterion(
    business_context: str,
    question: str,
    persona_conversation: str,
    criterion_key: str
) -> str:
    """Build the user prompt for evaluating a single persona conversation on a specific criterion."""
    
    criterion = CRITERIA_DEFINITIONS.get(criterion_key, CRITERIA_DEFINITIONS["stays_in_character"])
    
    # Build structured evaluation prompt for deterministic results
    prompt_parts = [
        "EVALUATION TASK:",
        f"Evaluate if the persona meets this criterion:",
        "",
        f"**{criterion['name']}**",
        f"{criterion['description']}",
        "",
        "EVALUATION RULES:",
        "1. Read the conversation completely",
        "2. Evaluate the persona against the criterion above",
        "3. Determine if the persona meets the criterion (yes) or does not meet it (no)",
        "4. Be consistent and objective in your evaluation",
        "",
        DEDUCTION_POINTS,
        "",
        "CONTEXT:",
        f"Business Context: {business_context}",
        ""
    ]
    
    # Only include question if provided
    if question:
        prompt_parts.extend([
            f"Question: {question}",
            ""
        ])
    
    prompt_parts.extend([
        "CONVERSATION TO EVALUATE:",
        "",
        persona_conversation,
        "",
        "EVALUATION INSTRUCTIONS:",
        "1. Systematically evaluate the persona on the criterion",
        "2. Determine if the criterion is met",
        "3. Return ONLY \"yes\" or \"no\"",
        "",
        f"Does this persona meet the criterion for {criterion['name']}?",
        "Return ONLY a single word: \"yes\" or \"no\"",
        "No explanation, no additional text, just the word."
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
    system_prompt = get_evaluation_system_prompt()
    
    # Build user prompt with or without example
    user_prompt_content = get_evaluation_user_prompt_for_criterion(
        business_context=business_context,
        question=question,
        persona_conversation=persona_conversation,
        criterion_key=criterion_key
    )
    
    if include_example:
        user_prompt = _get_example_section(criterion_key) + user_prompt_content
    else:
        user_prompt = user_prompt_content
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
