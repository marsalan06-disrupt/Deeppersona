# generate_user_profile package
# Import key functions from submodules

from generate_user_profile.config import get_completion, parse_gpt_response, parse_json_response
from generate_user_profile.based_data import (
    generate_age_info,
    generate_career_info,
    generate_location,
    generate_gender,
    generate_personal_values,
    generate_life_attitude,
    generate_personal_story,
    generate_interests_and_hobbies,
    get_occupations
)
from generate_user_profile.select_attributes import (
    generate_user_profile,
    get_selected_attributes
)
from generate_user_profile.generate_profile import generate_single_profile

__all__ = [
    # Config
    'get_completion',
    'parse_gpt_response',
    'parse_json_response',
    # Based data
    'generate_age_info',
    'generate_career_info',
    'generate_location',
    'generate_gender',
    'generate_personal_values',
    'generate_life_attitude',
    'generate_personal_story',
    'generate_interests_and_hobbies',
    'get_occupations',
    # Select attributes
    'generate_user_profile',
    'get_selected_attributes',
    # Generate profile
    'generate_single_profile',
]
