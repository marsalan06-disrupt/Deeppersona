"""Transform DeepPersona output to regular persona schema."""

import json
import random
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from .validate_persona import validate_persona_structure
except ImportError:
    # Fallback for direct execution
    from validate_persona import validate_persona_structure

logger = logging.getLogger(__name__)


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


def convert_to_narrative_text(value: Any, field_name: str) -> str:
    """
    Convert structured data (dicts, lists) to narrative text format.
    
    Args:
        value: The value to convert (dict, list, or string)
        field_name: Name of the field for context
        
    Returns:
        str: Narrative text representation
    """
    if value is None:
        return ""
    
    # If already a string, return as-is (but check if it's JSON string)
    if isinstance(value, str):
        # Check if it's a JSON string that needs parsing
        if value.strip().startswith('{') or value.strip().startswith('['):
            try:
                parsed = json.loads(value)
                return convert_to_narrative_text(parsed, field_name)
            except (json.JSONDecodeError, TypeError):
                pass
        return value
    
    # Convert dict to narrative text
    if isinstance(value, dict):
        if field_name == "personal_values":
            # Convert personal_values dict to narrative
            values_orientation = value.get("values_orientation", "")
            if values_orientation:
                # Expand into a narrative about their values
                narrative = f"My core values and beliefs are deeply rooted in {values_orientation.lower()}. "
                narrative += f"This value system shapes how I approach decisions, relationships, and life choices. "
                narrative += f"It influences my priorities, what I stand for, and how I navigate the complexities of daily life. "
                narrative += f"These values are not just abstract concepts but practical guides that inform my actions and reactions to various situations I encounter."
                return narrative
            return str(value)
        
        elif field_name == "life_attitude":
            # Convert life_attitude dict to narrative
            attitude = value.get("attitude", "")
            attitude_details = value.get("attitude_details", "")
            coping_mechanism = value.get("coping_mechanism", "")
            
            narrative_parts = []
            if attitude:
                narrative_parts.append(f"My overall attitude toward life can be described as {attitude.lower()}.")
            if attitude_details:
                narrative_parts.append(f"This manifests in my daily life through {attitude_details.lower()}")
            if coping_mechanism:
                narrative_parts.append(f"When facing challenges, I typically {coping_mechanism.lower()}")
            
            if narrative_parts:
                return " ".join(narrative_parts) + " This approach to life has been shaped by my experiences and continues to influence how I respond to both opportunities and difficulties."
            return str(value)
        
        elif field_name == "personal_story":
            # Extract personal_story text from dict
            story_text = value.get("personal_story", "")
            if story_text:
                return story_text
            # If no "personal_story" key, try to find any text value
            for key, val in value.items():
                if isinstance(val, str) and len(val) > 50:  # Likely the story text
                    return val
            return str(value)
        
        else:
            # Generic dict conversion - create narrative from key-value pairs
            parts = []
            for key, val in value.items():
                if isinstance(val, (str, int, float, bool)):
                    parts.append(f"{key}: {val}")
                elif isinstance(val, list):
                    parts.append(f"{key}: {', '.join(str(v) for v in val)}")
            return ". ".join(parts) + "." if parts else str(value)
    
    # Convert list to narrative text
    if isinstance(value, list):
        if field_name == "interests":
            # Convert interests list to narrative
            if value:
                interests_text = ", ".join(str(item) for item in value[:-1])
                if len(value) > 1:
                    interests_text += f", and {value[-1]}"
                else:
                    interests_text = str(value[0])
                narrative = f"My interests and hobbies include {interests_text}. "
                narrative += "These activities provide me with enjoyment, relaxation, and a way to express myself. "
                narrative += "They reflect my personality and preferences, and I often find myself drawn to these pursuits in my free time."
                return narrative
        # Generic list conversion
        return ", ".join(str(item) for item in value)
    
    # Fallback: convert to string
    return str(value)


def transform_to_regular_persona(
    deep_persona: Dict[str, Any],
    profile_id: str,
    profile_role: str,
    profile_industry: Optional[str] = None,
    base_persona_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transform DeepPersona output to match step2.selectedPersonas structure.
    Preserves primary attributes from base persona, generates secondary attributes via similarity.

    Args:
        deep_persona: Output from DeepPersona generation containing base_profile and complete_persona
        profile_id: The profile ID this persona belongs to
        profile_role: The role from the profile (e.g., "Startup Founder")
        profile_industry: Optional industry from profile
        base_persona_id: Optional ID of the base persona this deep persona is derived from

    Returns:
        Dict matching the regular persona schema
    """
    base = deep_persona["base_profile"]
    complete = deep_persona["complete_persona"]

    # Generate unique ID with "deep" prefix for identification
    persona_id = f"persona_deep_{int(time.time() * 1000)}_{random.randint(100000000, 999999999)}"

    # Extract values with fallbacks (these come from base_profile which contains primary attributes)
    age = base.get("age_info", {}).get("age", 35)
    gender = base.get("gender", "male")
    location = base.get("location", {})
    city = location.get("city", "Unknown")
    country = location.get("country", "Unknown")
    
    # Extract primary attributes from base_profile (these are preserved from base persona)
    primary_attributes = base.get("_primary_attributes", {})

    # Extract base_info from complete persona (fallback source for enrichment fields)
    base_info = complete.get("Base Info", {})

    # Helper to get enrichment fields - try base first, then base_info from complete
    def get_enrichment_field(field_name: str) -> str:
        """
        Get enrichment field from base or complete's Base Info and convert to narrative text.
        
        Returns narrative text string instead of structured dict/list.
        """
        value = base.get(field_name)
        if value:
            parsed = parse_if_string(value)
            if field_name in ["interests", "personal_story"]:
                parsed = flatten_nested_field(parsed, field_name)
            # Convert to narrative text
            return convert_to_narrative_text(parsed, field_name)
        
        # Fallback to Base Info in complete persona
        if base_info and field_name in base_info:
            parsed = parse_if_string(base_info[field_name])
            if field_name in ["interests", "personal_story"]:
                parsed = flatten_nested_field(parsed, field_name)
            # Convert to narrative text
            return convert_to_narrative_text(parsed, field_name)
        
        return ""

    # Build the persona with core fields
    persona = {
        # Required fields matching regular schema
        "id": persona_id,
        "profileId": profile_id,
        "name": generate_name_from_gender(gender),
        "age": age,
        "role": profile_role,
        "company": extract_company_from_complete(complete),
        "location": f"{city}, {country}",
        "industry": profile_industry or extract_industry_from_complete(complete),
        "seniority_level": map_age_to_seniority(age),
        "company_size_range": primary_attributes.get("company_size_range") or primary_attributes.get("size_of_business") or "51-200",
        "experience": extract_experience_from_complete(complete),
        "pain_points": extract_pain_points_from_complete(complete),

        # DeepPersona enrichment fields (REQUIRED by paper - "roughly 1 MB of narrative text")
        "summary": complete.get("Summary", ""),
        "personal_values": get_enrichment_field("personal_values"),
        "life_attitude": get_enrichment_field("life_attitude"),
        "interests": get_enrichment_field("interests"),
        "personal_story": get_enrichment_field("personal_story"),

        # Timestamps
        "createdAt": datetime.now(),
        "updatedAt": datetime.now()
    }

    # Flatten _primary_attributes to root level (for compatibility with existing schema)
    if primary_attributes:
        for key, value in primary_attributes.items():
            if key not in persona:  # Don't overwrite existing fields
                persona[key] = value

    # PRESERVE hierarchical structure from complete persona (matching paper methodology)
    # The paper uses sections like "Demographic Information", "Career and Work Identity", etc.
    # We preserve these as nested structures instead of flattening
    # This maintains the taxonomy structure: Section.Category.Attribute
    for section_name, section_data in complete.items():
        if section_name in ["Summary", "Base Info"]:
            continue  # Skip these as they're handled separately
        if isinstance(section_data, dict) and section_data:
            # Preserve the section hierarchy (CORRECT approach per paper)
            # This creates structure like:
            # {
            #   "Demographic Information": { "Age": { "LifeStage": "..." }, ... },
            #   "Career and Work Identity": { "Profession": { "status": "..." }, ... }
            # }
            persona[section_name] = section_data

    # Add basePersonaId if provided (links deep persona to base persona)
    if base_persona_id:
        persona["basePersonaId"] = base_persona_id

    # Validate persona structure (logs issues but doesn't block)
    logger.info(f"Validating persona structure for {persona.get('name', 'Unknown')} (ID: {persona_id})")
    validation_result = validate_persona_structure(persona)
    
    if not validation_result["is_valid"]:
        logger.warning(
            f"Persona validation found issues but continuing (persona ID: {persona_id}). "
            f"See validation details above."
        )
    else:
        logger.info(f"Persona validation passed (persona ID: {persona_id})")

    return persona


def get_persona_summary(persona: Dict[str, Any]) -> str:
    """Get a brief summary of a persona for logging."""
    return (
        f"{persona.get('name', 'Unknown')} | "
        f"Age: {persona.get('age', '?')} | "
        f"Role: {persona.get('role', '?')} | "
        f"Location: {persona.get('location', '?')}"
    )
