"""
Main comparison script for DeepPersona vs Regular Persona interviews.

This script:
1. Fetches research document from Firestore
2. Generates DeepPersonas for each profile
3. Transforms them to regular schema
4. Backs up existing personas
5. Replaces one persona per profile with DeepPersona version
6. Updates Firestore

Usage:
    python run_comparison.py --research-id 6x4zztjWGiN7ajKF4Gf9
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Add parent directories to path for imports
DEEPPERSONA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUNCTIONS_DIR = os.path.dirname(DEEPPERSONA_DIR)
sys.path.insert(0, DEEPPERSONA_DIR)
sys.path.insert(0, FUNCTIONS_DIR)

import firebase_admin
from firebase_admin import credentials, firestore

# Import directly from files (avoiding __init__.py which has outdated imports)
from generate_user_profile.select_attributes import generate_user_profile, get_selected_attributes
from generate_user_profile.generate_profile import generate_single_profile
from transform_persona import transform_to_regular_persona, get_persona_summary


# Initialize Firebase
def init_firebase():
    """Initialize Firebase Admin SDK."""
    if not firebase_admin._apps:
        # Try to find service account key
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
            # Try default credentials
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


def get_profiles_from_research(research: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract profiles from research document."""
    profiles = research.get("step2", {}).get("profiles", [])
    if not profiles:
        raise ValueError("No profiles found in research")
    return profiles


def get_personas_from_research(research: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract personas from research document."""
    return research.get("step2", {}).get("selectedPersonas", [])


def backup_personas(personas: List[Dict[str, Any]], research_id: str) -> str:
    """Backup existing personas to a JSON file."""
    backup_dir = os.path.join(os.path.dirname(__file__), "backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"personas_backup_{research_id}_{timestamp}.json")

    # Convert datetime objects to strings for JSON serialization
    serializable_personas = []
    for p in personas:
        persona_copy = {}
        for k, v in p.items():
            if isinstance(v, datetime):
                persona_copy[k] = v.isoformat()
            elif hasattr(v, 'isoformat'):  # Handle Firestore timestamps
                persona_copy[k] = v.isoformat() if hasattr(v, 'isoformat') else str(v)
            else:
                persona_copy[k] = v
        serializable_personas.append(persona_copy)

    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(serializable_personas, f, indent=2, default=str)

    print(f"Backed up {len(personas)} personas to: {backup_file}")
    return backup_file


def generate_deeppersona_for_profile(profile: Dict[str, Any], problem_statement: str) -> Dict[str, Any]:
    """
    Generate a DeepPersona aligned with the given profile.

    Args:
        profile: Profile dictionary with role, industry info
        problem_statement: The research problem statement for context

    Returns:
        Dictionary with base_profile, complete_persona, and backstory
    """
    print(f"\n{'='*60}")
    print(f"Generating DeepPersona for profile: {profile.get('name', 'Unknown')}")
    print(f"{'='*60}")

    # Generate base profile
    print("\n[1/3] Generating base profile...")
    base_profile = generate_user_profile()

    print(f"  Age: {base_profile.get('age_info', {}).get('age', '?')}")
    print(f"  Gender: {base_profile.get('gender', '?')}")
    print(f"  Location: {base_profile.get('location', {}).get('city', '?')}, {base_profile.get('location', {}).get('country', '?')}")
    print(f"  Career: {base_profile.get('career_info', {}).get('status', '?')}")

    # Select attributes
    print("\n[2/3] Selecting attributes via vector search...")
    selected_attributes = get_selected_attributes(base_profile, attribute_count=200)
    print(f"  Selected {len(selected_attributes) if isinstance(selected_attributes, list) else 'N/A'} attributes")

    # Generate complete persona
    print("\n[3/3] Generating complete persona...")
    complete_persona = generate_single_profile(
        template=None,
        profile_index=0,
        attribute_count=200,
        base_profile=base_profile,
        selected_attributes=selected_attributes
    )

    backstory = complete_persona.get("Summary", "")
    print(f"  Backstory length: {len(backstory)} characters")

    return {
        "base_profile": base_profile,
        "complete_persona": complete_persona,
        "backstory": backstory
    }


def replace_persona_in_list(
    personas: List[Dict[str, Any]],
    profile_id: str,
    new_persona: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Replace one persona for a given profile with a new one.

    Args:
        personas: List of all personas
        profile_id: Profile ID to replace persona for
        new_persona: New persona to insert

    Returns:
        Tuple of (updated_personas_list, replaced_persona)
    """
    updated_personas = []
    replaced_persona = None
    replaced = False

    for persona in personas:
        if persona.get("profileId") == profile_id and not replaced:
            # Replace the first persona for this profile
            replaced_persona = persona
            updated_personas.append(new_persona)
            replaced = True
            print(f"  Replacing: {persona.get('name', 'Unknown')} -> {new_persona.get('name', 'Unknown')}")
        else:
            updated_personas.append(persona)

    if not replaced:
        print(f"  Warning: No persona found for profile {profile_id}, adding new one")
        updated_personas.append(new_persona)

    return updated_personas, replaced_persona


def update_firestore(db, research_id: str, updated_personas: List[Dict[str, Any]]):
    """Update Firestore with the new personas list."""
    doc_ref = db.collection("research").document(research_id)

    doc_ref.update({
        "step2.selectedPersonas": updated_personas,
        "step2.lastUpdated": datetime.now(),
        "dateUpdated": datetime.now()
    })

    print(f"\nFirestore updated with {len(updated_personas)} personas")


def main():
    parser = argparse.ArgumentParser(description="Run DeepPersona comparison")
    parser.add_argument("--research-id", required=True, help="Research ID to process")
    parser.add_argument("--dry-run", action="store_true", help="Generate personas without updating Firestore")
    args = parser.parse_args()

    research_id = args.research_id
    dry_run = args.dry_run

    print(f"\n{'#'*60}")
    print(f"# DeepPersona Comparison Script")
    print(f"# Research ID: {research_id}")
    print(f"# Dry Run: {dry_run}")
    print(f"{'#'*60}")

    # Initialize Firebase
    print("\n[INIT] Connecting to Firebase...")
    db = init_firebase()

    # Fetch research
    print(f"\n[FETCH] Loading research document...")
    research = fetch_research(db, research_id)
    print(f"  Research Name: {research.get('researchName', 'Unknown')}")
    print(f"  Current Step: {research.get('currentStep', '?')}")

    # Get problem statement
    step1 = research.get("step1", {})
    problem_statement = step1.get("problemStatement") or step1.get("researchGoal") or ""
    print(f"  Problem Statement: {problem_statement[:100]}...")

    # Get profiles and personas
    profiles = get_profiles_from_research(research)
    personas = get_personas_from_research(research)

    print(f"\n[INFO] Found {len(profiles)} profiles and {len(personas)} personas")

    # Show current personas
    print("\n[CURRENT PERSONAS]")
    for p in personas:
        source = p.get("source", "regular")
        print(f"  - {p.get('name', 'Unknown')} (Profile: {p.get('profileId', '?')}, Source: {source})")

    # Backup existing personas
    print("\n[BACKUP] Backing up existing personas...")
    backup_file = backup_personas(personas, research_id)

    # Find profiles that have existing personas (only generate DeepPersonas for these)
    profile_ids_with_personas = set(p.get("profileId") for p in personas)
    profiles_to_process = [p for p in profiles if p.get("id") in profile_ids_with_personas]

    print(f"\n[INFO] Only {len(profiles_to_process)} profiles have personas, processing only those:")
    for p in profiles_to_process:
        print(f"  - {p.get('name', 'Unknown')} ({p.get('id', '?')[:12]}...)")

    # Generate DeepPersonas only for profiles with existing personas
    print("\n[GENERATE] Creating DeepPersonas for profiles with existing personas...")
    deep_personas = {}

    for profile in profiles_to_process:
        profile_id = profile.get("id")
        profile_name = profile.get("name", "Unknown")
        profile_role = profile.get("role", profile_name)  # Use profile name as role if not specified
        profile_industry = profile.get("industry")

        # Generate DeepPersona
        deep_persona_data = generate_deeppersona_for_profile(profile, problem_statement)

        # Transform to regular schema
        print(f"\n[TRANSFORM] Converting to regular persona schema...")
        transformed_persona = transform_to_regular_persona(
            deep_persona=deep_persona_data,
            profile_id=profile_id,
            profile_role=profile_role,
            profile_industry=profile_industry
        )

        print(f"  Result: {get_persona_summary(transformed_persona)}")
        deep_personas[profile_id] = transformed_persona

    # Replace one persona per profile
    print("\n[REPLACE] Replacing one persona per profile...")
    updated_personas = personas.copy()
    replaced_personas = []

    for profile_id, new_persona in deep_personas.items():
        updated_personas, replaced = replace_persona_in_list(
            updated_personas,
            profile_id,
            new_persona
        )
        if replaced:
            replaced_personas.append(replaced)

    # Save replaced personas to backup
    if replaced_personas:
        replaced_backup = backup_personas(replaced_personas, f"{research_id}_replaced")
        print(f"  Saved replaced personas to: {replaced_backup}")

    # Show final personas
    print("\n[FINAL PERSONAS]")
    for p in updated_personas:
        source = p.get("source", "regular")
        print(f"  - {p.get('name', 'Unknown')} (Profile: {p.get('profileId', '?')}, Source: {source})")

    # Update Firestore (unless dry run)
    if dry_run:
        print("\n[DRY RUN] Skipping Firestore update")

        # Save to local file instead
        output_file = os.path.join(
            os.path.dirname(__file__),
            "output",
            f"comparison_personas_{research_id}.json"
        )
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(updated_personas, f, indent=2, default=str)
        print(f"  Saved to: {output_file}")
    else:
        print("\n[UPDATE] Updating Firestore...")
        update_firestore(db, research_id, updated_personas)

    print("\n" + "="*60)
    print("COMPARISON SETUP COMPLETE")
    print("="*60)
    print(f"\nNext Steps:")
    print(f"  1. Trigger interviews: Call run_persona_cloud_function with research_id={research_id}")
    print(f"  2. Wait for interviews to complete")
    print(f"  3. Run analyze_results.py to compare transcripts")
    print(f"\nBackup location: {backup_file}")

    return updated_personas


if __name__ == "__main__":
    main()
