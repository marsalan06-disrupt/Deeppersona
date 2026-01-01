"""Transform DeepPersona output to regular persona schema."""

import json
import random
import time
from datetime import datetime
from typing import Dict, Any, Optional


def parse_if_string(value: Any) -> Any:
    """Parse value if it's a stringified JSON, otherwise return as-is."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


def flatten_nested_field(value: Any, field_name: str) -> Any:
    """Flatten nested structures like {field_name: {field_name: actual_value}}."""
    if isinstance(value, dict) and len(value) == 1 and field_name in value:
        inner = value[field_name]
        # Check if inner is also the same nesting
        if isinstance(inner, dict) and len(inner) == 1 and field_name in inner:
            return inner[field_name]
        return inner
    return value

# Name lists for generating realistic names
MALE_NAMES = [
    "James", "Michael", "David", "John", "Robert", "William", "Richard", "Joseph",
    "Thomas", "Christopher", "Daniel", "Matthew", "Anthony", "Mark", "Steven",
    "Andrew", "Paul", "Joshua", "Kenneth", "Kevin", "Brian", "George", "Timothy",
    "Hiroshi", "Kenji", "Takeshi", "Hans", "Klaus", "Pierre", "Jean", "Carlos",
    "Miguel", "Raj", "Amit", "Vikram", "Wei", "Chen", "Liam", "Noah", "Oliver"
]

FEMALE_NAMES = [
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan",
    "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Margaret", "Sandra",
    "Ashley", "Emily", "Donna", "Michelle", "Dorothy", "Carol", "Amanda", "Melissa",
    "Yuki", "Sakura", "Hana", "Anna", "Maria", "Sophie", "Emma", "Isabella",
    "Priya", "Anita", "Deepa", "Li", "Mei", "Olivia", "Ava", "Charlotte", "Mia"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White", "Harris",
    "Tanaka", "Yamamoto", "Suzuki", "Mueller", "Schmidt", "Dubois", "Martin",
    "Silva", "Santos", "Sharma", "Patel", "Kumar", "Wang", "Zhang", "Chen"
]


def generate_name_from_gender(gender: str) -> str:
    """Generate a realistic name based on gender."""
    if gender.lower() == "male":
        first_name = random.choice(MALE_NAMES)
    else:
        first_name = random.choice(FEMALE_NAMES)
    last_name = random.choice(LAST_NAMES)
    return f"{first_name} {last_name}"


def map_age_to_seniority(age: int) -> str:
    """Map age to seniority level."""
    if age < 25:
        return "Entry"
    elif age < 35:
        return "Mid"
    elif age < 45:
        return "Senior"
    elif age < 55:
        return "Director"
    else:
        return "VP"


def extract_from_complete_persona(complete: Dict[str, Any], section: str, key: str, default: str = "") -> str:
    """Extract a value from the complete persona structure."""
    if section in complete and isinstance(complete[section], dict):
        return complete[section].get(key, default)
    return default


def extract_experience_from_complete(complete: Dict[str, Any]) -> str:
    """Extract experience description from complete persona."""
    # Try Career and Work Identity section first
    career_section = complete.get("Career and Work Identity", {})
    if isinstance(career_section, dict):
        # Look for experience-related keys
        for key in ["experience", "professional_experience", "work_experience", "background"]:
            if key in career_section:
                return str(career_section[key])

    # Fallback to base info
    base_info = complete.get("Base Info", {})
    if isinstance(base_info, dict):
        career_info = base_info.get("career_info", {})
        if isinstance(career_info, dict):
            return career_info.get("status", "Professional with relevant industry experience")

    return "Experienced professional in their field"


def extract_pain_points_from_complete(complete: Dict[str, Any]) -> str:
    """Extract pain points from complete persona."""
    # Look in various sections for challenges/pain points
    for section_name in ["Core Values, Beliefs, and Philosophy", "Lifestyle and Daily Routine", "Other Attributes"]:
        section = complete.get(section_name, {})
        if isinstance(section, dict):
            for key in ["challenges", "pain_points", "frustrations", "struggles"]:
                if key in section:
                    return str(section[key])

    # Generate from life attitude if available
    base_info = complete.get("Base Info", {})
    if isinstance(base_info, dict):
        life_attitude = base_info.get("life_attitude", {})
        if isinstance(life_attitude, dict):
            coping = life_attitude.get("coping_mechanism", "")
            if coping:
                return f"Deals with challenges by {coping.lower()}"

    return "Faces typical professional challenges in their role"


def extract_company_from_complete(complete: Dict[str, Any]) -> str:
    """Extract company information from complete persona."""
    career_section = complete.get("Career and Work Identity", {})
    if isinstance(career_section, dict):
        for key in ["company", "employer", "organization", "workplace"]:
            if key in career_section:
                return str(career_section[key])
    return "Mid-size company"


def extract_industry_from_complete(complete: Dict[str, Any]) -> str:
    """Extract industry from complete persona."""
    career_section = complete.get("Career and Work Identity", {})
    if isinstance(career_section, dict):
        for key in ["industry", "sector", "field"]:
            if key in career_section:
                return str(career_section[key])

    # Try to infer from occupation
    base_info = complete.get("Base Info", {})
    if isinstance(base_info, dict):
        career_info = base_info.get("career_info", {})
        if isinstance(career_info, dict):
            status = career_info.get("status", "")
            if status:
                # Simple inference
                status_lower = status.lower()
                if any(word in status_lower for word in ["tech", "software", "developer", "engineer"]):
                    return "Technology"
                elif any(word in status_lower for word in ["market", "sales", "business"]):
                    return "Business Services"
                elif any(word in status_lower for word in ["health", "medical", "doctor", "nurse"]):
                    return "Healthcare"
                elif any(word in status_lower for word in ["finance", "bank", "account"]):
                    return "Finance"

    return "Professional Services"


def transform_to_regular_persona(
    deep_persona: Dict[str, Any],
    profile_id: str,
    profile_role: str,
    profile_industry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transform DeepPersona output to match step2.selectedPersonas structure.

    Args:
        deep_persona: Output from DeepPersona generation containing base_profile and complete_persona
        profile_id: The profile ID this persona belongs to
        profile_role: The role from the profile (e.g., "Startup Founder")
        profile_industry: Optional industry from profile

    Returns:
        Dict matching the regular persona schema
    """
    base = deep_persona["base_profile"]
    complete = deep_persona["complete_persona"]

    # Generate unique ID with deep_ prefix for identification
    persona_id = f"persona_deep_{int(time.time() * 1000)}_{random.randint(100000000, 999999999)}"

    # Extract values with fallbacks
    age = base.get("age_info", {}).get("age", 35)
    gender = base.get("gender", "male")
    location = base.get("location", {})
    city = location.get("city", "Unknown")
    country = location.get("country", "Unknown")

    # Build the persona
    persona = {
        # Required fields matching regular schema
        "id": persona_id,
        "profileId": profile_id,
        "name": generate_name_from_gender(gender),
        "age": age,
        "role": profile_role,  # Use profile role for consistency
        "company": extract_company_from_complete(complete),
        "location": f"{city}, {country}",
        "industry": profile_industry or extract_industry_from_complete(complete),
        "seniority_level": map_age_to_seniority(age),
        "company_size_range": "51-200",
        "experience": extract_experience_from_complete(complete),
        "pain_points": extract_pain_points_from_complete(complete),

        # DeepPersona enrichment (extra fields for richer interviews)
        # Parse stringified JSON and flatten nested structures
        "backstory": complete.get("Summary", ""),
        "personal_values": parse_if_string(base.get("personal_values", {})),
        "life_attitude": parse_if_string(base.get("life_attitude", {})),
        "interests": flatten_nested_field(parse_if_string(base.get("interests", {})), "interests"),
        "personal_story": flatten_nested_field(parse_if_string(base.get("personal_story", {})), "personal_story"),

        # Metadata
        "source": "deeppersona",  # Tag to identify in comparison
        "createdAt": datetime.now(),
        "updatedAt": datetime.now()
    }

    return persona


def get_persona_summary(persona: Dict[str, Any]) -> str:
    """Get a brief summary of a persona for logging."""
    return (
        f"{persona.get('name', 'Unknown')} | "
        f"Age: {persona.get('age', '?')} | "
        f"Role: {persona.get('role', '?')} | "
        f"Location: {persona.get('location', '?')} | "
        f"Source: {persona.get('source', 'regular')}"
    )
