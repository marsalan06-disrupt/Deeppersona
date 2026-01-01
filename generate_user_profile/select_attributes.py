#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Attribute Selector Script
# This script analyzes user profiles and selects the most suitable attributes

import json
import os
import sys
import logging
from typing import Dict, List, Any, Optional, Tuple
import argparse
from pathlib import Path
import random
import numpy as np
import pickle
from tqdm import tqdm
import time
ATTRIBUTE_SELECTION_CACHE = None

# Import project configuration
from generate_user_profile.config import client, GPT_MODEL, parse_json_response

# Define get_completion function
def get_completion(messages, model=GPT_MODEL, temperature=0.7):
    """Generate text completion using OpenAI API"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return None

# Import functions from based_data module
from generate_user_profile.based_data import (
    generate_age_info,
    generate_gender,
    generate_career_info,
    generate_location,
    generate_personal_values,
    generate_life_attitude,
    generate_personal_story,
    generate_interests_and_hobbies
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Attribute dataset path
ATTRIBUTES_PATH = os.path.join(PROJECT_ROOT, 'data', 'large_attributes.json')

# Vector database path
EMBEDDINGS_PATH = os.path.join(PROJECT_ROOT, 'data', 'attribute_embeddings.pkl')

# Default model from config
DEFAULT_MODEL = GPT_MODEL

# Vector search parameters
NEAR_NEIGHBOR_COUNT = 7  # Near neighbor count
MID_NEIGHBOR_COUNT = 2   # Mid-distance neighbor count
FAR_NEIGHBOR_COUNT = 1   # Far-distance neighbor count
DIVERSITY_THRESHOLD = 0.7  # Diversity threshold (cosine similarity)

class AttributeSelector:
    """
    Attribute Selector Class
    Analyzes user profiles and selects appropriate attributes using GPT-4o
    """

    def __init__(self, model: str = DEFAULT_MODEL, user_profile: Dict = None):
        """
        Initialize attribute selector

        Args:
            model: GPT model to use
            user_profile: User profile data (optional)
        """
        self.model = model

        # OpenAI client is set up in config.py

        # Load attribute data
        self.attributes = self._load_json(ATTRIBUTES_PATH)

        # Set user profile
        self.user_profile = user_profile

        # Validate data
        self._validate_data()

        # Load vector database
        self.embeddings_data = self._load_embeddings()

        # Initialize attribute paths and vector mappings
        self.path_to_embedding = {}
        self.paths = []
        self.embeddings = []

        if self.embeddings_data:
            self.paths = self.embeddings_data.get('paths', [])
            self.embeddings = self.embeddings_data.get('embeddings', [])

            # Create path to vector mapping
            for i, path in enumerate(self.paths):
                if i < len(self.embeddings):
                    self.path_to_embedding[path] = self.embeddings[i]

            logger.info(f"Loaded {len(self.paths)} attribute paths with corresponding embeddings")

        logger.info(f"Loaded attributes with {len(self.attributes.keys())} top-level categories")
    
    def _load_json(self, file_path: str) -> Dict:
        """Load JSON data from file"""
        try:
            return json.loads(Path(file_path).read_text(encoding='utf-8'))
        except Exception as e:
            logger.error(f"Error loading JSON from {file_path}: {e}")
            raise

    def _load_embeddings(self) -> Dict:
        """Load attribute embeddings vector database"""
        try:
            if not os.path.exists(EMBEDDINGS_PATH):
                logger.warning(f"Embeddings file {EMBEDDINGS_PATH} does not exist")
                return None

            with open(EMBEDDINGS_PATH, 'rb') as f:
                embeddings_data = pickle.load(f)

            # Check data structure and standardize key names
            paths_key = 'attribute_paths' if 'attribute_paths' in embeddings_data else 'paths'
            embeddings_key = 'embeddings'

            # Get paths and embeddings
            paths = embeddings_data.get(paths_key, [])
            embeddings = embeddings_data.get(embeddings_key, [])

            # Return None if data is invalid
            if not isinstance(embeddings_data, dict) or not paths or not isinstance(embeddings, np.ndarray):
                logger.warning("Invalid embeddings data format")
                return None

            # Standardize returned data dictionary
            standardized_data = {
                'paths': paths,
                'embeddings': embeddings
            }

            logger.info(f"Loaded {len(paths)} attribute embeddings from {EMBEDDINGS_PATH}")
            return standardized_data

        except Exception as e:
            logger.error(f"Error loading embeddings: {e}")
            return None

    def _validate_data(self):
        """Validate loaded data and convert format if needed"""
        # Check attribute format
        if isinstance(self.attributes, dict):
            # If nested dict format (like large_attributes.json), convert to path format
            if "paths" not in self.attributes:
                logger.info("Converting attributes from nested dict format to path format")
                self.attributes = {"paths": self._flatten_attributes(self.attributes)}
        else:
            raise ValueError("Invalid attribute format: not a dictionary")
            
    def _create_profile_embedding(self, profile: Dict) -> np.ndarray:
        """
        Create embedding vector for user profile

        Args:
            profile: User profile dictionary

        Returns:
            Profile embedding vector
        """
        try:
            # Extract profile summary
            profile_summary = self._extract_profile_summary(profile)

            # Generate embedding using OpenAI API
            response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=profile_summary
            )

            # Extract embedding vector
            embedding = np.array(response.data[0].embedding)
            logger.info(f"Successfully created embedding for user profile")
            return embedding

        except Exception as e:
            logger.error(f"Error creating profile embedding: {e}")
            return None
            
    def _compute_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity value, range [-1, 1]
        """
        # Handle empty vectors or None values
        if vec1 is None or vec2 is None or len(vec1) == 0 or len(vec2) == 0:
            return 0.0

        # Ensure vector dimensions match
        if len(vec1) != len(vec2):
            logger.warning(f"Vector dimension mismatch: {len(vec1)} vs {len(vec2)}")
            return 0.0

        # Compute vector norms
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        # Handle zero vectors
        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Compute cosine similarity
        return np.dot(vec1, vec2) / (norm1 * norm2)

    def get_profile(self) -> Dict:
        """Get user profile"""
        return self.user_profile
        
    def _check_if_career_needed(self, profile: Dict, profile_summary: str) -> bool:
        """
        Use GPT to determine if "Career and Work Identity" attributes are needed

        Args:
            profile: User profile dictionary
            profile_summary: User profile summary

        Returns:
            Boolean indicating whether career-related attributes are needed
        """
        # Create prompt for determining career attribute necessity
        prompt = f"""
        # Career Attribute Necessity Assessment
        
        ## User Profile Summary:
        {profile_summary}
        
        ## Task Description:
        You are an AI assistant tasked with determining whether the "Career and Work Identity" attribute category is relevant and necessary for this specific individual based on their profile.
        
        Consider the following factors:
        1. The person's age and life stage
        2. Current employment or educational status
        3. How central career and work identity appears to be to this person's life
        4. Whether career information would be essential to create a complete picture of this person
        
        ## Output Format:
        Provide a JSON response with these keys:
        1. "is_career_needed": Boolean (true/false) indicating whether Career and Work Identity attributes are needed
        2. "reasoning": String explaining your rationale
        
        Your response must be valid JSON that can be parsed by Python's json.loads() function.
        """
        
        try:
            # Call GPT API using get_completion function from config.py
            messages = [
                {"role": "system", "content": "You are an AI assistant that analyzes user profiles and determines whether career attributes are necessary. You always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ]
            content = get_completion(messages, model=self.model, temperature=0.3)

            # Use the project's JSON parsing function
            result = parse_json_response(content, {"is_career_needed": True, "reasoning": "Career attributes needed by default"})

            # Ensure result contains necessary keys
            if "is_career_needed" not in result:
                logger.warning("Missing 'is_career_needed' key in GPT response, defaulting to True")
                result["is_career_needed"] = True

            logger.info(f"Career attributes needed: {result['is_career_needed']}, Reason: {result.get('reasoning', 'No reasoning provided')}")

            return result["is_career_needed"]

        except Exception as e:
            logger.error(f"Error calling GPT API for career assessment: {e}")
            # Default to needing career attributes on error
            return True
    
    def _extract_profile_summary(self, profile: Dict) -> str:
        """
        Extract profile summary for GPT analysis

        Args:
            profile: User profile dictionary

        Returns:
            Profile summary string
        """
        summary_parts = []
        
        # Add age information
        if "age_info" in profile:
            age_info = profile["age_info"]
            if "age" in age_info:
                summary_parts.append(f"Age: {age_info['age']}")
            if "age_group" in age_info:
                summary_parts.append(f"Age Group: {age_info['age_group']}")
        
        # Add gender information
        if "gender" in profile:
            gender = profile["gender"]
            # Convert Chinese characters to English if needed
            if gender == "male":
                gender = "Male"
            elif gender == "female":
                gender = "Female"
            summary_parts.append(f"Gender: {gender}")
        
        # Add location information
        if "location" in profile:
            location = profile["location"]
            location_str = f"{location.get('city', '')}, {location.get('country', '')}"
            summary_parts.append(f"Location: {location_str}")
        
        # Add career information
        if "career_info" in profile and "status" in profile["career_info"]:
            summary_parts.append(f"Career Status: {profile['career_info']['status']}")
        
        # Add personal values
        if "personal_values" in profile and "values_orientation" in profile["personal_values"]:
            summary_parts.append(f"Values: {profile['personal_values']['values_orientation']}")
        
        # Add life attitude
        if "life_attitude" in profile:
            attitude = profile["life_attitude"]
            if "attitude" in attitude:
                summary_parts.append(f"Life Attitude: {attitude['attitude']}")
            if "attitude_details" in attitude:
                summary_parts.append(f"Attitude Details: {attitude['attitude_details']}")
            if "coping_mechanism" in attitude:
                summary_parts.append(f"Coping Mechanism: {attitude['coping_mechanism']}")
        
        # Add interests
        if "interests" in profile and "interests" in profile["interests"]:
            interests = profile["interests"]["interests"]
            if interests and isinstance(interests, list):
                summary_parts.append(f"Interests: {', '.join(interests)}")
        
        # Add personal story (life_story)
        if "personal_story" in profile and "personal_story" in profile["personal_story"]:
            life_story = profile["personal_story"]["personal_story"]
            if life_story:
                summary_parts.append(f"Life Story: {life_story}")

        # Add summary if available
        if "summary" in profile:
            summary_parts.append(f"Profile Summary: {profile['summary']}")

        # Now includes complete based_data info including life_story

        return "\n".join(summary_parts)
    
    def _flatten_attributes(self, attributes: Dict, prefix: str = "") -> List[str]:
        """
        Flatten attribute dictionary into attribute path list

        Args:
            attributes: Attribute dictionary or sub-dictionary
            prefix: Current path prefix
        """
        result = []

        def _flatten(attr_dict, curr_prefix):
            for k, v in attr_dict.items():
                path = f"{curr_prefix}.{k}" if curr_prefix else k
                # Only leaf nodes (empty dicts) are added to result
                if isinstance(v, dict):
                    if not v:  # Empty dict, this is a leaf node
                        result.append(path)
                    else:  # Non-empty dict, continue recursion
                        _flatten(v, path)
                else:  # Non-dict value, add directly
                    result.append(path)

        _flatten(attributes, prefix)
        return result

    def _get_attribute_categories(self) -> List[str]:
        """Get top-level attribute categories"""
        # Extract unique top-level categories from paths
        return sorted({path.split('.')[0] for path in self.attributes["paths"]})
    
    def _format_attributes_tree(self, attributes_dict: Dict, prefix: str = "", depth: int = 0) -> List[str]:
        """
        Format attribute dictionary as text tree structure

        Args:
            attributes_dict: Attribute dictionary
            prefix: Current path prefix
            depth: Current depth in tree

        Returns:
            List of formatted lines representing tree
        """
        lines = []
        
        for key, value in sorted(attributes_dict.items()):
            current_path = f"{prefix}.{key}" if prefix else key
            indent = "  " * depth
            
            if depth > 0:
                prefix_char = "│ " * (depth - 1) + "- "
            else:
                prefix_char = "- "
                
            lines.append(f"{indent}{prefix_char}{key}")
            
            if isinstance(value, dict) and value:
                sub_lines = self._format_attributes_tree(value, current_path, depth + 1)
                lines.extend(sub_lines)
                
        return lines
    
    def analyze_profile_for_attributes(self, profile: Dict) -> Dict[str, List[str]]:
        """
        Analyze user profile and determine which attributes should be generated

        Args:
            profile: User profile dictionary

        Returns:
            Dictionary containing 'recommended' and 'not_recommended' attribute categories
        """
        # Extract profile summary
        profile_summary = self._extract_profile_summary(profile)

        # Get attribute categories
        categories = self._get_attribute_categories()

        # Step 1: Use GPT to determine if "Career and Work Identity" is needed
        career_needed = self._check_if_career_needed(profile, profile_summary)

        # Step 2: Keep all first-level attributes (except possibly excluded "Career and Work Identity")
        recommended_categories = []
        not_recommended_categories = []

        for category in categories:
            if category == "Career and Work Identity" and not career_needed:
                not_recommended_categories.append(category)
                logger.info(f"Based on analysis, career and work identity attributes not needed")
            else:
                recommended_categories.append(category)

        # Generate result
        result = {
            "recommended": recommended_categories,
            "not_recommended": not_recommended_categories,
            "reasoning": f"Based on user background analysis, career and work identity attributes {'are' if career_needed else 'are not'} needed. Keeping all other first-level attributes, selecting features that best match user background."
        }

        return result
    
    def process_profile(self) -> Dict:
        """
        Process user profile and generate attribute recommendations

        Returns:
            Dictionary containing profile and attribute recommendations
        """
        # Generate user profile if not provided
        if not self.user_profile:
            self.user_profile = generate_user_profile()

        # Extract profile summary
        profile_summary = self._extract_profile_summary(self.user_profile)

        # Analyze profile and get attribute recommendations
        attribute_recommendations = self.analyze_profile_for_attributes(self.user_profile)

        # Return result
        return {
            "profile_summary": profile_summary,
            "attribute_recommendations": attribute_recommendations
        }
    
    def _get_nested_attributes(self, category: str) -> Dict:
        """
        Get nested attributes for specific category by rebuilding from paths

        Args:
            category: Category name
        """
        result = {}

        # Filter paths starting with this category and rebuild nested structure
        for path in [p for p in self.attributes["paths"] if p.startswith(f"{category}.")]:
            parts = path.split('.')[1:]  # Skip first part (category)
            current = result

            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = {}  # Leaf node
                else:
                    current.setdefault(part, {})  # Create if key doesn't exist
                    current = current[part]

        return result
    

    
    def select_top_attributes(self, path_list, target_count=200):
        """
        Select the most important and representative top-level attributes from path list.

        Args:
            path_list: List of attribute paths
            target_count: Target number of attributes to select

        Returns:
            List of selected attribute paths
        """
        if not path_list:
            return []
            
        # If we already have fewer paths than target, return all of them
        if len(path_list) <= target_count:
            return path_list
        
        # Extract unique top-level categories
        categories = {}
        for path in path_list:
            parts = path.split('.')
            if len(parts) > 0:
                category = parts[0]
                if category not in categories:
                    categories[category] = []
                categories[category].append(path)
        
        # Calculate how many attributes to select from each category
        # proportional to their representation in the original list
        total_paths = len(path_list)
        category_counts = {}
        for category, paths in categories.items():
            # Calculate proportional count but ensure at least 1 attribute per category
            count = max(1, int(len(paths) / total_paths * target_count))
            category_counts[category] = count
        
        # Adjust counts to match target_count as closely as possible
        total_selected = sum(category_counts.values())
        if total_selected < target_count:
            # Distribute remaining slots to largest categories
            remaining = target_count - total_selected
            sorted_categories = sorted(categories.keys(), 
                                      key=lambda c: len(categories[c]), 
                                      reverse=True)
            for i in range(remaining):
                if i < len(sorted_categories):
                    category_counts[sorted_categories[i]] += 1
        elif total_selected > target_count:
            # Remove from largest categories until we hit target
            excess = total_selected - target_count
            sorted_categories = sorted(categories.keys(), 
                                      key=lambda c: category_counts[c], 
                                      reverse=True)
            for i in range(excess):
                if i < len(sorted_categories) and category_counts[sorted_categories[i]] > 1:
                    category_counts[sorted_categories[i]] -= 1
        
        # Select paths from each category
        selected_paths = []
        for category, count in category_counts.items():
            category_paths = categories[category]
            
            # Prioritize paths with fewer segments (more general attributes)
            # and paths that represent common attributes across domains
            scored_paths = []
            for path in category_paths:
                parts = path.split('.')
                # Score is based on path depth (shorter is better) and presence of common terms
                common_terms = ['general', 'common', 'basic', 'core', 'essential', 'fundamental', 'key']
                common_term_bonus = any(term in path.lower() for term in common_terms)
                score = (10 - len(parts)) + (5 if common_term_bonus else 0)
                scored_paths.append((path, score))
            
            # Sort by score (higher is better) and select top paths
            sorted_paths = sorted(scored_paths, key=lambda x: x[1], reverse=True)
            selected_category_paths = [p[0] for p in sorted_paths[:count]]
            selected_paths.extend(selected_category_paths)
        
        return selected_paths
    
    # Note: Removed _select_best_matching_attributes method as it was replaced by new random selection and GPT filtering method

    def _find_interesting_neighbors(self, profile_embedding: np.ndarray, category_paths: List[str],
    target_count: int = 300) -> List[str]:
        """
        Implement "interesting neighbors" vector search scheme

        Args:
            profile_embedding: User profile embedding vector
            category_paths: List of attribute paths for specific category
            target_count: Target number of attributes to select

        Returns:
            List of selected attribute paths or empty list if read issues occur
        """
        # Return empty list if no vector database or paths are empty
        if not self.embeddings_data or not category_paths:
            logger.warning("No vector database available or category paths empty, returning empty list")
            return []

        # Filter paths that have embeddings in vector database
        valid_paths = [path for path in category_paths if path in self.path_to_embedding]

        if not valid_paths:
            logger.warning("No valid attribute paths match vector database, returning empty list")
            return []

        # Calculate similarity between each path and profile
        path_similarities = []
        for path in valid_paths:
            embedding = self.path_to_embedding[path]
            similarity = self._compute_cosine_similarity(profile_embedding, embedding)
            path_similarities.append((path, similarity))

        # Sort by similarity
        path_similarities.sort(key=lambda x: x[1], reverse=True)

        # Calculate number to select
        total_paths = len(path_similarities)

        # Return all paths if fewer than target count
        if total_paths <= target_count:
            return [p[0] for p in path_similarities]

        selected_paths = []
        used_indices = set()

        # Allocate near, mid-distance, far-distance neighbors in 5:3:2 ratio
        total_ratio = 5 + 3 + 2  # Total ratio = 10

        # 1. Select near neighbors (highest similarity) - 50% (5/10)
        near_count = min(int(target_count * 5 / total_ratio), total_paths // 3)
        near_indices = list(range(near_count))
        for i in random.sample(near_indices, min(near_count, len(near_indices))):
            if i not in used_indices:
                selected_paths.append(path_similarities[i][0])
                used_indices.add(i)

        # 2. Select mid-distance neighbors - 30% (3/10)
        mid_start = total_paths // 3
        mid_end = 2 * total_paths // 3
        mid_count = min(int(target_count * 3 / total_ratio), (mid_end - mid_start))
        mid_indices = list(range(mid_start, mid_end))
        if mid_indices:
            for i in random.sample(mid_indices, min(mid_count, len(mid_indices))):
                if i not in used_indices:
                    selected_paths.append(path_similarities[i][0])
                    used_indices.add(i)

        # 3. Select far-distance neighbors (lowest similarity) - 20% (2/10)
        far_start = 2 * total_paths // 3
        far_count = min(int(target_count * 2 / total_ratio), (total_paths - far_start))
        far_indices = list(range(far_start, total_paths))
        if far_indices:
            for i in random.sample(far_indices, min(far_count, len(far_indices))):
                if i not in used_indices:
                    selected_paths.append(path_similarities[i][0])
                    used_indices.add(i)

        # If more attributes needed to reach target, randomly select from unused indices
        remaining_count = target_count - len(selected_paths)
        if remaining_count > 0:
            remaining_indices = [i for i in range(total_paths) if i not in used_indices]
            if remaining_indices:
                additional_count = min(remaining_count, len(remaining_indices))
                for i in random.sample(remaining_indices, additional_count):
                    selected_paths.append(path_similarities[i][0])

        logger.info(f"Selected {len(selected_paths)} attributes using vector search (near: {near_count}, mid: {mid_count}, far: {far_count})")
        return selected_paths
    
    def get_top_attributes(self, result: Dict, target_count: int = 200) -> List[str]:
        """
        Get attribute list

        Args:
            result: Result from analyze_profile_for_attributes
            target_count: Target attribute count

        Returns:
            List of attribute paths
        """
        try:
            # Collect all recommended categories
            all_recommended = set()

            if "recommended" in result:
                all_recommended.update(result["recommended"])

            # Extract all paths
            all_paths = []
            category_paths = {}

            if "paths" in self.attributes:
                # If using new format with paths
                for path in self.attributes["paths"]:
                    # Only include paths from recommended categories
                    category = path.split('.')[0] if '.' in path else path
                    if category in all_recommended:
                        all_paths.append(path)
                        # Group paths by category
                        if category not in category_paths:
                            category_paths[category] = []
                        category_paths[category].append(path)
            else:
                # If using old nested format, flatten it
                for category in all_recommended:
                    paths = self._flatten_attributes(self._get_nested_attributes(category), category)
                    all_paths.extend(paths)
                    category_paths[category] = paths

            # Use passed target_count parameter, no longer random selection

            # If vector database available, use vector search
            if self.embeddings_data and self.user_profile:
                # Create user profile embedding
                profile_embedding = self._create_profile_embedding(self.user_profile)

                if profile_embedding is not None:
                    # Select attributes for each category
                    final_paths = []
                    for category, paths in category_paths.items():
                        # Allocate target count proportionally based on category size
                        category_ratio = len(paths) / len(all_paths)
                        category_target = max(3, int(target_count * category_ratio))

                        # Use vector search to select attributes for this category
                        category_selected = self._find_interesting_neighbors(
                            profile_embedding, paths, category_target
                        )
                        final_paths.extend(category_selected)

                    # If selected attributes exceed target count, randomly reduce
                    if len(final_paths) > target_count:
                        final_paths = random.sample(final_paths, target_count)

                    logger.info(f"Selected {len(final_paths)} attributes from {len(all_paths)} using vector search")
                    return final_paths

            # If no vector database or vector search failed, return empty list
            logger.warning(f"No vector database available or vector search failed, returning empty list")
            return []

        except Exception as e:
            logger.error(f"Error generating attribute list: {e}")
            # Return empty list on error
            logger.error(f"Attribute selection process error, returning empty list")
            return []

    # Note: Removed _random_select_from_top_categories method as random selection now happens directly in get_top_attributes
    


def generate_user_profile() -> Dict:
    """Generate user base profile"""
    # Generate and store direct function return values
    age_info = generate_age_info()
    gender = generate_gender()
    location = generate_location()
    career_info = generate_career_info(age_info["age"])

    # Generate personal values
    values = generate_personal_values(
        age=age_info["age"],
        gender=gender,
        occupation=career_info["status"],
        location=location
    )

    # Generate life attitude
    life_attitude = generate_life_attitude(
        age=age_info["age"],
        gender=gender,
        occupation=career_info["status"],
        location=location,
        values_orientation=values.get("values_orientation", "")
    )

    # Generate personal story
    personal_story = generate_personal_story(
        age=age_info["age"],
        gender=gender,
        occupation=career_info["status"],
        location=location,
        values_orientation=values.get("values_orientation", ""),
        life_attitude=life_attitude
    )

    # Generate interests and hobbies
    interests = generate_interests_and_hobbies(personal_story)

    # Store function return values
    user_profile = {
        "age_info": age_info,
        "gender": gender,
        "location": location,
        "career_info": career_info,
        "personal_values": values,
        "life_attitude": life_attitude,
        "personal_story": personal_story,
        "interests": interests
    }

    return user_profile

def get_selected_attributes(user_profile=None, attribute_count=200):
    global ATTRIBUTE_SELECTION_CACHE
    # Cache mechanism commented out to ensure fresh attribute selection each time
    # if ATTRIBUTE_SELECTION_CACHE is not None:
    #     return ATTRIBUTE_SELECTION_CACHE

    try:
        # Generate user profile if not provided
        if user_profile is None:
            user_profile = generate_user_profile()

        # Create selector with user profile
        selector = AttributeSelector(user_profile=user_profile)

        # Process profile
        result = selector.process_profile()

        # Get attribute recommendations
        attribute_recommendations = result.get("attribute_recommendations", {})

        # Get attribute list using passed attribute_count parameter
        top_paths = selector.get_top_attributes(attribute_recommendations, target_count=attribute_count)

        # Return attribute list
        ATTRIBUTE_SELECTION_CACHE = top_paths
        return top_paths

    except Exception as e:
        logger.error(f"Error getting selected attributes: {e}")
        return []

def build_nested_dict(paths: List[str]) -> Dict:
    result = {}
    for path in paths:
        parts = path.split('.')
        current = result
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]
    return result

def save_results(user_profile: Dict, selected_paths: List[str], output_dir: str = None) -> None:
    """
    Save user profile and selected attribute paths to files.
    Args:
        user_profile: User profile dictionary
        selected_paths: Selected attribute paths (list format)
        output_dir: Output directory (defaults to 'generate_user_profile/output')
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), 'output')
    try:
        from pathlib import Path
        import json
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save user profile
        profile_path = output_path / "user_profile.json"
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(user_profile, f, ensure_ascii=False, indent=2)
        logger.info(f"User profile saved to {profile_path}")

        # Convert selected_paths to nested dictionary structure
        nested_selected_paths = build_nested_dict(selected_paths)

        # Save attribute paths (nested dictionary format)
        paths_path = output_path / "selected_paths.json"
        with open(paths_path, 'w', encoding='utf-8') as f:
            json.dump(nested_selected_paths, f, ensure_ascii=False, indent=2)
        logger.info(f"Attribute paths saved to {paths_path}")
    except Exception as e:
        logger.error(f"Error saving results: {e}")
        raise

# Example: Auto-save in user profile and attribute list generation functions
# Only run when executed directly, not when imported
if __name__ == "__main__":
    user_profile = generate_user_profile()
    selected_paths = get_selected_attributes(user_profile)
    save_results(user_profile, selected_paths)
