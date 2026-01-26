"""
Analyze and compare interview results between DeepPersona and regular personas.

This script:
1. Fetches interview transcripts from Firestore
2. Groups by persona source (deeppersona vs regular)
3. Calculates metrics (scores, response length, emotional depth)
4. Generates comparison report

Usage:
    python analyze_results.py --research-id 6x4zztjWGiN7ajKF4Gf9
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import firebase_admin
from firebase_admin import credentials, firestore


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
        else:
            firebase_admin.initialize_app()

    return firestore.client()


def fetch_research(db, research_id: str) -> Dict[str, Any]:
    """Fetch research document."""
    doc = db.collection("research").document(research_id).get()
    if not doc.exists:
        raise ValueError(f"Research {research_id} not found")
    return doc.to_dict()


def fetch_interviews(db, research_id: str) -> List[Dict[str, Any]]:
    """Fetch all interview documents for a research."""
    interviews = []
    docs = db.collection("interviews").where("researchId", "==", research_id).stream()

    for doc in docs:
        interview = doc.to_dict()
        interview["_id"] = doc.id
        interviews.append(interview)

    return interviews


def get_persona_source(persona: Dict[str, Any]) -> str:
    """Get the source type of a persona."""
    return persona.get("source", "regular")


def calculate_metrics(conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate metrics from conversation history."""
    if not conversation_history:
        return {
            "total_questions": 0,
            "avg_score": 0,
            "avg_emotional": 0,
            "avg_tools": 0,
            "avg_response_length": 0,
            "total_word_count": 0,
            "scores": [],
            "response_lengths": []
        }

    scores = []
    emotional_scores = []
    tools_scores = []
    response_lengths = []

    for conv in conversation_history:
        # Skip probe questions for main metrics
        if conv.get("isProbe"):
            continue

        answer = conv.get("answer", "")
        word_count = len(answer.split())
        response_lengths.append(word_count)

        score = conv.get("score", 0)
        if score:
            scores.append(float(score))

        emotional = conv.get("emotional", 0)
        if emotional:
            emotional_scores.append(float(emotional))

        tools = conv.get("tools", 0)
        if tools:
            tools_scores.append(float(tools))

    return {
        "total_questions": len(response_lengths),
        "avg_score": sum(scores) / len(scores) if scores else 0,
        "avg_emotional": sum(emotional_scores) / len(emotional_scores) if emotional_scores else 0,
        "avg_tools": sum(tools_scores) / len(tools_scores) if tools_scores else 0,
        "avg_response_length": sum(response_lengths) / len(response_lengths) if response_lengths else 0,
        "total_word_count": sum(response_lengths),
        "scores": scores,
        "response_lengths": response_lengths
    }


def analyze_specificity(conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze specificity of responses (looking for concrete examples, numbers, names)."""
    specific_markers = [
        # Numbers and dates
        r'\d+',
        # Specific time references
        'last week', 'last month', 'yesterday', 'last year',
        # Personal examples
        'for example', 'for instance', 'specifically',
        # Named entities (rough heuristic)
        'we used', 'I tried', 'our team', 'my company'
    ]

    import re

    total_specific = 0
    total_answers = 0

    for conv in conversation_history:
        if conv.get("isProbe"):
            continue

        answer = conv.get("answer", "").lower()
        total_answers += 1

        # Count specific markers
        markers_found = 0
        for marker in specific_markers:
            if marker.startswith(r'\\'):
                if re.search(marker, answer):
                    markers_found += 1
            else:
                if marker in answer:
                    markers_found += 1

        if markers_found >= 2:
            total_specific += 1

    return {
        "specific_responses": total_specific,
        "total_responses": total_answers,
        "specificity_rate": total_specific / total_answers if total_answers > 0 else 0
    }


def generate_comparison_report(
    research: Dict[str, Any],
    interviews: List[Dict[str, Any]],
    personas_by_id: Dict[str, Dict[str, Any]]
) -> str:
    """Generate a markdown comparison report."""
    research_name = research.get("researchName", "Unknown")
    research_id = research.get("id", "Unknown")

    # Group interviews by persona source
    deep_interviews = []
    regular_interviews = []

    for interview in interviews:
        persona_id = interview.get("personaId")
        persona = personas_by_id.get(persona_id, {})
        source = get_persona_source(persona)

        if source == "deeppersona":
            deep_interviews.append((interview, persona))
        else:
            regular_interviews.append((interview, persona))

    # Calculate aggregate metrics
    deep_metrics = {"scores": [], "emotional": [], "tools": [], "lengths": [], "specificity": []}
    regular_metrics = {"scores": [], "emotional": [], "tools": [], "lengths": [], "specificity": []}

    report_lines = [
        f"# Interview Comparison Report",
        f"",
        f"**Research**: {research_name}",
        f"**Research ID**: {research_id}",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"---",
        f"",
        f"## Summary",
        f"",
        f"| Metric | DeepPersona ({len(deep_interviews)}) | Regular ({len(regular_interviews)}) |",
        f"|--------|-------------|---------|",
    ]

    # Process DeepPersona interviews
    for interview, persona in deep_interviews:
        conv_history = interview.get("conversationHistory", [])
        metrics = calculate_metrics(conv_history)
        specificity = analyze_specificity(conv_history)

        deep_metrics["scores"].extend(metrics["scores"])
        deep_metrics["emotional"].append(metrics["avg_emotional"])
        deep_metrics["tools"].append(metrics["avg_tools"])
        deep_metrics["lengths"].extend(metrics["response_lengths"])
        deep_metrics["specificity"].append(specificity["specificity_rate"])

    # Process Regular interviews
    for interview, persona in regular_interviews:
        conv_history = interview.get("conversationHistory", [])
        metrics = calculate_metrics(conv_history)
        specificity = analyze_specificity(conv_history)

        regular_metrics["scores"].extend(metrics["scores"])
        regular_metrics["emotional"].append(metrics["avg_emotional"])
        regular_metrics["tools"].append(metrics["avg_tools"])
        regular_metrics["lengths"].extend(metrics["response_lengths"])
        regular_metrics["specificity"].append(specificity["specificity_rate"])

    # Calculate averages
    def safe_avg(lst):
        return sum(lst) / len(lst) if lst else 0

    deep_avg_score = safe_avg(deep_metrics["scores"])
    regular_avg_score = safe_avg(regular_metrics["scores"])

    deep_avg_emotional = safe_avg(deep_metrics["emotional"])
    regular_avg_emotional = safe_avg(regular_metrics["emotional"])

    deep_avg_tools = safe_avg(deep_metrics["tools"])
    regular_avg_tools = safe_avg(regular_metrics["tools"])

    deep_avg_length = safe_avg(deep_metrics["lengths"])
    regular_avg_length = safe_avg(regular_metrics["lengths"])

    deep_avg_specificity = safe_avg(deep_metrics["specificity"])
    regular_avg_specificity = safe_avg(regular_metrics["specificity"])

    # Add metrics to report
    report_lines.extend([
        f"| Avg Judge Score | {deep_avg_score:.2f} | {regular_avg_score:.2f} |",
        f"| Avg Emotional Depth | {deep_avg_emotional:.2f} | {regular_avg_emotional:.2f} |",
        f"| Avg Tools/Framework | {deep_avg_tools:.2f} | {regular_avg_tools:.2f} |",
        f"| Avg Response Length | {deep_avg_length:.0f} words | {regular_avg_length:.0f} words |",
        f"| Specificity Rate | {deep_avg_specificity:.1%} | {regular_avg_specificity:.1%} |",
        f"",
    ])

    # Winner summary
    report_lines.extend([
        f"## Analysis",
        f"",
    ])

    winners = []
    if deep_avg_score > regular_avg_score:
        winners.append(("Judge Score", "DeepPersona", deep_avg_score - regular_avg_score))
    elif regular_avg_score > deep_avg_score:
        winners.append(("Judge Score", "Regular", regular_avg_score - deep_avg_score))

    if deep_avg_emotional > regular_avg_emotional:
        winners.append(("Emotional Depth", "DeepPersona", deep_avg_emotional - regular_avg_emotional))
    elif regular_avg_emotional > deep_avg_emotional:
        winners.append(("Emotional Depth", "Regular", regular_avg_emotional - deep_avg_emotional))

    if deep_avg_length > regular_avg_length:
        winners.append(("Response Length", "DeepPersona", deep_avg_length - regular_avg_length))
    elif regular_avg_length > deep_avg_length:
        winners.append(("Response Length", "Regular", regular_avg_length - deep_avg_length))

    for metric, winner, diff in winners:
        report_lines.append(f"- **{metric}**: {winner} wins by {diff:.2f}")

    # Detailed persona breakdown
    report_lines.extend([
        f"",
        f"---",
        f"",
        f"## Individual Persona Results",
        f"",
    ])

    # DeepPersona details
    report_lines.append(f"### DeepPersona Interviews")
    report_lines.append(f"")

    for interview, persona in deep_interviews:
        name = persona.get("name", "Unknown")
        profile_id = persona.get("profileId", "?")
        conv_history = interview.get("conversationHistory", [])
        metrics = calculate_metrics(conv_history)

        report_lines.extend([
            f"**{name}** (Profile: {profile_id})",
            f"- Questions: {metrics['total_questions']}",
            f"- Avg Score: {metrics['avg_score']:.2f}",
            f"- Avg Response: {metrics['avg_response_length']:.0f} words",
            f"- Summary: {len(persona.get('summary', ''))} chars",
            f"",
        ])

    # Regular details
    report_lines.append(f"### Regular Persona Interviews")
    report_lines.append(f"")

    for interview, persona in regular_interviews:
        name = persona.get("name", "Unknown")
        profile_id = persona.get("profileId", "?")
        conv_history = interview.get("conversationHistory", [])
        metrics = calculate_metrics(conv_history)

        report_lines.extend([
            f"**{name}** (Profile: {profile_id})",
            f"- Questions: {metrics['total_questions']}",
            f"- Avg Score: {metrics['avg_score']:.2f}",
            f"- Avg Response: {metrics['avg_response_length']:.0f} words",
            f"",
        ])

    # Sample responses comparison
    report_lines.extend([
        f"---",
        f"",
        f"## Sample Response Comparison",
        f"",
    ])

    # Get first question from each type
    if deep_interviews and regular_interviews:
        deep_conv = deep_interviews[0][0].get("conversationHistory", [])
        regular_conv = regular_interviews[0][0].get("conversationHistory", [])

        if deep_conv and regular_conv:
            # Find matching question
            deep_q1 = next((c for c in deep_conv if not c.get("isProbe")), None)
            regular_q1 = next((c for c in regular_conv if not c.get("isProbe")), None)

            if deep_q1 and regular_q1:
                report_lines.extend([
                    f"### Question: {deep_q1.get('question', 'N/A')[:100]}...",
                    f"",
                    f"**DeepPersona Response:**",
                    f"> {deep_q1.get('answer', 'N/A')[:500]}...",
                    f"",
                    f"**Regular Response:**",
                    f"> {regular_q1.get('answer', 'N/A')[:500]}...",
                    f"",
                ])

    return "\n".join(report_lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze interview comparison results")
    parser.add_argument("--research-id", required=True, help="Research ID to analyze")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    research_id = args.research_id

    print(f"Analyzing interviews for research: {research_id}")

    # Initialize Firebase
    db = init_firebase()

    # Fetch data
    print("Fetching research document...")
    research = fetch_research(db, research_id)

    print("Fetching interviews...")
    interviews = fetch_interviews(db, research_id)
    print(f"Found {len(interviews)} interviews")

    if not interviews:
        print("No interviews found. Make sure interviews have been run.")
        return

    # Build persona lookup
    personas = research.get("step2", {}).get("selectedPersonas", [])
    personas_by_id = {p.get("id"): p for p in personas}

    # Generate report
    print("Generating comparison report...")
    report = generate_comparison_report(research, interviews, personas_by_id)

    # Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report saved to: {args.output}")
    else:
        print("\n" + "="*60)
        print(report)

    # Also save to default location
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    default_output = os.path.join(output_dir, f"comparison_report_{research_id}.md")
    with open(default_output, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport also saved to: {default_output}")


if __name__ == "__main__":
    main()
