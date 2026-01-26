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
from typing import Dict, List, Any, Tuple, Optional

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
from generate_user_profile.based_data import (
    generate_age_info,
    generate_gender,
    generate_location,
    generate_career_info,
    generate_personal_values,
    generate_life_attitude,
    generate_personal_story,
    generate_interests_and_hobbies
)
from transform_persona import transform_to_regular_persona, get_persona_summary

# ============================================================================
# ANCHOR ATTRIBUTES DEFINITION (matching paper methodology)
# ============================================================================
# Paper defines 6 "non-negotiable anchor attributes" that form the foundation:
# 1. Age (and age group)
# 2. Location (city, country)
# 3. Career (job/role)
# 4. Personal Values (what they believe in)
# 5. Life Attitude (how they approach life)
# 6. Hobbies/Interests (what they like to do)

ANCHOR_ATTRIBUTES = {
    "age_info": {
        "required_fields": ["age", "age_group"],
        "description": "Age and age group classification"
    },
    "location": {
        "required_fields": ["city", "country"],
        "description": "Geographic location"
    },
    "career_info": {
        "required_fields": ["status"],
        "description": "Career and occupation"
    },
    "personal_values": {
        "required_fields": ["values_orientation"],
        "description": "Core values and beliefs"
    },
    "life_attitude": {
        "required_fields": ["attitude", "coping_mechanism"],
        "description": "Life outlook and coping strategies"
    },
    "interests": {
        "required_fields": ["interests"],
        "description": "Hobbies and interests"
    }
}

# Age group thresholds (configurable, matching based_data.py logic)
AGE_GROUP_THRESHOLDS = {
    "young_adult": 29,
    "adult": 45,
    "middle_aged": 65
}

def get_age_group(age: int) -> str:
    """Get age group based on configurable thresholds."""
    if age <= AGE_GROUP_THRESHOLDS["young_adult"]:
        return "young_adult"
    elif age <= AGE_GROUP_THRESHOLDS["adult"]:
        return "adult"
    elif age <= AGE_GROUP_THRESHOLDS["middle_aged"]:
        return "middle_aged"
    else:
        return "senior"

def validate_anchor_attributes(base_profile: dict) -> tuple[bool, List[str]]:
    """Check that all required anchor attributes are present.
    
    Returns:
        (is_valid, missing_anchors): Tuple of validation result and list of missing anchor names
    """
    missing = []
    for anchor_name, anchor_config in ANCHOR_ATTRIBUTES.items():
        if anchor_name not in base_profile:
            missing.append(anchor_name)
            continue
        anchor_data = base_profile[anchor_name]
        if not isinstance(anchor_data, dict):
            missing.append(anchor_name)
            continue
        for required_field in anchor_config["required_fields"]:
            if required_field not in anchor_data:
                missing.append(anchor_name)
                break
    return (len(missing) == 0, missing)


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


def get_persona_by_id(db, research_id: str, persona_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a specific persona by ID from research document."""
    research = fetch_research(db, research_id)
    personas = get_personas_from_research(research)
    
    for persona in personas:
        if persona.get("id") == persona_id:
            return persona
    
    return None


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


def extract_base_profile_from_persona(persona: Dict[str, Any], profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Extract anchor attributes from existing persona, then generate missing ones.
    
    Strategy:
    1. FIRST: Extract all possible anchor attributes from persona (flexible field mapping)
    2. SECOND: Check which of the 6 anchor attributes are missing
    3. THIRD: Generate only missing anchor attributes using extracted data as context
    
    Args:
        persona: Existing persona dictionary
        profile: Optional profile dictionary containing primary/secondary attributes definition
        
    Returns:
        Base profile dictionary with all 6 anchor attributes present
    """
    base_profile = {}
    
    # ========================================================================
    # STEP 1: EXTRACT ALL POSSIBLE DATA FROM PERSONA
    # ========================================================================
    
    # Extract age_info
    if "age" in persona:
        age = persona["age"]
        base_profile["age_info"] = {
            "age": age,
            "age_group": get_age_group(age)
        }
    
    # Extract gender (needed for generating other attributes)
    if "gender" in persona:
        base_profile["gender"] = persona["gender"]
    
    # Extract location (flexible parsing)
    if "location" in persona:
        location_str = str(persona["location"])
        location_parts = location_str.split(",")
        base_profile["location"] = {
            "city": location_parts[0].strip() if len(location_parts) > 0 else "Unknown",
            "country": location_parts[1].strip() if len(location_parts) > 1 else "Unknown"
        }
    
    # Extract career_info (flexible field mapping)
    if "role" in persona or "experience" in persona:
        career_info = {}
        if "role" in persona:
            career_info["status"] = persona["role"]
        elif "experience" in persona:
            career_info["status"] = persona["experience"]
        if "experience" in persona and "role" in persona:
            career_info["experience"] = persona["experience"]
        base_profile["career_info"] = career_info
    
    # Extract personal_values (if stored directly in persona)
    if "personal_values" in persona:
        pv = persona["personal_values"]
        if isinstance(pv, dict):
            base_profile["personal_values"] = pv
        elif isinstance(pv, str):
            base_profile["personal_values"] = {"values_orientation": pv}
    
    # Extract life_attitude (if stored directly in persona)
    if "life_attitude" in persona:
        la = persona["life_attitude"]
        if isinstance(la, dict):
            base_profile["life_attitude"] = la
        elif isinstance(la, str):
            # Try to parse as JSON or use as attitude
            try:
                import json
                base_profile["life_attitude"] = json.loads(la)
            except:
                base_profile["life_attitude"] = {"attitude": la, "coping_mechanism": ""}
    
    # Extract interests (if stored directly in persona)
    if "interests" in persona:
        interests = persona["interests"]
        if isinstance(interests, dict):
            base_profile["interests"] = interests
        elif isinstance(interests, list):
            base_profile["interests"] = {"interests": interests}
        elif isinstance(interests, str):
            # Try to parse as JSON or split by comma
            try:
                import json
                parsed = json.loads(interests)
                base_profile["interests"] = {"interests": parsed if isinstance(parsed, list) else [parsed]}
            except:
                base_profile["interests"] = {"interests": [i.strip() for i in interests.split(",")]}
    
    # Extract primary attributes from persona if profile provides the list
    primary_attributes = {}
    if profile:
        profile_attrs = profile.get("attributes", {})
        primary_attr_names = profile_attrs.get("primary", [])
        
        # Extract values for each primary attribute from persona (only if present)
        for attr_name in primary_attr_names:
            if attr_name in persona:
                primary_attributes[attr_name] = persona[attr_name]
    
    # Also check for common primary attributes directly in persona
    common_primary_attrs = [
        "industry_type", "industry", 
        "size_of_business", "company_size_range",
        "decision_authority_level", 
        "average_monthly_spending_on_marketing",
        "frequency_of_service_use_last_30d"
    ]
    for attr_name in common_primary_attrs:
        if attr_name in persona and attr_name not in primary_attributes:
            primary_attributes[attr_name] = persona[attr_name]
    
    # Store primary attributes if any were found
    if primary_attributes:
        base_profile["_primary_attributes"] = primary_attributes
    
    # ========================================================================
    # STEP 2: CHECK WHAT'S MISSING AND GENERATE ONLY MISSING ANCHORS
    # ========================================================================
    
    is_valid, missing_anchors = validate_anchor_attributes(base_profile)
    
    if not is_valid:
        print(f"  Missing anchor attributes: {', '.join(missing_anchors)}")
        print(f"  Generating missing anchor attributes...")
        
        # Ensure we have age and gender first (needed for other generations)
        if "age_info" not in base_profile:
            base_profile["age_info"] = generate_age_info()
            print(f"    ✓ Generated age_info")
        
        if "gender" not in base_profile:
            base_profile["gender"] = generate_gender()
            print(f"    ✓ Generated gender")
        
        age = base_profile["age_info"]["age"]
        gender = base_profile["gender"]
        
        # Generate location if missing
        if "location" not in base_profile:
            base_profile["location"] = generate_location()
            print(f"    ✓ Generated location")
        
        location = base_profile["location"]
        
        # Generate career_info if missing (depends on age)
        if "career_info" not in base_profile:
            base_profile["career_info"] = generate_career_info(age)
            print(f"    ✓ Generated career_info")
        
        occupation = base_profile["career_info"]["status"]
        
        # Generate personal_values if missing (depends on age, gender, occupation, location)
        if "personal_values" not in base_profile:
            base_profile["personal_values"] = generate_personal_values(
                age, gender, occupation, location
            )
            print(f"    ✓ Generated personal_values")
        
        values_orientation = base_profile["personal_values"]["values_orientation"]
        
        # Generate life_attitude if missing (depends on age, gender, occupation, location, values)
        if "life_attitude" not in base_profile:
            base_profile["life_attitude"] = generate_life_attitude(
                age, gender, occupation, location, values_orientation
            )
            print(f"    ✓ Generated life_attitude")
        
        # Generate interests if missing (depends on personal_story, but we can generate minimal story)
        if "interests" not in base_profile:
            # Generate a minimal personal story to derive interests from
            life_attitude = base_profile["life_attitude"]
            personal_story = generate_personal_story(
                age, gender, occupation, location, values_orientation, life_attitude
            )
            base_profile["interests"] = generate_interests_and_hobbies(personal_story)
            print(f"    ✓ Generated interests")
    
    # Final validation
    is_valid, missing_anchors = validate_anchor_attributes(base_profile)
    if not is_valid:
        raise ValueError(f"Failed to generate all anchor attributes. Still missing: {', '.join(missing_anchors)}")
    
    print(f"  ✓ All 6 anchor attributes present and validated")
    
    return base_profile


def generate_deeppersona_from_existing_persona(
    persona: Dict[str, Any],
    profile: Optional[Dict[str, Any]] = None,
    attribute_count: int = 200
) -> Dict[str, Any]:
    """
    Generate a DeepPersona using the same primary attributes as existing persona,
    with similar secondary attributes via vector similarity search.
    
    Args:
        persona: Existing persona dictionary
        profile: Optional profile dictionary containing primary/secondary attributes definition
        attribute_count: Number of attributes to select (default: 200)
        
    Returns:
        Dictionary with base_profile, complete_persona, and summary
    """
    print(f"\n{'='*60}")
    print(f"Generating DeepPersona from existing persona: {persona.get('name', 'Unknown')}")
    print(f"{'='*60}")
    
    # Extract base profile from existing persona (includes primary attributes)
    print("\n[1/4] Extracting primary attributes from existing persona...")
    base_profile = extract_base_profile_from_persona(persona, profile)
    
    primary_attrs = base_profile.get("_primary_attributes", {})
    print(f"  Age: {base_profile.get('age_info', {}).get('age', '?')}")
    print(f"  Gender: {base_profile.get('gender', '?')}")
    print(f"  Location: {base_profile.get('location', {}).get('city', '?')}, {base_profile.get('location', {}).get('country', '?')}")
    print(f"  Career: {base_profile.get('career_info', {}).get('status', '?')}")
    if primary_attrs:
        print(f"  Primary attributes extracted: {len(primary_attrs)} ({', '.join(list(primary_attrs.keys())[:3])}...)")
    
    # Select attributes using vector similarity search (will find similar secondary attributes)
    # The base_profile already contains primary attributes, so vector search will find similar ones
    print(f"\n[2/4] Selecting similar secondary attributes via vector search...")
    selected_attributes = get_selected_attributes(base_profile, attribute_count=attribute_count)
    print(f"  Selected {len(selected_attributes) if isinstance(selected_attributes, list) else 'N/A'} attributes")
    
    # Generate complete persona using the base profile and selected attributes
    print("\n[3/4] Generating complete persona with similar attributes...")
    complete_persona = generate_single_profile(
        template=None,
        profile_index=0,
        attribute_count=attribute_count,
        base_profile=base_profile,
        selected_attributes=selected_attributes
    )
    
    summary = complete_persona.get("Summary", "")
    print(f"  Summary length: {len(summary)} characters")
    
    return {
        "base_profile": base_profile,
        "complete_persona": complete_persona,
        "summary": summary
    }


def generate_deeppersona_for_profile(profile: Dict[str, Any], problem_statement: str) -> Dict[str, Any]:
    """
    Generate a DeepPersona aligned with the given profile.

    Args:
        profile: Profile dictionary with role, industry info
        problem_statement: The research problem statement for context

    Returns:
        Dictionary with base_profile, complete_persona, and summary
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


def add_deeppersona_to_research(
    db,
    research_id: str,
    base_persona_id: str,
    deep_persona_data: Dict[str, Any],
    profile_id: str,
    profile_role: str,
    profile_industry: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Generate and add a DeepPersona to research document with reference to base persona.
    
    Args:
        db: Firestore database client
        research_id: Research document ID
        base_persona_id: ID of the base persona this DeepPersona is derived from
        deep_persona_data: Deep persona generation data (from generate_deeppersona_from_existing_persona)
        profile_id: Profile ID this persona belongs to
        profile_role: Role from the profile
        profile_industry: Optional industry from profile
        dry_run: If True, don't update Firestore
        
    Returns:
        Transformed persona dictionary
    """
    # Transform to regular schema
    print(f"\n[4/4] Converting to regular persona schema...")
    transformed_persona = transform_to_regular_persona(
        deep_persona=deep_persona_data,
        profile_id=profile_id,
        profile_role=profile_role,
        profile_industry=profile_industry,
        base_persona_id=base_persona_id
    )
    
    deep_persona_id = transformed_persona.get("id")

    print(f"  Result: {get_persona_summary(transformed_persona)}")
    print(f"  Base Persona ID: {base_persona_id}")
    print(f"  Deep Persona ID: {deep_persona_id}")

    # Get current personas list
    research = fetch_research(db, research_id)
    personas = get_personas_from_research(research)

    # Check if a deep persona already exists for this base persona
    existing_deep_persona = None
    existing_deep_persona_index = None
    for i, persona in enumerate(personas):
        if persona.get("basePersonaId") == base_persona_id:
            existing_deep_persona = persona
            existing_deep_persona_index = i
            break
    
    if existing_deep_persona:
        print(f"\n  WARNING: Deep persona already exists for base persona {base_persona_id}")
        print(f"  Existing Deep Persona ID: {existing_deep_persona.get('id')}")
        print(f"  Existing Deep Persona Name: {existing_deep_persona.get('name', 'Unknown')}")
        print(f"  Replacing existing deep persona with new one...")
        # Remove the existing deep persona
        personas.pop(existing_deep_persona_index)
    
    # Add the new deep persona to the list (no bidirectional link - only deep persona links to base)
    # The deep persona has basePersonaId to link back to base, but base persona is not modified
    personas.append(transformed_persona)
    
    # Update Firestore (unless dry run)
    if not dry_run:
        print(f"\n[SAVE] Saving DeepPersona to Firestore...")
        update_firestore(db, research_id, personas)
    else:
        print(f"\n[DRY RUN] Would save DeepPersona to Firestore")
        # Save to local file
        output_file = os.path.join(
            os.path.dirname(__file__),
            "output",
            f"deeppersona_from_{base_persona_id}_{research_id}.json"
        )
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(transformed_persona, f, indent=2, default=str)
        print(f"  Saved to: {output_file}")
    
    return transformed_persona


def main():
    parser = argparse.ArgumentParser(description="Run DeepPersona comparison")
    parser.add_argument("--research-id", required=True, help="Research ID to process")
    parser.add_argument("--persona-id", help="Persona ID to generate DeepPersona from (if provided, generates from existing persona)")
    parser.add_argument("--attribute-count", type=int, default=200, help="Number of attributes to select (default: 200)")
    parser.add_argument("--dry-run", action="store_true", help="Generate personas without updating Firestore")
    args = parser.parse_args()

    research_id = args.research_id
    persona_id = args.persona_id
    attribute_count = args.attribute_count
    dry_run = args.dry_run

    print(f"\n{'#'*60}")
    print(f"# DeepPersona Comparison Script")
    print(f"# Research ID: {research_id}")
    if persona_id:
        print(f"# Persona ID: {persona_id} (generating from existing persona)")
    print(f"# Attribute Count: {attribute_count}")
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

    # If persona_id is provided, generate DeepPersona from existing persona
    if persona_id:
        print(f"\n[FETCH] Fetching persona {persona_id}...")
        base_persona = get_persona_by_id(db, research_id, persona_id)
        
        if not base_persona:
            raise ValueError(f"Persona {persona_id} not found in research {research_id}")
        
        print(f"  Found persona: {base_persona.get('name', 'Unknown')}")
        print(f"  Profile ID: {base_persona.get('profileId', '?')}")
        print(f"  Role: {base_persona.get('role', '?')}")
        
        # Get profile information
        profiles = get_profiles_from_research(research)
        profile_id = base_persona.get("profileId")
        profile = next((p for p in profiles if p.get("id") == profile_id), None)
        
        if not profile:
            raise ValueError(f"Profile {profile_id} not found for persona {persona_id}")
        
        profile_role = profile.get("role", base_persona.get("role", "Professional"))
        profile_industry = profile.get("industry", base_persona.get("industry"))
        
        # Generate DeepPersona from existing persona (pass profile to extract primary attributes)
        deep_persona_data = generate_deeppersona_from_existing_persona(
            base_persona,
            profile=profile,
            attribute_count=attribute_count
        )
        
        # Add to research
        transformed_persona = add_deeppersona_to_research(
            db=db,
            research_id=research_id,
            base_persona_id=persona_id,
            deep_persona_data=deep_persona_data,
            profile_id=profile_id,
            profile_role=profile_role,
            profile_industry=profile_industry,
            dry_run=dry_run
        )
        
        print("\n" + "="*60)
        print("DEEP PERSONA GENERATION COMPLETE")
        print("="*60)
        print(f"\nGenerated DeepPersona:")
        print(f"  Name: {transformed_persona.get('name', 'Unknown')}")
        print(f"  ID: {transformed_persona.get('id', '?')}")
        print(f"  Base Persona ID: {persona_id}")
        
        return transformed_persona

    # Original workflow: Generate DeepPersonas for all profiles with existing personas
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

        # Find existing persona for this profile (to extract primary attributes)
        base_persona = None
        base_persona_id = None
        for persona in personas:
            if persona.get("profileId") == profile_id:
                base_persona = persona
                base_persona_id = persona.get("id")
                break
        
        if not base_persona:
            print(f"  Warning: No existing persona found for profile {profile_id}, skipping...")
            continue

        # Generate DeepPersona using primary attributes from existing persona
        # This preserves primary attributes and generates similar secondary attributes via vector search
        print(f"\n[GENERATE] Generating DeepPersona from existing persona: {base_persona.get('name', 'Unknown')}")
        deep_persona_data = generate_deeppersona_from_existing_persona(
            base_persona,
            profile=profile,
            attribute_count=attribute_count
        )

        # Transform to regular schema (preserves primary attributes from base, generates secondary via similarity)
        print(f"\n[TRANSFORM] Converting to regular persona schema...")
        transformed_persona = transform_to_regular_persona(
            deep_persona=deep_persona_data,
            profile_id=profile_id,
            profile_role=profile_role,
            profile_industry=profile_industry,
            base_persona_id=base_persona_id
        )

        deep_persona_id = transformed_persona.get("id")

        print(f"  Result: {get_persona_summary(transformed_persona)}")
        print(f"  Deep Persona ID: {deep_persona_id}")
        if base_persona_id:
            print(f"  Base Persona ID: {base_persona_id} (linked via basePersonaId)")
        deep_personas[profile_id] = transformed_persona

    # Add deep personas without replacing originals (keep all personas)
    print("\n[ADD] Adding deep personas to existing personas (keeping all)...")
    updated_personas = personas.copy()
    added_personas = []

    for profile_id, new_persona in deep_personas.items():
        # Find the base persona for this profile (for linking)
        base_persona_id = None
        for persona in updated_personas:
            if persona.get("profileId") == profile_id:
                base_persona_id = persona.get("id")
                break
        
        # Add the new deep persona to the list (keeping all original personas)
        updated_personas.append(new_persona)
        added_personas.append(new_persona)
        
        deep_persona_id = new_persona.get("id")
        print(f"  Added: Deep Persona {deep_persona_id} for Profile {profile_id}")
        if base_persona_id:
            print(f"    (Links to base persona {base_persona_id} via basePersonaId)")
    
    if added_personas:
        print(f"  Added {len(added_personas)} deep persona(s) to the list")

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
