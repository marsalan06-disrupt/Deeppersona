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
    "persona_fidelity": {
        "name": "Persona fidelity",
        "description": "Reflects the given spec accurately"
    },
    "human_authenticity": {
        "name": "Human authenticity",
        "description": "Sounds like a real person, not an AI:\n   - Natural speech patterns and conversation flow\n   - Appropriate emotional responses\n   - Admits uncertainty/struggles when realistic"
    },
    "psychological_depth": {
        "name": "Psychological depth",
        "description": "Shows genuine understanding of:\n   - User empathy and emotional connection\n   - Personal growth and learning from experience\n   - Nuanced thinking about complex trade-offs"
    },
    "relevance_focus": {
        "name": "Relevance & focus",
        "description": "Addresses the question directly without over-explaining"
    }
}

DEDUCTION_POINTS = """DEDUCT points for:
- Tool name-dropping without context
- Overly polished/corporate language
- Listing everything instead of telling stories
- Missing emotional connection to users"""


def _get_example_section(criterion_key: str = "human_authenticity") -> str:
    """Get the one-shot example section for prompts."""
    criterion = CRITERIA_DEFINITIONS.get(criterion_key, CRITERIA_DEFINITIONS["human_authenticity"])
    
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
    
    criterion = CRITERIA_DEFINITIONS.get(criterion_key, CRITERIA_DEFINITIONS["persona_fidelity"])
    
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
