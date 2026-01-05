"""
Compare persona conversations using logprobs to determine which performed better.

This script:
1. Fetches conversations from Firestore for two personas
2. Sends comparison prompt with conversations labeled as "1" and "2"
3. Extracts logprob for first token response ("1" or "2")
4. Calculates linear probability
5. Maps response back to original persona IDs
6. Saves results to JSON file

Usage:
    python compare_conversations_logprob.py --research-id <id> --persona-1-id <id> --persona-2-id <id>
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
import numpy as np

# Add parent directories to path for imports
DEEPPERSONA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUNCTIONS_DIR = os.path.dirname(DEEPPERSONA_DIR)
sys.path.insert(0, DEEPPERSONA_DIR)
sys.path.insert(0, FUNCTIONS_DIR)

import firebase_admin
from firebase_admin import credentials, firestore
from prompts import get_comparison_messages, get_comparison_messages_for_criterion, CRITERIA_DEFINITIONS
from generate_user_profile.config import client as openai_client

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


def fetch_conversations(db, research_id: str, persona_id: str) -> List[Dict[str, Any]]:
    """Fetch all conversations for a persona from Firestore."""
    interviews_ref = db.collection("interviews")
    query = interviews_ref.where("researchId", "==", research_id).where("personaId", "==", persona_id)
    docs = query.get()
    
    conversations = []
    for doc in docs:
        conversations.append(doc.to_dict())
    
    return conversations


def extract_qa_pairs(conversation: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract question-answer pairs from conversation."""
    qa_pairs = []
    
    # Extract conversation messages if available
    messages = conversation.get("messages", [])
    if not messages:
        # Try alternative field names
        messages = conversation.get("conversation", []) or conversation.get("history", [])
    
    if messages:
        i = 0
        while i < len(messages):
            msg = messages[i]
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            
            # Look for USER message followed by ASSISTANT message
            if role == "user":
                question = content
                answer = ""
                
                # Look for the next ASSISTANT message
                if i + 1 < len(messages) and messages[i + 1].get("role", "").lower() == "assistant":
                    answer = messages[i + 1].get("content", "")
                    qa_pairs.append({
                        "question": question,
                        "answer": answer
                    })
                    i += 2  # Skip both user and assistant messages
                    continue
            
            i += 1
    
    return qa_pairs


def format_conversation_for_prompt(conversation: Dict[str, Any]) -> str:
    """Format conversation data for inclusion in prompt."""
    formatted_parts = []
    
    # Extract conversation messages if available
    messages = conversation.get("messages", [])
    if not messages:
        # Try alternative field names
        messages = conversation.get("conversation", []) or conversation.get("history", [])
    
    if messages:
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            formatted_parts.append(f"{role.upper()}: {content}")
    else:
        # Fallback: include all relevant fields
        for key, value in conversation.items():
            if key not in ["researchId", "personaId", "id", "createdAt", "updatedAt"]:
                formatted_parts.append(f"{key}: {str(value)}")
    
    return "\n".join(formatted_parts) if formatted_parts else "No conversation data available"




def compare_conversations_with_logprob(
    client: Any,
    messages: List[Dict[str, str]],
    model: str = "gpt-4o",
    temperature: float = 0.0
) -> Dict[str, Any]:
    """Call OpenAI API with logprobs enabled and extract first token response."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            logprobs=True,
            top_logprobs=2,  # Get logprob for the chosen token and the not chosen
            max_tokens=1  # We only want the first token ("1" or "2")
        )
        
        choice = response.choices[0]
        message_content = choice.message.content.strip()
        
        # Extract logprobs for the first token
        logprobs_data = choice.logprobs
        if logprobs_data and logprobs_data.content:
            first_token = logprobs_data.content[0]
            token_text = first_token.token
            logprob_value = first_token.logprob
            
            # Calculate linear probability
            linear_prob = np.round(np.exp(logprob_value) * 100, 2)
            
            # Get top alternatives if available
            top_logprobs = []
            if hasattr(first_token, 'top_logprobs') and first_token.top_logprobs:
                for alt in first_token.top_logprobs:
                    top_logprobs.append({
                        "token": alt.token,
                        "logprob": alt.logprob,
                        "linear_prob": np.round(np.exp(alt.logprob) * 100, 2)
                    })
            
            return {
                "response": message_content,
                "first_token": token_text,
                "logprob": logprob_value,
                "linear_probability": float(linear_prob),
                "top_alternatives": top_logprobs,
                "full_response": response
            }
        else:
            return {
                "response": message_content,
                "first_token": message_content[0] if message_content else None,
                "logprob": None,
                "linear_probability": None,
                "error": "No logprobs returned"
            }
            
    except Exception as e:
        return {
            "error": str(e),
            "response": None,
            "logprob": None,
            "linear_probability": None
        }


def determine_confidence(linear_prob: float) -> str:
    """Determine confidence level based on linear probability."""
    if linear_prob >= 90:
        return "very_high"
    elif linear_prob >= 75:
        return "high"
    elif linear_prob >= 60:
        return "medium"
    elif linear_prob >= 50:
        return "low"
    else:
        return "very_low"


def main():
    parser = argparse.ArgumentParser(description="Compare persona conversations using logprobs")
    parser.add_argument("--research-id", required=True, help="Research ID")
    parser.add_argument("--persona-1-id", required=True, help="First persona ID to compare")
    parser.add_argument("--persona-2-id", required=True, help="Second persona ID to compare")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use (default: gpt-4o)")
    parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for generation (default: 0.0)")
    args = parser.parse_args()

    research_id = args.research_id
    persona_1_id = args.persona_1_id
    persona_2_id = args.persona_2_id
    model = args.model
    temperature = args.temperature

    print(f"\n{'#'*60}")
    print(f"# Persona Conversation Comparison (Logprob Analysis)")
    print(f"# Research ID: {research_id}")
    print(f"# Persona 1 ID: {persona_1_id}")
    print(f"# Persona 2 ID: {persona_2_id}")
    print(f"{'#'*60}")

    # Initialize Firebase
    print("\n[INIT] Connecting to Firebase...")
    db = init_firebase()

    # Initialize OpenAI client (using config from generate_user_profile)
    print("[INIT] Initializing OpenAI client...")
    client = openai_client

    # Fetch research document for business context
    print(f"\n[FETCH] Loading research document...")
    research = fetch_research(db, research_id)
    business_context = research.get("step1", {}).get("problemStatement") or research.get("step1", {}).get("researchGoal") or "No business context provided"
    print(f"  Business Context: {business_context[:100]}...")

    # Fetch conversations for both personas
    print(f"\n[FETCH] Loading conversations for Persona 1 ({persona_1_id})...")
    conversations_1 = fetch_conversations(db, research_id, persona_1_id)
    print(f"  Found {len(conversations_1)} conversation(s)")

    print(f"\n[FETCH] Loading conversations for Persona 2 ({persona_2_id})...")
    conversations_2 = fetch_conversations(db, research_id, persona_2_id)
    print(f"  Found {len(conversations_2)} conversation(s)")

    if not conversations_1:
        raise ValueError(f"No conversations found for persona {persona_1_id}")
    if not conversations_2:
        raise ValueError(f"No conversations found for persona {persona_2_id}")

    # Format full conversations
    print(f"\n[FORMAT] Formatting conversations...")
    persona_1_conversation_text = format_conversation_for_prompt(conversations_1[0])
    persona_2_conversation_text = format_conversation_for_prompt(conversations_2[0])
    
    print(f"  Persona 1 conversation length: {len(persona_1_conversation_text)} chars")
    print(f"  Persona 2 conversation length: {len(persona_2_conversation_text)} chars")
    
    if not persona_1_conversation_text or not persona_2_conversation_text:
        raise ValueError("Could not format conversations")
    
    # Get all criteria keys
    criteria_keys = list(CRITERIA_DEFINITIONS.keys())
    total_comparisons = len(criteria_keys)
    
    # Compare full conversations, evaluating each criterion separately
    print(f"\n[COMPARE] Comparing full conversations across {len(criteria_keys)} criteria ({total_comparisons} total comparisons)...")
    
    criterion_results = []
    comparison_count = 0
    
    # Evaluate each criterion separately on the full conversations
    for criterion_key in criteria_keys:
        criterion = CRITERIA_DEFINITIONS[criterion_key]
        comparison_count += 1
        
        print(f"\n  [{comparison_count}/{total_comparisons}] Evaluating: {criterion['name']}...")
        
        # Build comparison messages for full conversations and this criterion
        # Include example only for the very first comparison
        messages = get_comparison_messages_for_criterion(
            business_context=business_context,
            question="",  # No specific question, evaluating full conversation
            persona_1_answer=persona_1_conversation_text,
            persona_2_answer=persona_2_conversation_text,
            criterion_key=criterion_key,
            include_example=(comparison_count == 1)
        )
        
        # Call OpenAI with logprobs
        result = compare_conversations_with_logprob(
            client=client,
            messages=messages,
            model=model,
            temperature=temperature
        )
        
        if "error" in result:
            print(f"    ERROR: {result['error']}")
            criterion_results.append({
                "criterion_key": criterion_key,
                "criterion_name": criterion["name"],
                "error": result["error"]
            })
            continue
        
        # Map response back to actual persona IDs
        winner_label = result["first_token"]
        if winner_label == "1":
            winner_id = persona_1_id
            loser_id = persona_2_id
        elif winner_label == "2":
            winner_id = persona_2_id
            loser_id = persona_1_id
        else:
            print(f"    WARNING: Unexpected response token: {winner_label}")
            winner_id = None
            loser_id = None
        
        criterion_result = {
            "criterion_key": criterion_key,
            "criterion_name": criterion["name"],
            "winner_label": winner_label,
            "winner_persona_id": winner_id,
            "loser_persona_id": loser_id,
            "logprob": result.get("logprob"),
            "linear_probability": result.get("linear_probability"),
            "confidence": determine_confidence(result.get("linear_probability", 0)) if result.get("linear_probability") else None,
            "response_text": result.get("response"),
            "top_alternatives": result.get("top_alternatives", [])
        }
        
        criterion_results.append(criterion_result)
        print(f"    Winner: Persona {winner_label} | Confidence: {criterion_result['confidence']} ({criterion_result['linear_probability']}%)")
    
    # Calculate overall winner per criterion
    criterion_wins = {key: {"persona_1": 0, "persona_2": 0} for key in criteria_keys}
    total_persona_1_wins = 0
    total_persona_2_wins = 0
    
    for cr in criterion_results:
        if "error" not in cr:
            winner_label = cr.get("winner_label")
            criterion_key = cr.get("criterion_key")
            if winner_label == "1":
                criterion_wins[criterion_key]["persona_1"] = 1
                total_persona_1_wins += 1
            elif winner_label == "2":
                criterion_wins[criterion_key]["persona_2"] = 1
                total_persona_2_wins += 1
    
    # Determine overall winner
    if total_persona_1_wins > total_persona_2_wins:
        overall_winner_id = persona_1_id
        overall_loser_id = persona_2_id
        overall_winner_label = "1"
    elif total_persona_2_wins > total_persona_1_wins:
        overall_winner_id = persona_2_id
        overall_loser_id = persona_1_id
        overall_winner_label = "2"
    else:
        overall_winner_id = None
        overall_loser_id = None
        overall_winner_label = "tie"
    
    # Prepare criterion-wise summary
    criterion_summary = {}
    for criterion_key, criterion in CRITERIA_DEFINITIONS.items():
        wins = criterion_wins[criterion_key]
        if wins["persona_1"] > wins["persona_2"]:
            winner = "1"
        elif wins["persona_2"] > wins["persona_1"]:
            winner = "2"
        else:
            winner = "tie"
        
        criterion_summary[criterion_key] = {
            "criterion_name": criterion["name"],
            "winner": winner,
            "persona_1_wins": wins["persona_1"],
            "persona_2_wins": wins["persona_2"]
        }
    
    # Prepare output
    output = {
        "timestamp": datetime.now().isoformat(),
        "research_id": research_id,
        "persona_1_id": persona_1_id,
        "persona_2_id": persona_2_id,
        "overall_comparison": {
            "winner_label": overall_winner_label,
            "winner_persona_id": overall_winner_id,
            "loser_persona_id": overall_loser_id,
            "persona_1_wins": total_persona_1_wins,
            "persona_2_wins": total_persona_2_wins,
            "total_criteria": len(criteria_keys)
        },
        "criterion_summary": criterion_summary,
        "criteria_results": criterion_results,
        "persona_1_conversation_preview": persona_1_conversation_text[:500] + "..." if len(persona_1_conversation_text) > 500 else persona_1_conversation_text,
        "persona_2_conversation_preview": persona_2_conversation_text[:500] + "..." if len(persona_2_conversation_text) > 500 else persona_2_conversation_text,
        "model_used": model,
        "temperature": temperature,
        "business_context": business_context[:200] + "..." if len(business_context) > 200 else business_context
    }

    # Save to JSON file
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(
        output_dir,
        f"comparison_logprob_{research_id}_{persona_1_id[:8]}_{persona_2_id[:8]}_{timestamp}.json"
    )

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    # Print results
    print("\n" + "="*60)
    print("COMPARISON RESULTS")
    print("="*60)
    print(f"\nOverall Winner: Persona {overall_winner_label} ({overall_winner_id})")
    print(f"Persona 1 Total Wins: {total_persona_1_wins}/{total_persona_1_wins + total_persona_2_wins}")
    print(f"Persona 2 Total Wins: {total_persona_2_wins}/{total_persona_1_wins + total_persona_2_wins}")
    
    print(f"\nCriterion-wise Summary:")
    for criterion_key, summary in criterion_summary.items():
        print(f"  {summary['criterion_name']}:")
        print(f"    Winner: Persona {summary['winner']}")
        print(f"    Persona 1: {summary['persona_1_wins']} wins | Persona 2: {summary['persona_2_wins']} wins")
    
    print(f"\nCriterion Results:")
    for cr in criterion_results:
        if "error" not in cr:
            print(f"  {cr['criterion_name']}: Persona {cr['winner_label']} | {cr['confidence']} ({cr['linear_probability']}%) | Logprob: {cr['logprob']}")
        else:
            print(f"  {cr.get('criterion_name', 'Unknown')}: ERROR - {cr['error']}")
    
    print(f"\nResults saved to: {output_file}")

    return output


if __name__ == "__main__":
    main()

