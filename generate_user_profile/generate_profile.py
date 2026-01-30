#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import json
import os
import random
import sys
import time
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional
from generate_user_profile.config import get_completion
import subprocess
# Add current directory to system path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def safe_str(value):
    """
    Ensure a string is returned.
      - If value is already a str, return it.
      - Otherwise (dict, list, or other), return the JSON serialization with multi-line formatting
    """
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)

def get_project_root() -> str:
    """Get the project root directory path."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..'))
    return project_root


def copy_files_from_source_to_target():
    """Copy files from source to target location."""
    # Source path - no longer needed as we save directly to correct directory
    # But kept for compatibility
    correct_output_dir = os.path.join(get_project_root(), "output")

    # Ensure target directory exists
    os.makedirs(correct_output_dir, exist_ok=True)

    print(f"Output directory set to: {correct_output_dir}")
    return True


def get_timestamped_filename(base_path: str) -> str:
    """Add timestamp to file path.

    Args:
        base_path: Base file path.

    Returns:
        str: File path with timestamp.
    """
    directory = os.path.dirname(base_path)
    filename = os.path.basename(base_path)
    name, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_filename = f"{name}_{timestamp}{ext}"
    return os.path.join(directory, timestamped_filename)


def save_json_file(file_path: str, data: Dict, use_timestamp: bool = True) -> str:
    """Save JSON file.

    Args:
        file_path: Target file path.
        data: Data to save.
        use_timestamp: Whether to use timestamp, default True.

    Returns:
        str: Actual saved file path.
    """
    try:
        if use_timestamp:
            actual_path = get_timestamped_filename(file_path)
        else:
            actual_path = file_path

        os.makedirs(os.path.dirname(actual_path), exist_ok=True)
        with open(actual_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return actual_path
    except Exception as e:
        print(f"Error saving JSON file: {e}")
        return file_path


def extract_paths(obj: Dict, prefix: str = "") -> List[str]:
    """Extract all attribute paths from nested JSON object.

    Args:
        obj: Nested JSON object.
        prefix: Current path prefix.

    Returns:
        List[str]: List of attribute paths.
    """
    paths = []
    for key, value in obj.items():
        new_prefix = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            if not value:  # Empty dict means leaf node
                paths.append(new_prefix)
            else:
                paths.extend(extract_paths(value, new_prefix))
    return paths



def generate_category_attributes(category_paths: Dict, custom_prompt: str, category_name: str, is_deep_generation: bool = False) -> Dict:
    """Generate all attribute values for a top-level category at once.

    Args:
        category_paths: All attribute paths and structure under the category.
        custom_prompt: Custom prompt with specific generation instructions.
        category_name: Top-level category name.
        is_deep_generation: If True, generate deeper, more detailed values (for small attribute sets).

    Returns:
        Dict: All generated attribute values.
    """
    # Collect all leaf node paths under this category
    leaf_paths = []

    def collect_leaf_paths(obj, current_path):
        for key, value in obj.items():
            path = f"{current_path}.{key}" if current_path else key
            if isinstance(value, dict):
                if not value:  # Leaf node
                    leaf_paths.append(path)
                else:
                    collect_leaf_paths(value, path)

    collect_leaf_paths(category_paths, "")

    # If no leaf nodes, return empty dict
    if not leaf_paths:
        return {}
    
    # Enhanced system prompt for deep generation (when few attributes)
    if is_deep_generation:
        system_prompt = """You are generating detailed, in-depth attribute values for a deep persona profile. 
Format your response as a JSON object where each key is the attribute path and each value is a rich, detailed description.

For deep generation:
- Provide comprehensive, nuanced values (200-500 characters per attribute)
- Include specific details, examples, and context
- Show depth of personality, behavior, and characteristics
- Make values feel authentic and multi-dimensional
- Avoid generic or superficial descriptions"""
    else:
        # Standard system prompt for normal generation
        system_prompt = """Format your response as a JSON object where each key is the attribute path and each value is the generated attribute value (not exceeding 100 characters)."""

    # Enhanced user prompt for deep generation
    if is_deep_generation:
        user_prompt = f"""{custom_prompt}

IMPORTANT: You are generating DEEP, DETAILED values for a high-quality persona profile. Each attribute should be rich, nuanced, and comprehensive.

Attribute Paths to generate detailed values for:
"""
        for path in leaf_paths:
            user_prompt += f"- {path}\n"
        user_prompt += """
Generate comprehensive, detailed values for all these attributes in JSON format. Each value should be:
- Rich and multi-dimensional (200-500 characters)
- Specific and concrete, not generic
- Authentic and believable
- Contextually appropriate for the persona
- Show depth of personality and behavior
"""
    else:
        # Standard user prompt
        user_prompt = f"{custom_prompt}\n\nAttribute Paths to generate values for:\n"
        for path in leaf_paths:
            user_prompt += f"- {path}\n"
        user_prompt += "\nGenerate suitable values for all these attributes in JSON format."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        print(f"  Generating {len(leaf_paths)} attribute values for {category_name}...")
        response = get_completion(messages)
        if not response:
            print(f"  Failed to generate {category_name} attributes: empty response")
            return {}

        # Try to parse JSON response
        try:
            import json
            # Clean response, remove possible markdown code block markers
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            generated_values = json.loads(cleaned_response)
            print(f"  Successfully generated {len(generated_values)} attribute values")
            return generated_values
        except json.JSONDecodeError as e:
            print(f"  Failed to parse {category_name} JSON: {e}")
            print(f"  Response content: {response[:100]}..." if len(response) > 100 else f"Response content: {response}")
            return {}
    except Exception as e:
        print(f"  Error generating {category_name} attributes: {e}")
        return {}


def generate_final_summary(profile: Dict, base_info: Dict = None) -> str:
    """Generate final summary for user profile.

    Args:
        profile: Complete user profile data.
        base_info: Base info containing life_story etc.

    Returns:
        str: Final summary text.
    """
    system_prompt = """
Your task: Based solely on the provided user attributes and personal story, create an objective and factual personal profile, roughly 3000-4000 words.

Content Requirements:
	•	The profile must be written entirely in the first-person perspective.
	•	The output should be a coherent, logically structured narrative, not a list of points. The order may vary: it does not need to follow the fixed "background → challenge → conclusion" pattern, and may instead begin with daily life or interests.
 	•	The opening must explicitly state my country or region, ensuring that geographic location is clearly highlighted at the very start.
	•	Must include:
	1.	Basic background (e.g., location, identity)
	2.	Daily life or work routines
	3.	Personal interests and hobbies (explicitly highlighted)
	4.	Behavioral tendencies or values (positive or negative)
	•	Interests and hobbies must be integrated naturally, not superficially. Add small, ordinary details (e.g., food preferences, leisure activities, quirks) that make the character feel real.
	•	If there are negative traits, imperfections, or contradictions, they must be represented faithfully without softening. Do not reframe them as "growth" or "lessons learned."
	•	No declarative or reflective endings. Avoid abstract statements like "I've learned…," "This shows…," or "Success means…." The ending should remain grounded in daily routines or interests.
	•	Only include information explicitly provided in the attributes and story. No invention, speculation, or interpretation.
	•	Prohibit the use of words such as' balance 'and' balance '
	•	Expand on details, provide rich descriptions, and create a comprehensive narrative that captures the depth and complexity of this person's life.
"""
    user_prompt = f"Complete Profile (in JSON format):\n{json.dumps(profile, ensure_ascii=False, indent=2)}\n\n"
    
    user_prompt +="""Generate a first-person narrative of roughly 3000-4000 words from the provided profile. Your primary goal is to make the person feel real, believable, and authentic. Provide extensive detail about their life, experiences, routines, thoughts, and perspectives.

To achieve this, strictly follow the 'Show, Don't Tell' principle:
1.  **Illustrate, Don't Declare:** Show values and traits through specific actions, stories, and decisions, rather than stating them directly.
2.  **Connect Actions to Motivation:** Briefly explain the 'why' behind key life choices and habits to reveal the person's inner logic and create narrative depth.
3.  **Maintain a Natural Voice:** The tone must be sincere and grounded—thoughtful but not overly abstract or dramatic.

Weave all elements into a cohesive story, not a simple list of facts."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        response = get_completion(messages)
        summary = response.strip() if response else ""
        # Check if word count is within acceptable range (3000-4000 words)
        word_count = len(summary.split())
        if word_count < 2000:
            print(f"Warning: Summary is only {word_count} words (target: 3000-4000 words)")
        elif word_count > 4000:
            summary = enforce_word_limit(summary, 4000)
            print(f"Summary was adjusted to 4000 words (from {word_count})")
        else:
            print(f"Summary generated with {word_count} words")
        return summary
    except Exception as e:
        print(f"Error generating final summary: {e}")
        return ""


def print_section(section: Dict, indent: int = 0) -> None:
    """Print config section content.

    Args:
        section: Config section to print.
        indent: Indentation level.
    """
    indent_str = "  " * indent
    for key, value in section.items():
        if isinstance(value, dict):
            print(f"{indent_str}{key}:")
            print_section(value, indent + 1)
        else:
            print(f"{indent_str}{key}: {value}")


def generate_section(template_section: Dict, base_info: str, section_name: str, indent: int = 0, is_deep_generation: bool = False) -> Dict:
    """Generate a section of the profile.

    Args:
        template_section: Corresponding section in template.
        base_info: Base info text.
        section_name: Section name.
        indent: Indentation level.
        is_deep_generation: If True, generate deeper, more detailed values.

    Returns:
        Dict: Generated config section.
    """
    section_result = {}
    indent_str = "  " * indent

    print(f"{indent_str}Generating {section_name} section...")

    # If top-level category, generate all attributes at once
    if indent == 0:  # Top-level category
        # Use new function to generate all attribute values at once
        all_attributes = generate_category_attributes(template_section, base_info, section_name, is_deep_generation=is_deep_generation)

        # If attributes were generated successfully, add them to result
        if all_attributes:
            # Build result dictionary
            for path, value in all_attributes.items():
                # Split path
                parts = path.split('.')
                # Skip first part (category name)
                if len(parts) > 1 and parts[0] == section_name:
                    parts = parts[1:]

                # Recursively build nested dictionary
                current = section_result
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:  # Last part, set value
                        current[part] = value
                        print(f"{indent_str}  - {'.'.join(parts)}: {value}")
                    else:
                        if part not in current:
                            current[part] = {}
                        current = current[part]

            return section_result

    # If not top-level or batch generation failed, use recursive approach
    for key, value in template_section.items():
        current_path = f"{section_name}.{key}" if section_name else key

        if isinstance(value, dict):
            if not value:  # Leaf node
                generated_value = generate_attribute_value(current_path, base_info)
                section_result[key] = generated_value
                print(f"{indent_str}  - {key}: {generated_value}")
            else:  # Nested node
                section_result[key] = generate_section(value, base_info, current_path, indent + 1)

    return section_result


def enforce_word_limit(text: str, limit: int = 300) -> str:
    """Trim text to at most `limit` words."""
    words = text.split()
    if len(words) > limit:
        return ' '.join(words[:limit])
    return text


def append_profile_to_json(file_path: str, profile: Dict, use_timestamp: bool = True) -> str:
    """Append profile to JSON file.

    Args:
        file_path: Target file path.
        profile: Profile to append.
        use_timestamp: Whether to use timestamp, default True.

    Returns:
        str: Actual saved file path.
    """
    try:
        if use_timestamp:
            actual_path = get_timestamped_filename(file_path)
            profiles = [profile]  # New file, only contains current profile
        else:
            actual_path = file_path
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    profiles = json.load(f)
            else:
                profiles = []
            profiles.append(profile)

        os.makedirs(os.path.dirname(actual_path), exist_ok=True)
        with open(actual_path, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2)
        return actual_path
    except Exception as e:
        print(f"Error appending profile to JSON file: {e}")
        return file_path


def generate_single_profile(template: Dict = None, profile_index: int = 0, attribute_count: int = 200,
                           base_profile: Dict = None, selected_attributes: List = None) -> Dict:
    """Generate a complete user profile based on the given template.

    Args:
        template: Optional template for generation.
        profile_index: Index of the profile to generate.
        attribute_count: Number of attributes to include.
        base_profile: Optional pre-generated base profile. If provided, skips base profile generation.
        selected_attributes: Optional pre-selected attributes list. If provided, skips attribute selection.

    Returns:
        Dict: The generated user profile.
    """

    # Import required functions
    from generate_user_profile.select_attributes import generate_user_profile as gen_profile
    from generate_user_profile.select_attributes import get_selected_attributes, save_results, build_nested_dict

    # Use provided base_profile or generate a new one
    if base_profile is not None:
        print('Using provided base profile...')
        user_profile = base_profile
    else:
        print(f'Generating new base profile...')
        user_profile = gen_profile()

    # Use provided selected_attributes or generate new ones
    if selected_attributes is not None:
        print(f'Using provided {len(selected_attributes)} attributes...')
        selected_paths_list = selected_attributes
    else:
        print(f'Selecting {attribute_count} attributes via vector search...')
        selected_paths_list = get_selected_attributes(user_profile, attribute_count)

    # Save results to output directory
    correct_output_dir = os.path.join(get_project_root(), "output")
    save_results(user_profile, selected_paths_list, correct_output_dir)

    # Copy files from source to target location
    copy_files_from_source_to_target()

    # Load the saved data (selected_paths needs to be in nested dict format)
    project_root = get_project_root()
    output_dir = os.path.join(project_root, "output")

    # Use the user_profile we already have
    base_info = user_profile
    if 'Occupations' not in base_info:
        print("Warning: 'Occupations' key is missing in the user profile. Setting it to an empty list.")
        base_info['Occupations'] = []

    # Convert selected_paths list to nested dict if needed
    if isinstance(selected_paths_list, list):
        selected_paths = build_nested_dict(selected_paths_list)
    else:
        selected_paths_path = os.path.join(output_dir, 'selected_paths.json')
        with open(selected_paths_path, 'r', encoding='utf-8') as f:
            selected_paths = json.load(f)

    # Ensure these fields are strings
    for k in ("life_attitude", "interests"):
        base_info[k] = safe_str(base_info.get(k, ""))

    # Example assertion: ensure the profile includes an 'Occupations' field
    assert 'Occupations' in base_info, "The 'Occupations' key is missing in the user profile."
    
    # Determine if we should use deep generation (for 10 or fewer attributes)
    is_deep_generation = attribute_count <= 10
    if is_deep_generation:
        print(f"[DEEP GENERATION MODE] Generating detailed, comprehensive values for {len(selected_paths_list)} attributes")
    
    # Initialize profile dictionary
    profile = {
        "Base Info": base_info,
        "Generated At": time.strftime("%Y-%m-%d %H:%M:%S"),
        "Profile Index": profile_index + 1
    }

    # Step 1: Generate Demographic Information
    life_story = base_info.get("personal_story", {}).get("personal_story", "")
    demographic_input = (
        "Base Information (for reference):\n" + json.dumps(base_info, ensure_ascii=False, indent=2) + "\n\n"
        "Life Story (for reference):\n" + str(life_story) + "\n\n"
        "Instructions: Based on the `base_info` and `life_story` provided, **develop and elaborate on** the 'Demographic Information' section in English. Your task is to **appropriately expand upon and enrich** the existing information from `base_info` and incorporate relevant insights from the `life_story`. Focus on elaborating on the given data points, adding further relevant details, or providing context to make the demographic profile more comprehensive and insightful. While you should avoid simply repeating the `base_info` verbatim, ensure that all generated content is **directly built upon and logically extends** the information available in `base_info` and `life_story`, rather than introducing entirely new, unrelated demographic facts. The goal is a coherent, more descriptive, and enhanced version of the original data that reflects the person's life experiences."
    )
    demographic_template = selected_paths.get("Demographic Information")
    if demographic_template and demographic_template != "":
        print('Generating Demographic Information...')
        demographic_section = generate_category_attributes(demographic_template, demographic_input, "Demographic Information", is_deep_generation=is_deep_generation)
        # Build nested dictionary structure
        nested_result = {}
        for path, value in demographic_section.items():
            parts = path.split('.')
            if len(parts) > 1 and parts[0] == "Demographic Information":
                parts = parts[1:]
            
            current = nested_result
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = value
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
        profile["Demographic Information"] = nested_result
    else:
        print('No valid "Demographic Information" template found in selected_paths, skipping Demographic Information.')
    
    # Step 2: Generate Career Information
    career_template = selected_paths.get("Career and Work Identity")
    if career_template and career_template != "":
        print('Generating Career and Work Identity...')
        # Construct input for Career and Work Identity, including Demographic Information
        career_input = (
            "Base Information (for reference):\n" + json.dumps(base_info, ensure_ascii=False, indent=2) + "\n\n"
            "Life Story (for reference):\n" + str(life_story) + "\n\n"
            "Demographic Information (for reference):\n" + json.dumps(profile.get("Demographic Information", {}), ensure_ascii=False, indent=2) + "\n\n"
            "Instructions: Based on the `base_info`, `life_story`, and `Demographic Information` provided above, **develop and elaborate on** the 'Career and Work Identity' section in English. "
            "Your aim is to distill and articulate the career identity, professional journey, and work-related aspirations that are **evident or can be reasonably inferred from the combined `base_info`, `life_story`, and `Demographic Information`**. "
            "Offer fresh insights by providing a **deeper, more nuanced interpretation or by highlighting connections within the provided data** that illuminate these aspects. "
            "Ensure that this elaboration is **logically consistent with and directly stems from** the provided information. "
            "**Do not introduce new career details or aspirations that are not grounded in or clearly supported by the source material.** "
            "The section should be an insightful and coherent expansion of what can be understood from the source material."
        )
        career_info_section = generate_category_attributes(career_template, career_input, "Career and Work Identity", is_deep_generation=is_deep_generation)
        # Build nested dictionary structure
        nested_result = {}
        for path, value in career_info_section.items():
            parts = path.split('.')
            if len(parts) > 1 and parts[0] == "Career and Work Identity":
                parts = parts[1:]
            
            current = nested_result
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = value
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
        profile["Career and Work Identity"] = nested_result
    else:
        print('No valid "Career and Work Identity" template found in selected_paths, skipping.')
    
    # Step 3: Generate Core Values, Beliefs, and Philosophy
    pv_orientation = base_info.get("personal_values", {}).get("values_orientation", "")
    if not isinstance(pv_orientation, str):
        pv_orientation = json.dumps(pv_orientation, ensure_ascii=False)
    core_input = (
        "Life Story (for reference):\n" + str(life_story) + "\n\n"
        "Demographic Information (for reference):\n" + json.dumps(profile.get("Demographic Information", {}), ensure_ascii=False, indent=2) + "\n\n"
        "Career Information (for reference):\n" + json.dumps(profile.get("Career and Work Identity", {}), ensure_ascii=False, indent=2) + "\n\n"
        "Personal Values (for reference):\n" + pv_orientation + "\n\n"
        "Instructions: Based on the `life_story` and other information provided above, **develop and elaborate on** the 'Core Values, Beliefs, and Philosophy' section in English. Your aim is to distill and articulate the core values, beliefs, and philosophical outlook that are **evident or can be reasonably inferred from the `life_story` and other provided information**. Offer fresh insights by providing a **deeper, more nuanced interpretation or by highlighting connections within the provided data** that illuminate these guiding principles. Ensure that this elaboration is **logically consistent with and directly stems from** the provided information. **Do not introduce new values, beliefs, or philosophies that are not grounded in or clearly supported by the source material.** The section should be an insightful and coherent expansion of what can be understood from the source material.IMPORTANT: Avoid including anything related to community-building activities.Prohibit the use of words such as' balance 'and' balance '"
    )
    core_template = selected_paths.get("Core Values, Beliefs, and Philosophy")
    if core_template and core_template != "":
        print('Generating Core Values, Beliefs, and Philosophy...')
        core_values_section = generate_category_attributes(core_template, core_input, "Core Values, Beliefs, and Philosophy", is_deep_generation=is_deep_generation)
        # Build nested dictionary structure
        nested_result = {}
        for path, value in core_values_section.items():
            parts = path.split('.')
            if len(parts) > 1 and parts[0] == "Core Values, Beliefs, and Philosophy":
                parts = parts[1:]
            
            current = nested_result
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = value
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
        profile["Core Values, Beliefs, and Philosophy"] = nested_result
    else:
        print('No valid "Core Values, Beliefs, and Philosophy" template found in selected_paths, skipping.')
    
    # Step 4: Generate Lifestyle and Daily Routine
    life_attitude = base_info["life_attitude"]
    lifestyle_input = (
        "Life Story (for reference):\n" + str(life_story) + "\n\n"
        "Life Attitude (for reference):\n" + life_attitude + "\n\n"
        "Demographic Information (for reference):\n" + json.dumps(profile.get("Demographic Information", {}), ensure_ascii=False, indent=2) + "\n\n"
        "Career Information (for reference):\n" + json.dumps(profile.get("Career and Work Identity", {}), ensure_ascii=False, indent=2) + "\n\n"
        "Core Values (for reference):\n" + json.dumps(profile.get("Core Values, Beliefs, and Philosophy", {}), ensure_ascii=False, indent=2) + "\n\n"
        "Instructions: Based on the `life_story`, `life_attitude`, and other information provided above, generate detailed Lifestyle and Daily Routine section in English. Use the life story to inform realistic daily routines that align with the person's experiences and background.Prohibit the use of words such as' balance 'and' balance '"
    )
    lifestyle_template = selected_paths.get("Lifestyle and Daily Routine")
    if lifestyle_template and lifestyle_template != "":
        print('Generating Lifestyle and Daily Routine...')
        lifestyle_section = generate_category_attributes(lifestyle_template, lifestyle_input, "Lifestyle and Daily Routine", is_deep_generation=is_deep_generation)
        # Build nested dictionary structure
        nested_result = {}
        for path, value in lifestyle_section.items():
            parts = path.split('.')
            if len(parts) > 1 and parts[0] == "Lifestyle and Daily Routine":
                parts = parts[1:]
            
            current = nested_result
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = value
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
        profile["Lifestyle and Daily Routine"] = nested_result
    else:
        print('No valid "Lifestyle and Daily Routine" template found in selected_paths, skipping.')
    
    # Step 5: Generate Cultural and Social Context
    cultural_input = (
        "Life Story (for reference):\n" + str(life_story) + "\n\n"
        "Life Attitude (for reference):\n" + life_attitude + "\n\n"
        "Demographic Information (for reference):\n" + json.dumps(profile.get("Demographic Information", {}), ensure_ascii=False, indent=2) + "\n\n"
        "Career Information (for reference):\n" + json.dumps(profile.get("Career and Work Identity", {}), ensure_ascii=False, indent=2) + "\n\n"
        "Core Values (for reference):\n" + json.dumps(profile.get("Core Values, Beliefs, and Philosophy", {}), ensure_ascii=False, indent=2) + "\n\n"
        "Lifestyle (for reference):\n" + json.dumps(profile.get("Lifestyle and Daily Routine", {}), ensure_ascii=False, indent=2) + "\n\n"
        "Instructions: Based on the `life_story`, `life_attitude`, and other information provided above, generate detailed Cultural and Social Context section in English. Use the life story to inform realistic cultural contexts that align with the person's experiences and background.Prohibit the use of words such as' balance 'and' balance '"
    )
    cultural_template = selected_paths.get("Cultural and Social Context")
    if cultural_template and cultural_template != "":
        print('Generating Cultural and Social Context...')
        cultural_section = generate_category_attributes(cultural_template, cultural_input, "Cultural and Social Context", is_deep_generation=is_deep_generation)
        # Build nested dictionary structure
        nested_result = {}
        for path, value in cultural_section.items():
            parts = path.split('.')
            if len(parts) > 1 and parts[0] == "Cultural and Social Context":
                parts = parts[1:]
            
            current = nested_result
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = value
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
        profile["Cultural and Social Context"] = nested_result
    else:
        print('No valid "Cultural and Social Context" template found in selected_paths, skipping.')
    
    # Step 6: Generate Hobbies, Interests, and Lifestyle
    interests = base_info["interests"]
    hobbies_input = (
        "Base Information (for reference):\n" + json.dumps(base_info, ensure_ascii=False, indent=2) + "\n\n"
        "Life Story (for reference):\n" + str(life_story) + "\n\n"
        "Demographic Information (for reference):\n" + json.dumps(profile.get("Demographic Information", {}), ensure_ascii=False, indent=2) + "\n\n"
        "Career Information (for reference):\n" + json.dumps(profile.get("Career and Work Identity", {}), ensure_ascii=False, indent=2) + "\n\n"
        "Core Values, Beliefs, and Philosophy (for reference):\n" + json.dumps(profile.get("Core Values, Beliefs, and Philosophy", {}), ensure_ascii=False, indent=2) + "\n\n"
        "Lifestyle and Daily Routine (for reference):\n" + json.dumps(profile.get("Lifestyle and Daily Routine", {}), ensure_ascii=False, indent=2) + "\n\n"
        "Cultural and Social Context (for reference):\n" + json.dumps(profile.get("Cultural and Social Context", {}), ensure_ascii=False, indent=2) + "\n\n"
        "Ensure that all hobbies, interests, and lifestyle choices presented are:1.  **Firmly anchored to and primarily derived from the hobbies indicated in `base_info` and experiences from `life_story`.**2.  Logically consistent with all provided information.3.  Enriched by supplementary information where appropriate, without overshadowing the core hobbies from `base_info`.**Do not introduce new primary hobbies or interests that are not clearly supported by or cannot be reasonably inferred from the `base_info` and `life_story` themselves.** Any lifestyle elements should logically flow from or align with these established hobbies and the overall profile.Prohibit the use of words such as' balance 'and' balance '"
    )
    hobbies_template = selected_paths.get("Hobbies, Interests, and Lifestyle")
    if hobbies_template and hobbies_template != "":
        print('Generating Hobbies, Interests, and Lifestyle...')
        hobbies_section = generate_category_attributes(hobbies_template, hobbies_input, "Hobbies, Interests, and Lifestyle", is_deep_generation=is_deep_generation)
        # Build nested dictionary structure
        nested_result = {}
        for path, value in hobbies_section.items():
            parts = path.split('.')
            if len(parts) > 1 and parts[0] == "Hobbies, Interests, and Lifestyle":
                parts = parts[1:]
            
            current = nested_result
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = value
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
        profile["Hobbies, Interests, and Lifestyle"] = nested_result
    else:
        print('No valid "Hobbies, Interests, and Lifestyle" template found in selected_paths, skipping.')
    
    # Step 7: Generate Other Attributes
    other_attributes_input = (
        "Life Story (for reference):\n" + str(life_story) + "\n\n"
        "Complete Profile (for reference):\n" + json.dumps(profile, ensure_ascii=False, indent=2) + "\n\n"
        "Instructions: Based on the `life_story` and complete profile, generate the remaining attributes for the user profile in English with refined details. Ensure that all attributes are consistent with the person's life experiences as described in the life story."
    )
    other_template = selected_paths.get("Other Attributes")
    if other_template and other_template != "":
        print('Generating Other Attributes...')
        other_attributes_section = generate_category_attributes(other_template, other_attributes_input, "Other Attributes", is_deep_generation=is_deep_generation)
        # Build nested dictionary structure
        nested_result = {}
        for path, value in other_attributes_section.items():
            parts = path.split('.')
            if len(parts) > 1 and parts[0] == "Other Attributes":
                parts = parts[1:]
            
            current = nested_result
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = value
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
        profile["Other Attributes"] = nested_result
    else:
        print('No valid "Other Attributes" template found in selected_paths, skipping.')

    # Prepare a copy of profile for summary generation by removing unwanted keys
    profile_for_summary = profile.copy()
    for key in ['base_info', 'Base Info', 'personal_story', 'interests', 'Occupations']:
         profile_for_summary.pop(key, None)
    
    # Generate the final summary using the filtered profile and base_info
    final_summary_text = generate_final_summary(profile_for_summary, base_info)
    profile["Summary"] = final_summary_text
    
    # Remove unwanted keys from the final profile
    for key in ['base_info', 'Base Info', 'personal_story', 'interests', 'Occupations']:
         profile.pop(key, None)

    return profile


def generate_multiple_profiles(num_rounds: int = 8) -> None:
    """Generate multiple rounds of user profiles with varying attribute counts.

    Args:
        num_rounds: Number of rounds to generate, default 8. Each round generates profiles with different attribute counts.
    """
    start_time = time.time()
    print(f"Starting generation of {num_rounds} rounds of profiles with varying attribute counts...")

    # Get project root directory
    project_root = get_project_root()

    # Create output directory
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)

    # Define attribute counts for each profile
    attribute_counts = [100, 150, 200, 250, 300, 350]
    total_profiles = num_rounds * len(attribute_counts)

    # Initialize dictionary to store all profiles
    all_profiles = {
        "metadata": {
            "profiles_completed": 0,
            "total_profiles": total_profiles,
            "total_rounds": num_rounds,
            "description": "Collection of user profiles with varying attribute counts across multiple rounds"
        }
    }

    # Set merged file path (no timestamp)
    base_all_profiles_path = os.path.join(output_dir, f"profile_ind.json")
    all_profiles_path = base_all_profiles_path

    # Initialize and save merged file
    actual_path = save_json_file(all_profiles_path, all_profiles, use_timestamp=False)
    print(f"Initialized merged file: {actual_path}")
    all_profiles_path = actual_path  # Use actual saved path

    # Counter to track total profiles generated
    profile_count = 0

    # Generate profiles round by round
    for round_num in range(num_rounds):
        print(f"\n===== Starting round {round_num+1}/{num_rounds} =====\n")

        # Generate profiles with all different attribute counts in each round
        for attr_index, current_attribute_count in enumerate(attribute_counts):
            profile_count += 1

            print(f"\n----- Generating profile {round_num+1}.{attr_index+1} (attribute count: {current_attribute_count}) -----\n")

            try:
                # Generate single profile with attribute count
                profile = generate_single_profile(None, profile_count-1, current_attribute_count)

                if not profile:
                    print(f"Profile {round_num+1}.{attr_index+1} generation failed, skipping")
                    continue

                # Add to dictionary and save
                profile_key = f"Profile_R{round_num+1}_A{attr_index+1}_Count_{current_attribute_count}"
                all_profiles[profile_key] = profile
                all_profiles["metadata"]["profiles_completed"] = profile_count

                # Save updated merged file
                save_json_file(all_profiles_path, all_profiles, use_timestamp=False)
                print(f"\nProgress: {profile_count}/{total_profiles} profiles completed (round {round_num+1}/{num_rounds})")
                print(f"Added profile {round_num+1}.{attr_index+1} (attribute count: {current_attribute_count}) to: {all_profiles_path}")
                print("\n" + "-"*50 + "\n")
            except Exception as e:
                print(f"Error generating profile {round_num+1}.{attr_index+1}: {e}")
                continue

        print(f"\n===== Round {round_num+1}/{num_rounds} completed =====\n")
        print("\n" + "="*50 + "\n")

    # Add completion status
    all_profiles["metadata"]["status"] = "completed"
    save_json_file(all_profiles_path, all_profiles, use_timestamp=False)

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"\nAll {all_profiles['metadata']['profiles_completed']} profiles successfully generated and saved to: {all_profiles_path}")
    print(f"Generation completed in {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    generate_multiple_profiles(10)
