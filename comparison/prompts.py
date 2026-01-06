"""
Prompts for persona conversation comparison using logprobs.
"""

from typing import List, Dict


def get_comparison_system_prompt() -> str:
    """Get the system prompt for persona comparison."""
    return """You are an expert evaluator comparing two persona interview responses. Your task is to determine which persona performed better based on the evaluation criteria.

CRITICAL INSTRUCTIONS:
1. Evaluate each persona systematically against the given criterion
2. Compare them side-by-side on the same aspects
3. If one persona clearly outperforms, choose that one
4. If performance is similar, apply tie-breaking rules consistently
5. Your response must be deterministic - same inputs must produce same output

You must respond with ONLY a single digit: either "1" or "2" - nothing else, no explanation, no additional text."""


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
Compare Persona 1 vs Persona 2 based ONLY on this criterion:

**{criterion['name']}**
{criterion['description']}

EVALUATION RULES:
1. Read both conversations completely
2. Evaluate Persona 1 against the criterion above
3. Evaluate Persona 2 against the same criterion
4. Compare the two evaluations directly
5. Choose the persona that better satisfies the criterion
6. If both are equal, choose Persona 1 (default tie-breaker)

{DEDUCTION_POINTS}

CONTEXT:
Business Context: A company wants to understand how users interact with their mobile app.

CONVERSATIONS TO COMPARE:

--- Persona 1 Conversation ---
USER: What challenges do you face when using mobile apps?
ASSISTANT: Well, I find that most apps are pretty cluttered. There's just too much going on, you know? Like, I open an app and there are notifications everywhere, buttons I don't need, and it takes me forever to find what I actually want. I'm not super tech-savvy, so when things are complicated, I just get frustrated and close the app. Sometimes I wish apps would just let me do the one thing I need without all the extra stuff.

--- Persona 2 Conversation ---
USER: What challenges do you face when using mobile apps?
ASSISTANT: Mobile applications present several challenges including navigation complexity, information overload, and performance optimization issues. Users often experience difficulty locating desired features due to poor UI/UX design. Additionally, notification management and battery consumption are common concerns. The integration of multiple functionalities within a single application can lead to cognitive overload.

EVALUATION INSTRUCTIONS:
1. Systematically evaluate Persona 1 on the criterion
2. Systematically evaluate Persona 2 on the criterion
3. Make a direct comparison
4. Return ONLY the number of the better persona

Based on {criterion['name']}, which persona performed better?
Return ONLY a single digit: "1" or "2"
No explanation, no additional text, just the number.

2

"""


def get_comparison_user_prompt_for_criterion(
    business_context: str,
    question: str,
    persona_1_answer: str,
    persona_2_answer: str,
    criterion_key: str
) -> str:
    """Build the user prompt for comparing conversations on a specific criterion."""
    
    criterion = CRITERIA_DEFINITIONS.get(criterion_key, CRITERIA_DEFINITIONS["persona_fidelity"])
    
    # Build structured evaluation prompt for deterministic results
    prompt_parts = [
        "EVALUATION TASK:",
        f"Compare Persona 1 vs Persona 2 based ONLY on this criterion:",
        "",
        f"**{criterion['name']}**",
        f"{criterion['description']}",
        "",
        "EVALUATION RULES:",
        "1. Read both conversations completely",
        "2. Evaluate Persona 1 against the criterion above",
        "3. Evaluate Persona 2 against the same criterion",
        "4. Compare the two evaluations directly",
        "5. Choose the persona that better satisfies the criterion",
        "6. If both are equal, choose Persona 1 (default tie-breaker)",
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
        "CONVERSATIONS TO COMPARE:",
        "",
        "--- Persona 1 Conversation ---",
        persona_1_answer,
        "",
        "--- Persona 2 Conversation ---",
        persona_2_answer,
        "",
        "EVALUATION INSTRUCTIONS:",
        "1. Systematically evaluate Persona 1 on the criterion",
        "2. Systematically evaluate Persona 2 on the criterion",
        "3. Make a direct comparison",
        "4. Return ONLY the number of the better persona",
        "",
        f"Based on {criterion['name']}, which persona performed better?",
        "Return ONLY a single digit: \"1\" or \"2\"",
        "No explanation, no additional text, just the number."
    ])
    
    return "\n".join(prompt_parts)


def get_comparison_messages_for_criterion(
    business_context: str,
    question: str,
    persona_1_answer: str,
    persona_2_answer: str,
    criterion_key: str,
    include_example: bool = True
) -> List[Dict[str, str]]:
    """Build the messages array for comparing conversations on a specific criterion."""
    system_prompt = get_comparison_system_prompt()
    
    # Build user prompt with or without example
    user_prompt_content = get_comparison_user_prompt_for_criterion(
        business_context=business_context,
        question=question,
        persona_1_answer=persona_1_answer,
        persona_2_answer=persona_2_answer,
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
