"""
Compare persona conversations using logprobs to determine which performed better.

This script:
1. Fetches conversations from Firestore for two personas
2. For each criterion, makes 2 independent calls (one per persona)
3. Evaluates each persona against the criterion (yes/no)
4. Extracts yes/no probabilities from top 20 logprobs
5. Compares yes probabilities to determine winner
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
from prompts import get_evaluation_messages_for_criterion, CRITERIA_DEFINITIONS
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


def format_conversation_for_prompt(conversation: Dict[str, Any]) -> str:
    """Format conversation history - extract only questions and answers from conversationHistory."""
    formatted_parts = []
    
    # Get conversationHistory from interview object (array of objects with question/answer fields)
    conversation_history = conversation.get("conversationHistory", [])
    
    if not conversation_history:
        return "No conversation history available"
    
    # Extract question and answer from each conversation item
    for item in conversation_history:
        question = item.get("question", "").strip()
        answer = item.get("answer", "").strip()
        
        if question:
            formatted_parts.append(f"QUESTION: {question}")
        if answer:
            formatted_parts.append(f"ANSWER: {answer}")
    
    return "\n".join(formatted_parts) if formatted_parts else "No conversation data available"




def evaluate_persona_with_logprob(
    client: Any,
    messages: List[Dict[str, str]],
    model: str = "gpt-4o",
    temperature: float = 0.0,
    seed: Optional[int] = None
) -> Dict[str, Any]:
    """Call OpenAI API with logprobs enabled and extract yes/no probabilities.
    
    For deterministic results:
    - temperature must be 0.0
    - seed can be set to a fixed value for reproducibility
    """
    try:
        # Ensure temperature is 0.0 for deterministic results
        if temperature != 0.0:
            print(f"  WARNING: Temperature is {temperature}, not 0.0. Determinism may be affected.")
        
        api_params = {
            "model": model,
            "messages": messages,
            "temperature": 0.0,  # Force to 0.0 for determinism
            "logprobs": True,
            "top_logprobs": 20,  # Get top 20 logprobs to find yes/no probabilities
            "max_tokens": 1  # We only want the first token ("yes" or "no")
        }
        
        # Add seed if provided (for additional determinism)
        if seed is not None:
            api_params["seed"] = seed
        
        response = client.chat.completions.create(**api_params)
        
        choice = response.choices[0]
        message_content = choice.message.content.strip()
        
        # Extract logprobs for the first token
        logprobs_data = choice.logprobs
        if logprobs_data and logprobs_data.content:
            first_token = logprobs_data.content[0]
            token_text = first_token.token
            logprob_value = first_token.logprob
            
            # Calculate linear probability for the chosen token
            linear_prob = np.round(np.exp(logprob_value) * 100, 2)
            
            # Extract yes/no probabilities from top_logprobs
            yes_prob = None
            no_prob = None
            
            # Helper function to check if token is yes/no
            def is_yes_token(token: str) -> bool:
                token_clean = token.strip().lower().rstrip('.,;:!?"\'')
                return token_clean == "yes"
            
            def is_no_token(token: str) -> bool:
                token_clean = token.strip().lower().rstrip('.,;:!?"\'')
                return token_clean == "no"
            
            # Get top alternatives if available
            top_logprobs = []
            if hasattr(first_token, 'top_logprobs') and first_token.top_logprobs:
                for alt in first_token.top_logprobs:
                    alt_token = alt.token
                    alt_logprob = alt.logprob
                    alt_linear_prob = np.round(np.exp(alt_logprob) * 100, 2)
                    
                    top_logprobs.append({
                        "token": alt_token,
                        "logprob": alt_logprob,
                        "linear_prob": float(alt_linear_prob)
                    })
                    
                    # Check for yes/no tokens in top_logprobs
                    # Use the highest probability if multiple matches found
                    if is_yes_token(alt_token):
                        if yes_prob is None or alt_linear_prob > yes_prob:
                            yes_prob = float(alt_linear_prob)
                    elif is_no_token(alt_token):
                        if no_prob is None or alt_linear_prob > no_prob:
                            no_prob = float(alt_linear_prob)
            
            # Also check the chosen token (if not found in top_logprobs)
            if yes_prob is None and is_yes_token(token_text):
                yes_prob = float(linear_prob)
            if no_prob is None and is_no_token(token_text):
                no_prob = float(linear_prob)
            
            return {
                "response": message_content,
                "first_token": token_text,
                "logprob": logprob_value,
                "linear_probability": float(linear_prob),
                "yes_probability": yes_prob,
                "no_probability": no_prob,
                "top_alternatives": top_logprobs,
                "full_response": response
            }
        else:
            return {
                "response": message_content,
                "first_token": message_content[0] if message_content else None,
                "logprob": None,
                "linear_probability": None,
                "yes_probability": None,
                "no_probability": None,
                "error": "No logprobs returned"
            }
            
    except Exception as e:
        return {
            "error": str(e),
            "response": None,
            "logprob": None,
            "linear_probability": None,
            "yes_probability": None,
            "no_probability": None
        }


def main():
    parser = argparse.ArgumentParser(description="Compare persona conversations using logprobs")
    parser.add_argument("--research-id", required=True, help="Research ID")
    parser.add_argument("--persona-1-id", required=True, help="First persona ID to compare")
    parser.add_argument("--persona-2-id", required=True, help="Second persona ID to compare")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use (default: gpt-4o)")
    parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for generation (default: 0.0, forced to 0.0 for determinism)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for deterministic results (optional)")
    args = parser.parse_args()

    research_id = args.research_id
    persona_1_id = args.persona_1_id
    persona_2_id = args.persona_2_id
    model = args.model
    temperature = args.temperature
    seed = args.seed

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
    total_evaluations = len(criteria_keys) * 2  # 2 calls per criterion (one per persona)
    
    # Store individual evaluation results - each call stored independently
    # Structure: {criterion_key: {persona_1_id: result, persona_2_id: result}}
    individual_results = {}
    
    # Evaluate each persona independently for each criterion
    print(f"\n[EVALUATE] Evaluating personas independently across {len(criteria_keys)} criteria ({total_evaluations} total evaluations)...")
    
    evaluation_count = 0
    
    # Make independent calls - store each result immediately to prevent data loss
    for criterion_key in criteria_keys:
        criterion = CRITERIA_DEFINITIONS[criterion_key]
        
        # Initialize storage for this criterion
        individual_results[criterion_key] = {}
        
        print(f"\n  Evaluating criterion: {criterion['name']}...")
        
        # Evaluate Persona 1 - store result immediately
        evaluation_count += 1
        print(f"    [{evaluation_count}/{total_evaluations}] Evaluating Persona 1...")
        
        # Include example only for the very first evaluation
        messages_1 = get_evaluation_messages_for_criterion(
            business_context=business_context,
            question="",  # No specific question, evaluating full conversation
            persona_conversation=persona_1_conversation_text,
            criterion_key=criterion_key,
            include_example=(evaluation_count == 1)
        )
        
        result_1 = evaluate_persona_with_logprob(
            client=client,
            messages=messages_1,
            model=model,
            temperature=temperature,
            seed=seed
        )
        
        # Store Persona 1 result immediately (independent of Persona 2)
        individual_results[criterion_key][persona_1_id] = {
            "persona_id": persona_1_id,
            "criterion_key": criterion_key,
            "criterion_name": criterion["name"],
            "response": result_1.get("response"),
            "yes_probability": result_1.get("yes_probability"),
            "no_probability": result_1.get("no_probability"),
            "logprob": result_1.get("logprob"),
            "linear_probability": result_1.get("linear_probability"),
            "first_token": result_1.get("first_token"),
            "top_alternatives": result_1.get("top_alternatives", []),
            "full_response": result_1.get("full_response"),  # Save full API response
            "error": result_1.get("error"),
            "timestamp": datetime.now().isoformat()
        }
        
        if result_1.get("error"):
            print(f"      ERROR: {result_1['error']}")
        else:
            yes_prob = result_1.get("yes_probability")
            no_prob = result_1.get("no_probability")
            top_alternatives = result_1.get("top_alternatives", [])
            
            if yes_prob is not None:
                print(f"      Persona 1: {yes_prob}% yes" + (f" | {no_prob}% no" if no_prob is not None else ""))
            else:
                print(f"      Persona 1: {result_1.get('response', 'N/A')}")
            
            # Log top token probabilities
            if top_alternatives:
                print(f"      Top token probabilities:")
                for i, alt in enumerate(top_alternatives[:5], 1):  # Show top 5
                    print(f"        {i}. '{alt.get('token', 'N/A')}': {alt.get('linear_prob', 0):.2f}% (logprob: {alt.get('logprob', 0):.4f})")
        
        # Evaluate Persona 2 - store result immediately (independent of Persona 1)
        evaluation_count += 1
        print(f"    [{evaluation_count}/{total_evaluations}] Evaluating Persona 2...")
        
        messages_2 = get_evaluation_messages_for_criterion(
            business_context=business_context,
            question="",  # No specific question, evaluating full conversation
            persona_conversation=persona_2_conversation_text,
            criterion_key=criterion_key,
            include_example=False  # Only include example once
        )
        
        result_2 = evaluate_persona_with_logprob(
            client=client,
            messages=messages_2,
            model=model,
            temperature=temperature,
            seed=seed
        )
        
        # Store Persona 2 result immediately (independent of Persona 1)
        individual_results[criterion_key][persona_2_id] = {
            "persona_id": persona_2_id,
            "criterion_key": criterion_key,
            "criterion_name": criterion["name"],
            "response": result_2.get("response"),
            "yes_probability": result_2.get("yes_probability"),
            "no_probability": result_2.get("no_probability"),
            "logprob": result_2.get("logprob"),
            "linear_probability": result_2.get("linear_probability"),
            "first_token": result_2.get("first_token"),
            "top_alternatives": result_2.get("top_alternatives", []),
            "full_response": result_2.get("full_response"),  # Save full API response
            "error": result_2.get("error"),
            "timestamp": datetime.now().isoformat()
        }
        
        if result_2.get("error"):
            print(f"      ERROR: {result_2['error']}")
        else:
            yes_prob = result_2.get("yes_probability")
            no_prob = result_2.get("no_probability")
            top_alternatives = result_2.get("top_alternatives", [])
            
            if yes_prob is not None:
                print(f"      Persona 2: {yes_prob}% yes" + (f" | {no_prob}% no" if no_prob is not None else ""))
            else:
                print(f"      Persona 2: {result_2.get('response', 'N/A')}")
            
            # Log top token probabilities
            if top_alternatives:
                print(f"      Top token probabilities:")
                for i, alt in enumerate(top_alternatives[:5], 1):  # Show top 5
                    print(f"        {i}. '{alt.get('token', 'N/A')}': {alt.get('linear_prob', 0):.2f}% (logprob: {alt.get('logprob', 0):.4f})")
    
    # Now compare results at the end - using stored individual results
    print(f"\n[COMPARE] Comparing stored results...")
    
    criterion_results = []
    
    for criterion_key in criteria_keys:
        criterion = CRITERIA_DEFINITIONS[criterion_key]
        
        # Get stored results for this criterion
        result_1 = individual_results[criterion_key].get(persona_1_id, {})
        result_2 = individual_results[criterion_key].get(persona_2_id, {})
        
        persona_1_yes_prob = result_1.get("yes_probability")
        persona_1_no_prob = result_1.get("no_probability")
        persona_2_yes_prob = result_2.get("yes_probability")
        persona_2_no_prob = result_2.get("no_probability")
        
        # Determine winner based on yes probabilities
        # If either persona has yes_prob > 30%, use yes_probability comparison (higher = better)
        # If both have yes_prob <= 30%, it's a "no" case - use no_probability comparison (lower = better)
        YES_THRESHOLD = 30.0  # 30% threshold for yes
        
        if persona_1_yes_prob is not None and persona_2_yes_prob is not None:
            # Check if either persona has yes_prob > 30%
            if persona_1_yes_prob > YES_THRESHOLD or persona_2_yes_prob > YES_THRESHOLD:
                # Use yes_probability comparison (higher = better)
                if persona_1_yes_prob > persona_2_yes_prob:
                    winner_id = persona_1_id
                    loser_id = persona_2_id
                    winner_label = "1"
                elif persona_2_yes_prob > persona_1_yes_prob:
                    winner_id = persona_2_id
                    loser_id = persona_1_id
                    winner_label = "2"
                else:
                    winner_id = None
                    loser_id = None
                    winner_label = "tie"
            else:
                # Both have yes_prob <= 30% - it's a "no" case, use no_probability (lower = better)
                if persona_1_no_prob is not None and persona_2_no_prob is not None:
                    if persona_1_no_prob < persona_2_no_prob:
                        winner_id = persona_1_id
                        loser_id = persona_2_id
                        winner_label = "1"
                    elif persona_2_no_prob < persona_1_no_prob:
                        winner_id = persona_2_id
                        loser_id = persona_1_id
                        winner_label = "2"
                    else:
                        winner_id = None
                        loser_id = None
                        winner_label = "tie"
                else:
                    # Fallback to yes_probability if no_prob not available
                    if persona_1_yes_prob > persona_2_yes_prob:
                        winner_id = persona_1_id
                        loser_id = persona_2_id
                        winner_label = "1"
                    elif persona_2_yes_prob > persona_1_yes_prob:
                        winner_id = persona_2_id
                        loser_id = persona_1_id
                        winner_label = "2"
                    else:
                        winner_id = None
                        loser_id = None
                        winner_label = "tie"
        else:
            # Cannot determine winner if both don't have valid probabilities
            # Mark as incomplete comparison
            winner_id = None
            loser_id = None
            winner_label = "incomplete"
            
            # Fallback: use response text if probabilities not available
            response_1 = result_1.get("response", "").strip().lower()
            response_2 = result_2.get("response", "").strip().lower()
            
            if "yes" in response_1 and "no" in response_2:
                winner_id = persona_1_id
                loser_id = persona_2_id
                winner_label = "1"
            elif "yes" in response_2 and "no" in response_1:
                winner_id = persona_2_id
                loser_id = persona_1_id
                winner_label = "2"
        
        # Determine if no_probability was used (both yes_prob <= 30%)
        used_no_probability = False
        if (persona_1_yes_prob is not None and persona_2_yes_prob is not None and 
            persona_1_yes_prob <= YES_THRESHOLD and persona_2_yes_prob <= YES_THRESHOLD):
            used_no_probability = True
        
        criterion_result = {
            "criterion_key": criterion_key,
            "criterion_name": criterion["name"],
            "persona_1": result_1,
            "persona_2": result_2,
            "winner_label": winner_label,
            "winner_persona_id": winner_id,
            "loser_persona_id": loser_id,
            "comparison": {
                "persona_1_yes_prob": persona_1_yes_prob,
                "persona_2_yes_prob": persona_2_yes_prob,
                "persona_1_no_prob": persona_1_no_prob,
                "persona_2_no_prob": persona_2_no_prob,
                "yes_difference": persona_1_yes_prob - persona_2_yes_prob if (persona_1_yes_prob is not None and persona_2_yes_prob is not None) else None,
                "no_difference": persona_1_no_prob - persona_2_no_prob if (persona_1_no_prob is not None and persona_2_no_prob is not None) else None,
                "yes_threshold": YES_THRESHOLD,
                "used_no_probability_comparison": used_no_probability
            }
        }
        
        criterion_results.append(criterion_result)
        
        # Print comparison summary
        if persona_1_yes_prob is not None and persona_2_yes_prob is not None:
            comparison_note = ""
            if used_no_probability:
                comparison_note = f" [using no_prob: P1: {persona_1_no_prob}% vs P2: {persona_2_no_prob}% (both yes <= {YES_THRESHOLD}%)]"
            print(f"  {criterion['name']}: Persona {winner_label} wins (P1: {persona_1_yes_prob}% vs P2: {persona_2_yes_prob}%){comparison_note}")
        elif persona_1_yes_prob is not None:
            print(f"  {criterion['name']}: Persona 1 has result ({persona_1_yes_prob}%), Persona 2 failed")
        elif persona_2_yes_prob is not None:
            print(f"  {criterion['name']}: Persona 2 has result ({persona_2_yes_prob}%), Persona 1 failed")
        else:
            print(f"  {criterion['name']}: Both personas failed or no valid probabilities")
    
    # Calculate overall winner per criterion
    # Only count wins when both personas have valid results for fair comparison
    criterion_wins = {key: {"persona_1": 0, "persona_2": 0, "incomplete": 0} for key in criteria_keys}
    total_persona_1_wins = 0
    total_persona_2_wins = 0
    total_incomplete = 0
    
    for cr in criterion_results:
        result_1 = cr.get("persona_1", {})
        result_2 = cr.get("persona_2", {})
        winner_label = cr.get("winner_label")
        criterion_key = cr.get("criterion_key")
        
        # Only count wins when both have valid yes probabilities (fair comparison)
        if (result_1.get("error") is None and result_2.get("error") is None and
            result_1.get("yes_probability") is not None and result_2.get("yes_probability") is not None):
            if winner_label == "1":
                criterion_wins[criterion_key]["persona_1"] = 1
                total_persona_1_wins += 1
            elif winner_label == "2":
                criterion_wins[criterion_key]["persona_2"] = 1
                total_persona_2_wins += 1
            elif winner_label == "tie":
                # Both tied - don't count as win for either
                pass
            else:
                # Incomplete comparison
                criterion_wins[criterion_key]["incomplete"] = 1
                total_incomplete += 1
        else:
            # Incomplete comparison due to errors or missing probabilities
            criterion_wins[criterion_key]["incomplete"] = 1
            total_incomplete += 1
    
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
        elif wins["persona_1"] == wins["persona_2"] and wins["persona_1"] > 0:
            winner = "tie"
        else:
            winner = "incomplete"
        
        criterion_summary[criterion_key] = {
            "criterion_name": criterion["name"],
            "winner": winner,
            "persona_1_wins": wins["persona_1"],
            "persona_2_wins": wins["persona_2"],
            "incomplete": wins["incomplete"]
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
            "incomplete_comparisons": total_incomplete,
            "total_criteria": len(criteria_keys)
        },
        "criterion_summary": criterion_summary,
        "criteria_results": criterion_results,
        "individual_results": individual_results,  # Store all individual call results
        "persona_1_conversation_preview": persona_1_conversation_text[:500] + "..." if len(persona_1_conversation_text) > 500 else persona_1_conversation_text,
        "persona_2_conversation_preview": persona_2_conversation_text[:500] + "..." if len(persona_2_conversation_text) > 500 else persona_2_conversation_text,
        "model_used": model,
        "temperature": temperature,
        "seed": seed,
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
    
    # Convert to absolute path for clarity
    output_file_abs = os.path.abspath(output_file)

    with open(output_file_abs, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    
    # Verify file was created
    if not os.path.exists(output_file_abs):
        raise FileNotFoundError(f"Failed to create output file: {output_file_abs}")

    # Print results
    print("\n" + "="*60)
    print("COMPARISON RESULTS")
    print("="*60)
    
    # Final Winner Tally
    total_comparable = total_persona_1_wins + total_persona_2_wins
    print("\n" + "-"*60)
    print("FINAL WINNER TALLY")
    print("-"*60)
    
    if overall_winner_label == "tie":
        print(f"\n🏆 RESULT: TIE")
        print(f"   Both personas performed equally")
    elif overall_winner_label == "incomplete":
        print(f"\n⚠️  RESULT: INCOMPLETE")
        print(f"   Unable to determine winner due to missing data")
    else:
        print(f"\n🏆 OVERALL WINNER: Persona {overall_winner_label}")
        print(f"   Winner ID: {overall_winner_id}")
    
    print(f"\n📊 FINAL SCORE:")
    if total_comparable > 0:
        p1_percentage = (total_persona_1_wins / total_comparable) * 100
        p2_percentage = (total_persona_2_wins / total_comparable) * 100
        print(f"   Persona 1: {total_persona_1_wins}/{total_comparable} wins ({p1_percentage:.1f}%)")
        print(f"   Persona 2: {total_persona_2_wins}/{total_comparable} wins ({p2_percentage:.1f}%)")
    else:
        print(f"   Persona 1: {total_persona_1_wins} wins")
        print(f"   Persona 2: {total_persona_2_wins} wins")
    
    if total_incomplete > 0:
        print(f"\n   Incomplete Comparisons: {total_incomplete}/{len(criteria_keys)}")
    
    print("-"*60)
    
    print(f"\nCriterion-wise Summary:")
    for criterion_key, summary in criterion_summary.items():
        print(f"  {summary['criterion_name']}:")
        print(f"    Winner: Persona {summary['winner']}")
        print(f"    Persona 1: {summary['persona_1_wins']} wins | Persona 2: {summary['persona_2_wins']} wins", end="")
        if summary.get('incomplete', 0) > 0:
            print(f" | Incomplete: {summary['incomplete']}")
        else:
            print()
    
    print(f"\nCriterion Results:")
    for cr in criterion_results:
        p1 = cr.get("persona_1", {})
        p2 = cr.get("persona_2", {})
        if p1.get("error") is None and p2.get("error") is None:
            p1_yes = p1.get("yes_probability", "N/A")
            p2_yes = p2.get("yes_probability", "N/A")
            print(f"  {cr['criterion_name']}: Persona {cr['winner_label']} wins")
            print(f"    Persona 1: {p1_yes}% yes | Persona 2: {p2_yes}% yes")
        else:
            errors = []
            if p1.get("error"):
                errors.append(f"Persona 1: {p1['error']}")
            if p2.get("error"):
                errors.append(f"Persona 2: {p2['error']}")
            print(f"  {cr.get('criterion_name', 'Unknown')}: ERROR - {'; '.join(errors)}")
    
    print(f"\nResults saved to: {output_file_abs}")
    print(f"  (Relative path: {output_file})")

    return output


if __name__ == "__main__":
    main()

