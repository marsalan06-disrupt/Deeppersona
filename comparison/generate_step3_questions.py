"""
Generate interview questions for step3 data based on selected hypotheses.

This script:
1. Fetches research document from Firestore
2. Gets step3 data (hypotheses, selectedHypotheses, interviewScript)
3. Gets step1 business context and conversation
4. Uses GPT to generate ONE question per personalization criterion (10 questions total)
   - Each question is focused on a specific criterion
   - Calls OpenAI API in a loop, one call per criterion
   - Each prompt focuses on: criterion, business_context, conversation, hypotheses
5. Adds questions to step3's interviewScript array

Usage:
    python generate_step3_questions.py --research-id <id>
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Add parent directories to path for imports
DEEPPERSONA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUNCTIONS_DIR = os.path.dirname(DEEPPERSONA_DIR)
sys.path.insert(0, DEEPPERSONA_DIR)
sys.path.insert(0, FUNCTIONS_DIR)

import firebase_admin
from firebase_admin import credentials, firestore
from prompts import PERSONALIZATION_CRITERIA_DEFINITIONS
from generate_user_profile.config import client as openai_client, get_completion

# Initialize Firebase
def init_firebase():
    """Initialize Firebase Admin SDK."""
    if not firebase_admin._apps:
        possible_paths = [
            os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
            os.path.join(os.path.dirname(__file__), "..", "..", "serviceAccountKey.json"),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "serviceAccountKey.json"),
        ]

        cred_path = None
        for path in possible_paths:
            if path and os.path.exists(path):
                cred_path = path
                break

        if cred_path:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print(f"Firebase initialized with credentials from: {cred_path}")
        else:
            firebase_admin.initialize_app()
            print("Firebase initialized with default credentials")

    return firestore.client()


def fetch_research(db, research_id: str) -> Dict[str, Any]:
    """Fetch research document from Firestore."""
    doc_ref = db.collection("research").document(research_id)
    doc = doc_ref.get()

    if not doc.exists:
        raise ValueError(f"Research document {research_id} not found")

    return doc.to_dict()


def format_conversation_for_prompt(conversation_data: Any) -> str:
    """Format conversation data for prompt.
    
    Handles various conversation formats:
    - Array of objects with question/answer fields
    - String format
    - Object with conversationHistory field
    """
    if not conversation_data:
        return "No conversation data available"
    
    # If it's a string, return as is
    if isinstance(conversation_data, str):
        return conversation_data
    
    # If it's a dict, try to extract conversationHistory
    if isinstance(conversation_data, dict):
        conversation_history = conversation_data.get("conversationHistory", conversation_data)
        if isinstance(conversation_history, str):
            return conversation_history
        if isinstance(conversation_history, list):
            formatted_parts = []
            for item in conversation_history:
                if isinstance(item, dict):
                    question = item.get("question", "").strip()
                    answer = item.get("answer", "").strip()
                    if question:
                        formatted_parts.append(f"QUESTION: {question}")
                    if answer:
                        formatted_parts.append(f"ANSWER: {answer}")
                elif isinstance(item, str):
                    formatted_parts.append(item)
            return "\n".join(formatted_parts) if formatted_parts else "No conversation data available"
    
    # If it's a list, format it
    if isinstance(conversation_data, list):
        formatted_parts = []
        for item in conversation_data:
            if isinstance(item, dict):
                question = item.get("question", "").strip()
                answer = item.get("answer", "").strip()
                if question:
                    formatted_parts.append(f"QUESTION: {question}")
                if answer:
                    formatted_parts.append(f"ANSWER: {answer}")
            elif isinstance(item, str):
                formatted_parts.append(item)
        return "\n".join(formatted_parts) if formatted_parts else "No conversation data available"
    
    # Fallback: convert to string
    return str(conversation_data)


def get_single_question_prompt(
    criterion_key: str,
    criterion_name: str,
    criterion_description: str,
    business_context: str,
    conversation: str,
    hypothesis_statements: List[str],
    hypothesis_ids: List[str],
    question_number: int,
    previous_questions: List[Dict[str, Any]] = None
) -> List[Dict[str, str]]:
    """Generate prompt for a single question based on one criterion.
    
    Args:
        criterion_key: The key of the criterion (e.g., "personalization_fit")
        criterion_name: The name of the criterion (e.g., "Personalization-Fit (PF)")
        criterion_description: The description of the criterion
        business_context: Business context from step1
        conversation: Conversation data from step1
        hypothesis_statements: List of hypothesis statements
        hypothesis_ids: List of hypothesis IDs corresponding to statements
        question_number: The question number (1-10)
        previous_questions: List of previously generated questions to avoid repetition
    
    Returns:
        List of message dictionaries for OpenAI API
    """
    
    # Format hypothesis statements with their IDs
    hypotheses_text = "\n".join([
        f"{hyp_id}: {stmt}"
        for hyp_id, stmt in zip(hypothesis_ids, hypothesis_statements)
    ])
    
    system_prompt = """You are a customer discovery assistant trained to write interview scripts based on The Mom Test principles. Your job is to generate practical, behavioral interview questions that avoid fluff, hypotheticals, or leading prompts.

TASK:
Generate ONE interview question that:
1. Validates the given hypotheses through real behavior and past experience
2. Is specifically designed to elicit responses that demonstrate the target personalization criterion
3. Follows The Mom Test principles - digs into real behavior, past experience, and pain—not feature feedback
4. Considers the business context and existing conversation context
5. Is DISTINCTLY DIFFERENT from previously generated questions (avoid repetition, similar phrasing, or overlapping topics)

THE MOM TEST PRINCIPLES (CRITICAL):
- Questions must dig into REAL BEHAVIOR and PAST EXPERIENCE, not hypotheticals or future desires
- Never assume a problem exists - phrase questions to invite description of the process/experience in neutral terms
- Use real-world context, not hypothetical future scenarios
- Focus on what they actually DO, not what they WOULD DO
- Avoid opinions, hypotheticals, or leading language
- Questions should uncover pain through behavior, not by asking about pain directly

HARD GUARDRAILS (MUST ENFORCE):
- NEVER use hypotheticals, opinions, or leading language
- DISALLOW these phrases: "would you", "will you", "would you pay", "do you like", "how would you feel", "imagine", "if we built", "should", "could you see yourself"
- NEVER use the words "Pain points" or "challenges" - instead ask neutrally about the process/experience
- NEVER assume a problem exists - use neutral phrasing (e.g., "How was the process of doing X?" instead of "What challenges did you face while doing X?")
- Focus on PAST BEHAVIOR and REAL EXPERIENCES, not future hypotheticals
- Questions should uncover behavior and experience, not ask for opinions or feature feedback

QUESTION DESIGN PRINCIPLES:
- Use open-ended questions that invite storytelling about REAL PAST EXPERIENCES
- Probe deeply into specific behaviors and actual events
- Focus on concrete examples: "When was the last time...", "Tell me about a time when...", "How do you usually..."
- Encourage specific details about actual behavior and past experiences
- Build on previous conversation context naturally
- VARY your question structure, phrasing, and approach - avoid using the same sentence patterns
- Explore DIFFERENT angles, aspects, or dimensions of the hypotheses
- Use diverse question types: "How", "What", "When", "Can you tell me about", "Tell me about", "Walk me through", etc.
- Ensure each question covers a UNIQUE aspect or perspective

OUTPUT FORMAT:
Return a JSON object (not an array) with the following structure:
{
  "question": "The question text",
  "hypothesisIds": ["hypothesis_1", "hypothesis_3"],
  "probingMode": "deep",
  "tags": ["workflow", "planning"]
}

Where:
- question: The interview question text (MUST follow The Mom Test principles - no hypotheticals, no leading language)
- hypothesisIds: Array of hypothesis IDs this question addresses (use EXACT IDs from the hypotheses list, can be empty array if it's a general opening question)
- probingMode: Either "normal" or "deep" (use "deep" for questions that probe into specific problem areas or behaviors)
- tags: Array of 1-2 relevant tags from these valid types ONLY:
  * "opening" - Build rapport and confirm user relevance
  * "problem discovery" - Uncover pain through behavior
  * "workflow" - Understand current process
  * "existing solutions" - What they currently use/do
  * "prioritization" - What matters most
  * "willingness to pay" - Payment behavior (if relevant)
  * "solution fit" - How solution fits workflow (only if solution validation stage)

VALID QUESTION EXAMPLES (following The Mom Test):
- "Can you tell me about how your team runs recurring meetings right now?" → opening
- "When was the last time you prepped for a recurring meeting? What did you do to get ready?" → problem discovery
- "How do you usually keep track of what was discussed or decided after the meeting?" → workflow
- "What tools are involved from prep to follow-up?" → existing solutions
- "What happens when follow-ups get missed or fall through the cracks?" → prioritization

INVALID QUESTION EXAMPLES (violate The Mom Test):
- "Would you use a tool that..." → hypothetical, forbidden phrase
- "Do you like the idea of..." → opinion, forbidden phrase
- "What challenges do you face..." → assumes problem exists, uses forbidden word
- "How would you feel if..." → hypothetical, forbidden phrase
- "Imagine you had..." → hypothetical, forbidden phrase"""

    # Format previous questions for context
    previous_questions_text = ""
    if previous_questions:
        previous_questions_text = "\n\nPREVIOUSLY GENERATED QUESTIONS (AVOID REPETITION):\n"
        for i, prev_q in enumerate(previous_questions, 1):
            prev_question_text = prev_q.get("question", "")
            prev_hyp_ids = prev_q.get("hypothesisIds", [])
            prev_tags = prev_q.get("tags", [])
            previous_questions_text += f"{i}. \"{prev_question_text}\" (Hypotheses: {prev_hyp_ids}, Tags: {prev_tags})\n"
        previous_questions_text += "\nIMPORTANT: Your question must be DISTINCTLY different from these. Use different phrasing, explore different angles, and avoid similar sentence structures or topics."
    
    # Determine if this should be an opening question
    is_opening_question = question_number <= 2
    opening_instruction = ""
    if is_opening_question:
        opening_instruction = f"\nSPECIAL INSTRUCTION: This is question #{question_number}. The first 1-2 questions should be 'opening' questions that build rapport and confirm user relevance. Use tag 'opening' and you may use empty hypothesisIds array if it's a general opening question."
    
    user_prompt = f"""TARGET PERSONALIZATION CRITERION:
Name: {criterion_name}
Description: {criterion_description}

BUSINESS CONTEXT:
{business_context}

EXISTING CONVERSATION CONTEXT:
{conversation}

HYPOTHESES TO VALIDATE:
{hypotheses_text}
{previous_questions_text}
{opening_instruction}

INSTRUCTIONS:
1. Generate ONE interview question following The Mom Test principles that validates hypotheses through REAL BEHAVIOR and PAST EXPERIENCE
2. The question should be designed to elicit responses demonstrating the target criterion: {criterion_name}
3. The question should directly relate to validating one or more of the hypotheses provided above
4. Use the EXACT hypothesis IDs from the list above (e.g., "hypothesis_1", "hypothesis_3", etc.) in the hypothesisIds array
5. VARY which hypotheses you address - don't always use the same combination
6. Choose "deep" probing mode if the question probes into specific problem areas or behaviors, otherwise use "normal" - VARY between modes
7. Select 1-2 appropriate tags from the valid tag list - VARY the tags to cover different aspects
8. The question should build naturally on the existing conversation context
9. CRITICAL - THE MOM TEST REQUIREMENTS:
    - Focus on PAST BEHAVIOR and REAL EXPERIENCES, not hypotheticals
    - Use neutral phrasing - never assume a problem exists
    - Ask about actual behavior: "How do you...", "When was the last time...", "Tell me about a time when..."
    - NEVER use forbidden phrases: "would you", "will you", "do you like", "how would you feel", "imagine", "if we built", "should", "could you see yourself"
    - NEVER use words "pain points" or "challenges" - ask neutrally about the process
    - Dig into real behavior and experience, not opinions or feature feedback
10. CRITICAL: Ensure your question is DISTINCTLY different from previously generated questions:
    - Use different question structures and phrasing
    - Explore different angles or aspects of the hypotheses
    - Avoid repeating similar topics or approaches
    - Vary your question type (How, What, When, Can you tell me about, Tell me about, Walk me through, etc.)
    - Cover unique aspects that haven't been addressed yet

Generate the question now and return it as a JSON object following the exact format specified above. Remember: The question must follow The Mom Test principles - focus on REAL BEHAVIOR and PAST EXPERIENCE, not hypotheticals or opinions."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def generate_single_question(
    criterion_key: str,
    criterion_data: Dict[str, str],
    business_context: str,
    conversation: str,
    hypothesis_statements: List[str],
    hypothesis_ids: List[str],
    question_number: int,
    previous_questions: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate a single question for one criterion using GPT.
    
    Returns:
        Dictionary with question data including id, question, hypothesisIds, order, probingMode, tags, isCustom, addedAt
    """
    
    print(f"\n[GENERATE] Generating question {question_number}/10 for criterion: {criterion_data['name']}")
    
    messages = get_single_question_prompt(
        criterion_key=criterion_key,
        criterion_name=criterion_data['name'],
        criterion_description=criterion_data['description'],
        business_context=business_context,
        conversation=conversation,
        hypothesis_statements=hypothesis_statements,
        hypothesis_ids=hypothesis_ids,
        question_number=question_number,
        previous_questions=previous_questions or []
    )
    
    response = get_completion(
        messages=messages,
        model="gpt-4o",
        temperature=0.7,
        max_retries=3
    )
    
    if not response:
        raise ValueError(f"Failed to generate question for criterion {criterion_key}")
    
    # Parse JSON response
    try:
        # Extract JSON from markdown if needed
        if "```json" in response:
            json_start = response.find("```json") + 7
            json_end = response.find("```", json_start)
            response = response[json_start:json_end].strip()
        elif "```" in response:
            json_start = response.find("```") + 3
            json_end = response.find("```", json_start)
            response = response[json_start:json_end].strip()
        
        question_data = json.loads(response)
        
        # Validate and fix question structure
        if not isinstance(question_data, dict):
            raise ValueError("Response is not a JSON object")
        
        # Ensure all required fields are present
        current_time = datetime.now(timezone.utc).isoformat() + "Z"
        
        # Build complete question object
        question = {
            "id": f"question_{question_number}",
            "question": question_data.get("question", ""),
            "hypothesisIds": question_data.get("hypothesisIds", []),
            "order": question_number,
            "probingMode": question_data.get("probingMode", "normal"),
            "tags": question_data.get("tags", []),
            "isCustom": False,
            "addedAt": current_time
        }
        
        # Validate and fix hypothesis IDs
        if isinstance(question["hypothesisIds"], list):
            # Filter to only include valid hypothesis IDs
            valid_ids = [hid for hid in question["hypothesisIds"] 
                       if isinstance(hid, str) and hid in hypothesis_ids]
            question["hypothesisIds"] = valid_ids
        else:
            question["hypothesisIds"] = []
        
        # Validate required fields
        if not question["question"]:
            raise ValueError(f"Question text is empty for criterion {criterion_key}")
        
        print(f"  ✓ Generated: {question['question'][:60]}...")
        print(f"    Hypothesis IDs: {question['hypothesisIds']}")
        print(f"    Tags: {question['tags']}")
        
        return question
        
    except json.JSONDecodeError as e:
        print(f"  Error parsing JSON response: {e}")
        print(f"  Response was: {response[:500]}...")
        raise ValueError(f"Failed to parse question JSON for criterion {criterion_key}: {e}")


def generate_questions(
    business_context: str,
    conversation: str,
    hypothesis_statements: List[str],
    hypothesis_ids: List[str],
    personalization_criteria: Dict[str, Dict[str, str]]
) -> List[Dict[str, Any]]:
    """Generate questions using GPT - one question per criterion.
    
    Args:
        business_context: Business context from step1
        conversation: Conversation data from step1
        hypothesis_statements: List of hypothesis statements
        hypothesis_ids: List of hypothesis IDs
        personalization_criteria: Dictionary of personalization criteria
    
    Returns:
        List of question dictionaries
    """
    
    print(f"\n[GENERATE] Generating questions using GPT (one per criterion)...")
    print(f"  Business context length: {len(business_context)} chars")
    print(f"  Conversation length: {len(conversation)} chars")
    print(f"  Number of hypotheses: {len(hypothesis_statements)}")
    print(f"  Number of criteria: {len(personalization_criteria)}")
    
    questions = []
    
    # Generate one question for each criterion
    for idx, (criterion_key, criterion_data) in enumerate(personalization_criteria.items(), start=1):
        try:
            question = generate_single_question(
                criterion_key=criterion_key,
                criterion_data=criterion_data,
                business_context=business_context,
                conversation=conversation,
                hypothesis_statements=hypothesis_statements,
                hypothesis_ids=hypothesis_ids,
                question_number=idx,
                previous_questions=questions  # Pass previously generated questions to avoid repetition
            )
            questions.append(question)
        except Exception as e:
            print(f"  ✗ Failed to generate question for {criterion_key}: {e}")
            # Continue with other criteria even if one fails
            continue
    
    print(f"\n  Generated {len(questions)} questions out of {len(personalization_criteria)} criteria")
    return questions


def update_step3_interview_script(db, research_id: str, new_questions: List[Dict[str, Any]]):
    """Update step3 interviewScript in Firestore."""
    print(f"\n[UPDATE] Updating step3 interviewScript in Firestore...")
    
    doc_ref = db.collection("research").document(research_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise ValueError(f"Research document {research_id} not found")
    
    research_data = doc.to_dict()
    step3 = research_data.get("step3", {})
    
    # Get existing interviewScript or initialize
    interview_script = step3.get("interviewScript", [])
    
    # Add new questions
    # Check if we should replace or append
    # For now, we'll append to existing questions
    existing_ids = {q.get("id") for q in interview_script if isinstance(q, dict)}
    
    # Add questions that don't already exist
    added_count = 0
    for question in new_questions:
        if question.get("id") not in existing_ids:
            interview_script.append(question)
            added_count += 1
    
    # Update step3
    step3["interviewScript"] = interview_script
    step3["lastUpdated"] = datetime.now(timezone.utc).isoformat() + "Z"
    
    # Update research document
    research_data["step3"] = step3
    doc_ref.set(research_data)
    
    print(f"  Added {added_count} new questions to interviewScript")
    print(f"  Total questions in interviewScript: {len(interview_script)}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate interview questions for step3 data based on selected hypotheses"
    )
    parser.add_argument(
        "--research-id",
        type=str,
        required=True,
        help="Research document ID"
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing interviewScript instead of appending"
    )
    
    args = parser.parse_args()
    research_id = args.research_id
    
    print("="*60)
    print("Generate Step3 Interview Questions")
    print("="*60)
    print(f"\nResearch ID: {research_id}")
    
    # Initialize Firebase
    print("\n[INIT] Initializing Firebase...")
    db = init_firebase()
    
    # Fetch research document
    print(f"\n[FETCH] Loading research document...")
    research = fetch_research(db, research_id)
    
    # Get step3 data
    step3 = research.get("step3", {})
    if not step3:
        raise ValueError("No step3 data found in research document")
    
    hypotheses = step3.get("hypotheses", [])
    selected_hypotheses = step3.get("selectedHypotheses", [])
    
    if not hypotheses:
        raise ValueError("No hypotheses found in step3 data")
    if not selected_hypotheses:
        raise ValueError("No selectedHypotheses found in step3 data")
    
    print(f"  Found {len(hypotheses)} total hypotheses")
    print(f"  Found {len(selected_hypotheses)} selected hypotheses")
    
    # Create hypothesis ID to statement map
    hypothesis_map = {h.get("id"): h.get("statement", "") for h in hypotheses if h.get("id")}
    
    # Get selected hypothesis statements and IDs
    selected_statements = []
    selected_ids = []
    for h_id in selected_hypotheses:
        if h_id in hypothesis_map:
            selected_statements.append(hypothesis_map[h_id])
            selected_ids.append(h_id)
        else:
            print(f"  Warning: Hypothesis ID {h_id} not found in hypotheses list")
    
    if not selected_statements:
        raise ValueError("No valid selected hypothesis statements found")
    
    print(f"\n[SELECTED HYPOTHESES]")
    for h_id, stmt in zip(selected_ids, selected_statements):
        print(f"  - {h_id}: {stmt[:80]}...")
    
    # Get step1 data
    step1 = research.get("step1", {})
    business_context = step1.get("problemStatement") or step1.get("researchGoal") or "No business context provided"
    
    # Get step1 conversation
    conversation_data = step1.get("conversation") or step1.get("conversationHistory") or ""
    conversation = format_conversation_for_prompt(conversation_data)
    
    print(f"\n[STEP1 DATA]")
    print(f"  Business Context: {business_context[:100]}...")
    print(f"  Conversation: {len(conversation)} chars")
    
    # Generate questions
    questions = generate_questions(
        business_context=business_context,
        conversation=conversation,
        hypothesis_statements=selected_statements,
        hypothesis_ids=selected_ids,
        personalization_criteria=PERSONALIZATION_CRITERIA_DEFINITIONS
    )
    
    # Display generated questions
    print(f"\n[GENERATED QUESTIONS]")
    for q in questions:
        print(f"  {q.get('id', '?')}: {q.get('question', '')[:60]}...")
        print(f"    Hypothesis IDs: {q.get('hypothesisIds', [])}")
        print(f"    Tags: {q.get('tags', [])}")
    
    # Update Firestore
    if args.replace:
        # Replace existing interviewScript
        step3["interviewScript"] = questions
        step3["lastUpdated"] = datetime.now(timezone.utc).isoformat() + "Z"
        research["step3"] = step3
        db.collection("research").document(research_id).set(research)
        print(f"\n[UPDATE] Replaced interviewScript with {len(questions)} questions")
    else:
        # Append to existing
        update_step3_interview_script(db, research_id, questions)
    
    print("\n" + "="*60)
    print("Done!")
    print("="*60)


if __name__ == "__main__":
    main()
