#!/usr/bin/env python3
"""
Complete flow test for Deeppersona profile generation.

This script demonstrates the full pipeline:
1. Generate base profile (demographics, values, story)
2. Select relevant attributes via vector search
3. Generate complete persona with all sections
"""

import json
import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from select_attributes import generate_user_profile, get_selected_attributes, save_results
from generate_profile import generate_single_profile


def print_section(title: str, char: str = "="):
    """Print a formatted section header."""
    print(f"\n{char * 60}")
    print(f" {title}")
    print(f"{char * 60}\n")


def print_base_profile(profile: dict):
    """Print base profile in a readable format."""
    print_section("BASE PROFILE", "-")

    # Age info
    age_info = profile.get("age_info", {})
    print(f"Age: {age_info.get('age')} ({age_info.get('age_group')})")

    # Gender
    print(f"Gender: {profile.get('gender')}")

    # Location
    location = profile.get("location", {})
    print(f"Location: {location.get('city')}, {location.get('country')}")

    # Career
    career = profile.get("career_info", {})
    print(f"Career: {career.get('status')}")

    # Values
    values = profile.get("personal_values", {})
    print(f"Values: {values.get('values_orientation', 'N/A')}")

    # Life attitude
    attitude = profile.get("life_attitude", {})
    if isinstance(attitude, dict):
        print(f"Attitude: {attitude.get('attitude', 'N/A')}")
        print(f"Details: {attitude.get('attitude_details', 'N/A')}")
        print(f"Coping: {attitude.get('coping_mechanism', 'N/A')}")

    # Personal story
    story = profile.get("personal_story", {})
    if isinstance(story, dict):
        story_text = story.get("personal_story", "")
        if story_text:
            print(f"\nPersonal Story:")
            print(f"  {story_text[:500]}..." if len(story_text) > 500 else f"  {story_text}")

    # Interests
    interests = profile.get("interests", {})
    if isinstance(interests, dict):
        interest_list = interests.get("interests", [])
        if interest_list:
            print(f"\nInterests: {', '.join(interest_list)}")


def print_attributes_summary(attributes: list):
    """Print a summary of selected attributes."""
    print_section("SELECTED ATTRIBUTES", "-")
    print(f"Total attributes selected: {len(attributes)}")

    # Group by top-level category
    categories = {}
    for attr in attributes:
        category = attr.split('.')[0] if '.' in attr else attr
        categories[category] = categories.get(category, 0) + 1

    print("\nAttributes by category:")
    for category, count in sorted(categories.items()):
        print(f"  - {category}: {count}")

    # Show sample attributes
    print("\nSample attributes (first 10):")
    for attr in attributes[:10]:
        print(f"  - {attr}")


def print_complete_profile(profile: dict):
    """Print the complete generated profile."""
    print_section("COMPLETE PERSONA", "-")

    # Print each section
    sections = [
        "Demographic Information",
        "Career and Work Identity",
        "Core Values, Beliefs, and Philosophy",
        "Lifestyle and Daily Routine",
        "Cultural and Social Context",
        "Hobbies, Interests, and Lifestyle",
        "Other Attributes"
    ]

    for section in sections:
        if section in profile and profile[section]:
            print(f"\n[{section}]")
            section_data = profile[section]
            if isinstance(section_data, dict):
                for key, value in list(section_data.items())[:5]:  # Show first 5 items
                    if isinstance(value, dict):
                        print(f"  {key}:")
                        for k, v in list(value.items())[:3]:
                            print(f"    - {k}: {v}")
                    else:
                        print(f"  - {key}: {value}")
                if len(section_data) > 5:
                    print(f"  ... and {len(section_data) - 5} more items")

    # Print summary
    if "Summary" in profile:
        print(f"\n[Summary]")
        print(profile["Summary"])


def save_test_results(base_profile: dict, attributes: list, complete_profile: dict, output_dir: str):
    """Save all test results to files."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save base profile
    base_path = os.path.join(output_dir, f"test_base_profile_{timestamp}.json")
    with open(base_path, 'w', encoding='utf-8') as f:
        json.dump(base_profile, f, ensure_ascii=False, indent=2)
    print(f"Saved base profile to: {base_path}")

    # Save attributes
    attr_path = os.path.join(output_dir, f"test_attributes_{timestamp}.json")
    with open(attr_path, 'w', encoding='utf-8') as f:
        json.dump({"attributes": attributes, "count": len(attributes)}, f, ensure_ascii=False, indent=2)
    print(f"Saved attributes to: {attr_path}")

    # Save complete profile
    complete_path = os.path.join(output_dir, f"test_complete_profile_{timestamp}.json")
    with open(complete_path, 'w', encoding='utf-8') as f:
        json.dump(complete_profile, f, ensure_ascii=False, indent=2)
    print(f"Saved complete profile to: {complete_path}")

    return base_path, attr_path, complete_path


def run_complete_flow(attribute_count: int = 150, save_output: bool = True):
    """
    Run the complete profile generation flow.

    Args:
        attribute_count: Number of attributes to select (default: 150)
        save_output: Whether to save results to files (default: True)

    Returns:
        tuple: (base_profile, selected_attributes, complete_profile)
    """
    print_section("DEEPPERSONA - COMPLETE FLOW TEST")
    print(f"Attribute count: {attribute_count}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 1: Generate base profile
    print_section("STEP 1: Generating Base Profile")
    print("Creating demographics, values, life story, and interests...")
    base_profile = generate_user_profile()
    print_base_profile(base_profile)

    # Step 2: Select attributes
    print_section("STEP 2: Selecting Attributes")
    print(f"Using vector search to find {attribute_count} relevant attributes...")
    selected_attributes = get_selected_attributes(base_profile, attribute_count=attribute_count)
    print_attributes_summary(selected_attributes)

    # Step 3: Generate complete persona using the SAME base profile and attributes
    print_section("STEP 3: Generating Complete Persona")
    print("Generating detailed profile sections using GPT...")
    print("(Using the same base profile and attributes from Steps 1 & 2)")
    complete_profile = generate_single_profile(
        template=None,
        profile_index=0,
        attribute_count=attribute_count,
        base_profile=base_profile,  # Pass the base profile from Step 1
        selected_attributes=selected_attributes  # Pass the attributes from Step 2
    )
    print_complete_profile(complete_profile)

    # Save results
    if save_output:
        print_section("SAVING RESULTS")
        output_dir = os.path.join(os.path.dirname(__file__), "output", "test_runs")
        save_test_results(base_profile, selected_attributes, complete_profile, output_dir)

    # Summary
    print_section("FLOW COMPLETE")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base profile generated: Yes")
    print(f"Attributes selected: {len(selected_attributes)}")
    print(f"Complete profile sections: {len([k for k in complete_profile.keys() if k not in ['Base Info', 'Generated At', 'Profile Index']])}")

    return base_profile, selected_attributes, complete_profile


if __name__ == "__main__":
    # Run complete flow with default settings
    # You can modify attribute_count to test different sizes: 100, 150, 200, 250, 300, 350
    base_profile, attributes, complete_profile = run_complete_flow(
        attribute_count=150,
        save_output=True
    )
