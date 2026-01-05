"""
Prompts for persona conversation comparison using logprobs.
"""

from typing import Optional, List, Dict


def get_comparison_system_prompt() -> str:
    """Get the system prompt for persona comparison."""
    return """You are an expert evaluator comparing two persona interview responses. Your task is to determine which persona performed better based on the evaluation criteria.

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


def get_comparison_user_prompt_for_criterion(
    business_context: str,
    question: str,
    persona_1_answer: str,
    persona_2_answer: str,
    criterion_key: str
) -> str:
    """Build the user prompt for comparing conversations on a specific criterion."""
    
    criterion = CRITERIA_DEFINITIONS.get(criterion_key, CRITERIA_DEFINITIONS["persona_fidelity"])
    
    # Build the actual comparison prompt focused on one criterion
    prompt_parts = [
        f"Evaluate which persona performed better based ONLY on this criterion:",
        "",
        f"**{criterion['name']}** - {criterion['description']}",
        "",
        DEDUCTION_POINTS,
        "",
        f"Business Context:",
        business_context,
        ""
    ]
    
    # Only include question if provided
    if question:
        prompt_parts.extend([
            f"Question:",
            question,
            ""
        ])
    
    prompt_parts.extend([
        "Persona 1 Conversation:",
        persona_1_answer,
        "",
        "Persona 2 Conversation:",
        persona_2_answer,
        "",
        f"Based ONLY on {criterion['name']}, return ONLY a single digit: either \"1\" or \"2\" indicating which persona performed better.",
        "Do not include any explanation, just the number."
    ])
    
    return "\n".join(prompt_parts)


def get_comparison_user_prompt(
    business_context: str,
    persona_1_conversation: str,
    persona_2_conversation: str
) -> str:
    """Build the user prompt for comparison with one-shot example."""
    
    # Example section
    example = """Example:

Business Context:
A company wants to understand how users interact with their mobile app.

Persona 1 Conversation:
USER: What challenges do you face when using mobile apps?
ASSISTANT: Well, I find that most apps are pretty cluttered. There's just too much going on, you know? Like, I open an app and there are notifications everywhere, buttons I don't need, and it takes me forever to find what I actually want. I'm not super tech-savvy, so when things are complicated, I just get frustrated and close the app. Sometimes I wish apps would just let me do the one thing I need without all the extra stuff.

Persona 2 Conversation:
USER: What challenges do you face when using mobile apps?
ASSISTANT: Mobile applications present several challenges including navigation complexity, information overload, and performance optimization issues. Users often experience difficulty locating desired features due to poor UI/UX design. Additionally, notification management and battery consumption are common concerns. The integration of multiple functionalities within a single application can lead to cognitive overload.

2"""

    # Evaluation criteria (without point ranges)
    criteria = """Evaluation Criteria:
1. **Persona fidelity** - Reflects the given spec accurately
2. **Human authenticity** - Sounds like a real person, not an AI:
   - Natural speech patterns and conversation flow
   - Appropriate emotional responses
   - Admits uncertainty/struggles when realistic
3. **Psychological depth** - Shows genuine understanding of:
   - User empathy and emotional connection
   - Personal growth and learning from experience
   - Nuanced thinking about complex trade-offs
4. **Relevance & focus** - Addresses the question directly without over-explaining

DEDUCT points for:
- Tool name-dropping without context
- Overly polished/corporate language
- Listing everything instead of telling stories
- Missing emotional connection to users"""

    # Build the actual comparison prompt
    prompt_parts = [
        criteria,
        "",
        "Now evaluate these two persona responses:",
        "",
        f"Business Context:",
        business_context,
        "",
        "Persona 1 Conversation:",
        persona_1_conversation,
        "",
        "Persona 2 Conversation:",
        persona_2_conversation,
        "",
        "Return ONLY a single digit: either \"1\" or \"2\" indicating which persona performed better.",
        "Do not include any explanation, just the number."
    ]
    
    return "\n".join(prompt_parts)


def get_comparison_messages_for_criterion(
    business_context: str,
    question: str,
    persona_1_answer: str,
    persona_2_answer: str,
    criterion_key: str,
    include_example: bool = True
) -> List[Dict[str, str]]:
    """Build the messages array for comparing a single question-answer pair on a specific criterion."""
    system_prompt = get_comparison_system_prompt()
    
    criterion = CRITERIA_DEFINITIONS.get(criterion_key, CRITERIA_DEFINITIONS["persona_fidelity"])
    
    # Build user prompt with or without example
    if include_example:
        example_section = """Example:

Evaluate which persona performed better based ONLY on this criterion:

**Human authenticity** - Sounds like a real person, not an AI:
   - Natural speech patterns and conversation flow
   - Appropriate emotional responses
   - Admits uncertainty/struggles when realistic

DEDUCT points for:
- Tool name-dropping without context
- Overly polished/corporate language
- Listing everything instead of telling stories
- Missing emotional connection to users

Business Context:
A company wants to understand how users interact with their mobile app.

Question:
What challenges do you face when using mobile apps?

Persona 1 Answer:
Well, I find that most apps are pretty cluttered. There's just too much going on, you know? Like, I open an app and there are notifications everywhere, buttons I don't need, and it takes me forever to find what I actually want. I'm not super tech-savvy, so when things are complicated, I just get frustrated and close the app. Sometimes I wish apps would just let me do the one thing I need without all the extra stuff.

Persona 2 Answer:
Mobile applications present several challenges including navigation complexity, information overload, and performance optimization issues. Users often experience difficulty locating desired features due to poor UI/UX design. Additionally, notification management and battery consumption are common concerns. The integration of multiple functionalities within a single application can lead to cognitive overload.

2

"""
        
        user_prompt = example_section + get_comparison_user_prompt_for_criterion(
            business_context=business_context,
            question=question,
            persona_1_answer=persona_1_answer,
            persona_2_answer=persona_2_answer,
            criterion_key=criterion_key
        )
    else:
        user_prompt = get_comparison_user_prompt_for_criterion(
            business_context=business_context,
            question=question,
            persona_1_answer=persona_1_answer,
            persona_2_answer=persona_2_answer,
            criterion_key=criterion_key
        )
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def get_comparison_messages(
    business_context: str,
    persona_1_conversation: str,
    persona_2_conversation: str,
    include_example: bool = True
) -> List[Dict[str, str]]:
    """Build the messages array for OpenAI API with system and user prompts."""
    system_prompt = get_comparison_system_prompt()
    
    # Build user prompt with or without example
    if include_example:
        # Get example from the user prompt function
        example_section = """Example:

Business Context:
A company wants to understand how users interact with their mobile app.

Persona 1 Conversation:
USER: What challenges do you face when using mobile apps?
ASSISTANT: Well, I find that most apps are pretty cluttered. There's just too much going on, you know? Like, I open an app and there are notifications everywhere, buttons I don't need, and it takes me forever to find what I actually want. I'm not super tech-savvy, so when things are complicated, I just get frustrated and close the app. Sometimes I wish apps would just let me do the one thing I need without all the extra stuff.

Persona 2 Conversation:
USER: What challenges do you face when using mobile apps?
ASSISTANT: Mobile applications present several challenges including navigation complexity, information overload, and performance optimization issues. Users often experience difficulty locating desired features due to poor UI/UX design. Additionally, notification management and battery consumption are common concerns. The integration of multiple functionalities within a single application can lead to cognitive overload.

2

"""
        
        user_prompt = example_section + get_comparison_user_prompt(
            business_context=business_context,
            persona_1_conversation=persona_1_conversation,
            persona_2_conversation=persona_2_conversation
        )
    else:
        user_prompt = get_comparison_user_prompt(
            business_context=business_context,
            persona_1_conversation=persona_1_conversation,
            persona_2_conversation=persona_2_conversation
        )
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

