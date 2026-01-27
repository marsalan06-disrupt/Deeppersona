"""
Persona validation module for verifying structure matches paper requirements.

This module validates:
1. Nesting depth (3 levels: Section.Category.Attribute)
2. Narrative size (~1 MB requirement)
3. Required sections and fields

All validations log warnings but do not block execution.
"""

import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

# Required sections per paper methodology
REQUIRED_SECTIONS = [
    "Demographic Information",
    "Career and Work Identity",
    "Core Values, Beliefs, and Philosophy",
    "Lifestyle and Daily Routine",
    "Cultural and Social Context",
    "Hobbies, Interests, and Lifestyle"
]

# Required narrative fields per paper
REQUIRED_NARRATIVE_FIELDS = [
    "backstory",
    "personal_values",
    "life_attitude",
    "interests",
    "personal_story"
]


def validate_nesting_depth(persona: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate that hierarchical sections follow 3-level structure: Section.Category.Attribute.
    
    Args:
        persona: The persona dictionary to validate
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    max_depth = 0
    deep_paths = []
    
    def check_depth(obj: Any, path: str = "", depth: int = 0) -> None:
        """Recursively check nesting depth."""
        nonlocal max_depth
        
        if isinstance(obj, dict):
            if not obj:  # Empty dict (leaf node)
                if depth > 3:
                    deep_paths.append(f"{path} (depth: {depth})")
                max_depth = max(max_depth, depth)
                return
            
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                current_depth = depth + 1
                
                if isinstance(value, dict):
                    check_depth(value, current_path, current_depth)
                else:
                    # Leaf value
                    if current_depth > 3:
                        deep_paths.append(f"{current_path} (depth: {current_depth})")
                    max_depth = max(max_depth, current_depth)
        elif isinstance(obj, (str, int, float, bool, list)):
            # Leaf value
            if depth > 3:
                deep_paths.append(f"{path} (depth: {depth})")
            max_depth = max(max_depth, depth)
    
    # Check each required section
    for section_name in REQUIRED_SECTIONS:
        if section_name in persona:
            section_data = persona[section_name]
            if isinstance(section_data, dict):
                check_depth(section_data, section_name, depth=1)
    
    # Check other hierarchical sections (not in required list)
    for key, value in persona.items():
        if key not in REQUIRED_SECTIONS and isinstance(value, dict):
            # Check if it looks like a hierarchical section (has nested dicts)
            if any(isinstance(v, dict) for v in value.values()):
                check_depth(value, key, depth=1)
    
    if max_depth > 3:
        issues.append(
            f"Nesting depth exceeds 3 levels (max found: {max_depth}). "
            f"Paper requires Section.Category.Attribute (3 levels)."
        )
        if deep_paths:
            issues.append(f"Deep paths found: {', '.join(deep_paths[:5])}")  # Show first 5
    
    is_valid = len(issues) == 0
    
    if not is_valid:
        logger.warning(f"Nesting depth validation failed: {', '.join(issues)}")
    else:
        logger.info(f"Nesting depth validation passed (max depth: {max_depth})")
    
    return is_valid, issues


def validate_narrative_size(persona: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that narrative fields total approximately 1 MB as required by paper.
    
    Args:
        persona: The persona dictionary to validate
        
    Returns:
        Tuple of (is_valid, validation_info_dict)
    """
    # Collect narrative text from all narrative fields
    narrative_fields_data = {}
    narrative_text_parts = []
    
    for field in REQUIRED_NARRATIVE_FIELDS:
        value = persona.get(field)
        
        if value is None:
            narrative_fields_data[field] = {
                "present": False,
                "size_bytes": 0,
                "size_mb": 0.0
            }
            continue
        
        # Convert to string representation
        if isinstance(value, dict):
            # For dict fields like personal_values, life_attitude, personal_story
            # Convert entire dict to string
            text = str(value)
        elif isinstance(value, list):
            # For interests list
            text = " ".join(str(item) for item in value)
        else:
            text = str(value)
        
        size_bytes = len(text.encode('utf-8'))
        size_mb = size_bytes / (1024 * 1024)
        
        narrative_fields_data[field] = {
            "present": True,
            "size_bytes": size_bytes,
            "size_mb": size_mb
        }
        
        narrative_text_parts.append(text)
    
    # Calculate total narrative size
    total_narrative_text = " ".join(narrative_text_parts)
    total_size_bytes = len(total_narrative_text.encode('utf-8'))
    total_size_mb = total_size_bytes / (1024 * 1024)
    
    # Paper requirement: ~1 MB
    target_size_mb = 1.0
    min_acceptable_mb = 0.8  # 80% of target
    
    is_valid = total_size_mb >= min_acceptable_mb
    issues = []
    
    if total_size_mb < min_acceptable_mb:
        issues.append(
            f"Narrative size too small: {total_size_mb:.3f}MB "
            f"(target: ~{target_size_mb}MB, minimum: {min_acceptable_mb}MB)"
        )
    
    # Log detailed information
    logger.info("=" * 60)
    logger.info("NARRATIVE SIZE VALIDATION")
    logger.info("=" * 60)
    logger.info(f"Total narrative size: {total_size_mb:.3f} MB ({total_size_bytes:,} bytes)")
    logger.info(f"Target: ~{target_size_mb} MB | Minimum acceptable: {min_acceptable_mb} MB")
    logger.info(f"Status: {'✓ SUFFICIENT' if is_valid else '✗ INSUFFICIENT'}")
    logger.info("")
    logger.info("Breakdown by field:")
    for field, data in narrative_fields_data.items():
        status = "✓" if data["present"] else "✗"
        logger.info(
            f"  {status} {field:20s} | "
            f"Size: {data['size_mb']:6.3f} MB | "
            f"Present: {data['present']}"
        )
    logger.info("=" * 60)
    
    if not is_valid:
        logger.warning(f"Narrative size validation failed: {', '.join(issues)}")
    else:
        logger.info("Narrative size validation passed")
    
    validation_info = {
        "is_valid": is_valid,
        "total_size_mb": total_size_mb,
        "total_size_bytes": total_size_bytes,
        "target_size_mb": target_size_mb,
        "min_acceptable_mb": min_acceptable_mb,
        "field_breakdown": narrative_fields_data,
        "issues": issues
    }
    
    return is_valid, validation_info


def validate_persona_structure(persona: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive validation of persona structure matching paper requirements.
    
    Validates:
    1. Required hierarchical sections exist
    2. Required narrative fields exist
    3. Nesting depth (3 levels max)
    4. Narrative size (~1 MB)
    
    Args:
        persona: The persona dictionary to validate
        
    Returns:
        Dictionary with validation results:
        {
            "is_valid": bool,
            "issues": List[str],
            "nesting_depth": {...},
            "narrative_size": {...},
            "sections_present": List[str],
            "sections_missing": List[str]
        }
    """
    all_issues = []
    
    # 1. Check required sections exist
    sections_present = []
    sections_missing = []
    
    for section in REQUIRED_SECTIONS:
        if section in persona:
            if isinstance(persona[section], dict):
                sections_present.append(section)
            else:
                all_issues.append(f"Section '{section}' exists but is not a dictionary")
                sections_missing.append(section)
        else:
            sections_missing.append(section)
            all_issues.append(f"Missing required section: {section}")
    
    # 2. Check required narrative fields
    narrative_fields_missing = []
    for field in REQUIRED_NARRATIVE_FIELDS:
        if field not in persona:
            narrative_fields_missing.append(field)
            all_issues.append(f"Missing required narrative field: {field}")
    
    # 3. Validate nesting depth
    nesting_valid, nesting_issues = validate_nesting_depth(persona)
    all_issues.extend(nesting_issues)
    
    # 4. Validate narrative size
    narrative_valid, narrative_info = validate_narrative_size(persona)
    all_issues.extend(narrative_info.get("issues", []))
    
    # Overall validation status
    is_valid = (
        len(sections_missing) == 0 and
        len(narrative_fields_missing) == 0 and
        nesting_valid and
        narrative_valid
    )
    
    result = {
        "is_valid": is_valid,
        "issues": all_issues,
        "sections_present": sections_present,
        "sections_missing": sections_missing,
        "narrative_fields_missing": narrative_fields_missing,
        "nesting_depth": {
            "is_valid": nesting_valid,
            "issues": nesting_issues
        },
        "narrative_size": narrative_info
    }
    
    # Log summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("PERSONA STRUCTURE VALIDATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Overall status: {'✓ VALID' if is_valid else '✗ INVALID'}")
    logger.info(f"Sections present: {len(sections_present)}/{len(REQUIRED_SECTIONS)}")
    logger.info(f"Narrative fields present: {len(REQUIRED_NARRATIVE_FIELDS) - len(narrative_fields_missing)}/{len(REQUIRED_NARRATIVE_FIELDS)}")
    logger.info(f"Nesting depth: {'✓ Valid' if nesting_valid else '✗ Invalid'}")
    logger.info(f"Narrative size: {narrative_info['total_size_mb']:.3f} MB ({'✓ Sufficient' if narrative_valid else '✗ Insufficient'})")
    
    if all_issues:
        logger.warning(f"Found {len(all_issues)} validation issue(s)")
        for i, issue in enumerate(all_issues[:10], 1):  # Show first 10 issues
            logger.warning(f"  {i}. {issue}")
        if len(all_issues) > 10:
            logger.warning(f"  ... and {len(all_issues) - 10} more issue(s)")
    else:
        logger.info("No validation issues found")
    
    logger.info("=" * 60)
    logger.info("")
    
    return result
