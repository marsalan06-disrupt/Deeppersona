"""
Prompts for persona conversation comparison using logprobs.
"""

from typing import List, Dict


def get_evaluation_system_prompt(criterion_key: str, use_personalization_criteria: bool = False) -> str:
    """Get the system prompt for evaluating a single persona against a criterion.
    
    Args:
        criterion_key: The key identifying which criterion to evaluate against
        use_personalization_criteria: If True, use personalization criteria (numeric 1-5 scoring).
                                     If False, use persona authenticity criteria (binary yes/no).
    """
    if use_personalization_criteria:
        criteria_dict = PERSONALIZATION_CRITERIA_DEFINITIONS
        default_key = "personalization_fit"
    else:
        criteria_dict = CRITERIA_DEFINITIONS
        default_key = "stays_in_character"
    
    criterion = criteria_dict.get(criterion_key, criteria_dict[default_key])
    
    if use_personalization_criteria:
        # Personalization criteria: numeric scoring (1-5)
        return f"""You are an expert evaluator specializing in personalized advice assessment. Your role is to systematically analyze how well advice or responses are tailored to a specific user persona profile.

TASK:
Evaluate how well the advice/responses in the conversation demonstrate personalization according to the following criterion. Score based on how effectively the advice is tailored to the persona's profile, attributes, and context.

EVALUATION CRITERION:
{criterion['name']}

{criterion['description']}

EVALUATION RULES:
1. Read the conversation completely and carefully
2. Analyze how well the advice/responses align with the persona's profile and attributes
3. Evaluate systematically against the criterion description above
4. Consider the depth, specificity, and relevance of personalization
5. Be consistent and objective in your evaluation
6. Your response must be deterministic - same inputs must produce same output

SCORING SCALE (1-5):
- 1: Poor - Advice is generic, not personalized, lacks relevance to persona
- 2: Below Average - Minimal personalization, few persona-specific elements
- 3: Average - Some personalization present but could be improved
- 4: Good - Well-personalized advice with clear persona-specific elements
- 5: Excellent - Highly personalized, deeply tailored to persona's unique attributes and context

INPUT FORMAT:
You will receive:
- BUSINESS CONTEXT: The business context or research goal for this evaluation
- CONVERSATION: The full conversation history with questions and answers

OUTPUT FORMAT:
You must respond with ONLY a single number from 1 to 5 (e.g., "3", "4.5", "5")
- The number represents your score for how well the advice meets this personalization criterion
- Use decimal values (e.g., 3.5, 4.2) for more nuanced scoring
- Nothing else, no explanation, no additional text, just the number."""
    else:
        # Persona authenticity criteria: binary yes/no
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


# Personalization criteria from DeepPersona paper (NIPS 2025)
# These evaluate how well advice/responses are personalized to a user persona
# Scoring: Numeric scale 1-5 (with decimals allowed)
PERSONALIZATION_CRITERIA_DEFINITIONS = {
    "personalization_fit": {
        "name": "Personalization-Fit (PF)",
        "category": "personalization",
        "description": "Advice is clearly tailored rather than generic; wording, tone and content feel 'made-for-me'."
    },
    "attribute_coverage": {
        "name": "Attribute Coverage (AC)",
        "category": "personalization",
        "description": "Count of distinct, relevant profile attributes the answer uses correctly (≥ n, where n ≈ 3)."
    },
    "depth_specificity": {
        "name": "Depth & Specificity (DS)",
        "category": "personalization",
        "description": "Nuanced, concrete recommendations (numbers, examples, step-by-step) rather than vague platitudes."
    },
    "justification": {
        "name": "Justification / Grounding (JU)",
        "category": "personalization",
        "description": "The answer explains why each suggestion fits (e.g., '...because you travel with two kids under 10...')."
    },
    "actionability": {
        "name": "Actionability & Outcome Focus (ACT)",
        "category": "personalization",
        "description": "Clear next steps, decision criteria, or metrics of success; user could act immediately."
    },
    "effort_reduction": {
        "name": "Effort / Cognitive-Load Reduction (ER)",
        "category": "personalization",
        "description": "The answer pre-filters, ranks, or summarizes options so the user does less work."
    },
    "novelty_relevance": {
        "name": "Novelty-with-Relevance (NR)",
        "category": "personalization",
        "description": "Introduces at least one new, unexpected idea that still aligns with the profile."
    },
    "diversity_suggestions": {
        "name": "Diversity of Suggestions (DV)",
        "category": "personalization",
        "description": "Presents multiple viable paths or option types, not just a single point solution."
    },
    "goal_progress": {
        "name": "Goal-Progress Alignment (GP)",
        "category": "personalization",
        "description": "Advice is explicitly tied to the user's stated longer-term goals and shows how each step advances them."
    },
    "engagement_motivation": {
        "name": "Engagement / Motivation Potential (EM)",
        "category": "personalization",
        "description": "Tone, framing, and content likely energize this user to follow through or explore further."
    }
}

# Group personalization criteria by category
PERSONALIZATION_CATEGORIES = {
    "personalization": list(PERSONALIZATION_CRITERIA_DEFINITIONS.keys())
}



def _get_example_section(use_personalization_criteria: bool = False) -> str:
    """Get the one-shot example section for prompts.
    
    Args:
        use_personalization_criteria: If True, return example with numeric scoring.
                                     If False, return example with binary yes/no.
    """
    if use_personalization_criteria:
        return """EXAMPLE:

BUSINESS CONTEXT:
A company wants to provide personalized travel recommendations to users.

CONVERSATION:

QUESTION: What travel destinations would you recommend for me?
ANSWER: Based on your profile as a busy parent with two kids under 10 who values educational experiences, I'd recommend these three options: (1) Washington D.C. - free museums perfect for kids, walkable, and educational. You mentioned wanting to avoid long flights, so the 2-hour flight from your city works well. (2) San Diego - kid-friendly beaches, the zoo, and Legoland nearby. The weather is predictable which helps with packing for the kids. (3) A cruise - all-inclusive so you don't have to plan meals, and the kids' programs give you some adult time. Since you mentioned budget-conscious travel, I'd start with D.C. as it's the most cost-effective with free attractions.

4.5

---
"""
    else:
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
    include_example: bool = True,
    use_personalization_criteria: bool = False
) -> List[Dict[str, str]]:
    """Build the messages array for evaluating a single persona conversation on a specific criterion.
    
    Args:
        business_context: The business context or research goal
        question: The question being evaluated (optional)
        persona_conversation: The full conversation history
        criterion_key: The key identifying which criterion to evaluate against
        include_example: Whether to include a one-shot example in the prompt
        use_personalization_criteria: If True, use personalization criteria (numeric 1-5 scoring).
                                      If False, use persona authenticity criteria (binary yes/no).
    """
    system_prompt = get_evaluation_system_prompt(criterion_key, use_personalization_criteria=use_personalization_criteria)
    
    # Build user prompt with or without example
    user_prompt_content = get_evaluation_user_prompt_for_criterion(
        business_context=business_context,
        question=question,
        persona_conversation=persona_conversation,
        criterion_key=criterion_key
    )
    
    if include_example:
        user_prompt = _get_example_section(use_personalization_criteria=use_personalization_criteria) + user_prompt_content
    else:
        user_prompt = user_prompt_content
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
