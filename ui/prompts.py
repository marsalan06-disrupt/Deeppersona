"""
All system and user prompts used in Deeppersona profile generation.
These can be viewed and edited in the UI.
"""

# ============== STEP 1: BASE PROFILE PROMPTS ==============

CAREER_INFO_SYSTEM = """You are an AI that generates realistic occupation statuses based on age. Respond with just the status, no explanation."""

CAREER_INFO_USER = """Generate an appropriate occupation or status for a {age} year old person. {age_context}"""

CAREER_INFO_YOUNG_CONTEXT = """Consider that the individuals are likely in school or engaged in youth activities. They may not have any formal occupation. If appropriate, you can mention their student status or indicate they have no occupation yet. Only in some cases, consider potential interest in early employment opportunities, internships, or non-traditional educational paths."""

CAREER_INFO_SENIOR_CONTEXT = """Consider they might be retired but could still be active in various ways."""


PERSONAL_VALUES_SYSTEM = """You are an assistant that generates realistic human value systems in ONE SENTENCE, including both positive and negative values. You ALWAYS respond with valid JSON objects that can be parsed by json.loads()."""

PERSONAL_VALUES_USER = """Generate a concise description of a person's core values and belief system based on:
Age: {age}, Gender: {gender}, Occupation: {occupation}, Location: {city}, {country}

IMPORTANT: This person has a {value_type} value system. Their values may be entirely consistent with their personal background or may conflict with it. Avoid introducing unnecessary contrasts or contradictions in their beliefs. Try to avoid being related to the community as much as possible. Avoid using words with similar meanings to 'balance' and 'balance'.

Please generate a short phrase that clearly captures the essence of this person's core values and beliefs without adding conflicting ideas or turnarounds.

CRITICAL: You must format your response EXACTLY as a valid JSON object with this structure:
{{
    "values_orientation": "short phrase describing their values"
}}

DO NOT include any text before or after the JSON. The response must be parseable by json.loads()."""


LIFE_ATTITUDE_SYSTEM = """You are an assistant that generates realistic human life attitudes in ONE SENTENCE, including positive, neutral, and negative outlooks. You ALWAYS respond with valid JSON objects that can be parsed by json.loads()."""

LIFE_ATTITUDE_USER = """Generate specific attributes about a person's life attitude based on the following information:

Age: {age}
Gender: {gender}
Occupation: {occupation}
Location: {city}, {country}
Core Values: {values_orientation}

IMPORTANT: This person's attitude toward life can be positive, neutral, or negative. In a negative state, they may hold a pessimistic, cynical, or even nihilistic view of life. Avoid involving concepts such as community or balance. Avoid using words with similar meanings to 'balance' and 'balance'.

I need you to generate ONLY the following specific attributes, each expressed as a single sentence:

1. attitude: A single, concise sentence (5-10 words) describing their overall life attitude
2. attitude_details: A single sentence (15-20 words) explaining how this attitude manifests in their daily life
3. coping_mechanism: A single sentence (5-10 words) describing how they deal with challenges

CRITICAL: You must format your response EXACTLY as a valid JSON object with this structure:
{{"attitude": "single sentence", "attitude_details": "single sentence", "coping_mechanism": "single sentence"}}

DO NOT include any text before or after the JSON. The response must be parseable by json.loads()."""


PERSONAL_STORY_SYSTEM = """You are an assistant that generates concise realistic personal stories, including both positive and negative life experiences. You ALWAYS respond with valid JSON objects that can be parsed by json.loads()."""

PERSONAL_STORY_USER = """Generate {num_stories} concise personal stories for a person with the following characteristics:

Age: {age}
Gender: {gender}
Occupation: {occupation}
Location: {city}, {country}
Core Values: {values_orientation}
Life Attitude: {attitude} ({attitude_category})

IMPORTANT: The story can be positive, negative, or a mix of both. Please do not avoid including life experiences that may be controversial or have negative consequences. The narration should be as specific as possible, objective, and free from any subjective comments or value judgments. The stories that unfold should be closely related to their country and region, reflecting events that could genuinely happen to the people there. This could be a random event unrelated to the background, or a significant turning point in their life. Please avoid including anything related to community building.

Please provide {num_stories} brief personal stories (each 150-200 words).

CRITICAL: You must format your response EXACTLY as a valid JSON object with this structure:
{{"personal_stories": ["story 1", "story 2", ...]}}

DO NOT include any text before or after the JSON. The response must be parseable by json.loads()."""


INTERESTS_SYSTEM = """You are an assistant that extracts realistic interests and hobbies from a person's life story, including both positive activities and negative habits. You ALWAYS respond with valid JSON objects that can be parsed by json.loads()."""

INTERESTS_USER = """Based on the following personal story and key life events, infer two to three hobbies or interests this person might use to relax. These activities can be positive or negative and may include non-traditional, controversial, or unexpected ones, such as various sports, traveling, or even smoking, drinking, or using marijuana. Please make inferences about the person's possible interests based on the story, rather than simply extracting them directly from the story.

Personal Story: {story_text}

IMPORTANT: Avoid including anything related to community-building activities.

Please extract 2 hobbies or interests based on these reflections and format your response as a JSON object:

{{
   "interests": ["interest1", "interest2"]
}}

DO NOT include any text before or after the JSON. The response must be parseable by json.loads()."""


# ============== STEP 2: ATTRIBUTE SELECTION PROMPTS ==============

CAREER_NEEDED_SYSTEM = """You are a profile analyzer. Your task is to determine if career-related attributes are necessary for a complete user profile. You ALWAYS respond with valid JSON."""

CAREER_NEEDED_USER = """Based on the following user profile summary, determine if "Career and Work Identity" attributes are essential to create a complete picture of this person.

User Profile Summary:
{profile_summary}

Consider:
1. Is this person currently working or in a career-focused life stage?
2. Would career attributes add meaningful information to their profile?
3. Are there other aspects of their life that are more defining?

Respond with a JSON object:
{{"is_career_needed": true/false, "reasoning": "brief explanation"}}"""


# ============== STEP 3: PROFILE SECTION PROMPTS ==============

SECTION_GENERATION_SYSTEM = """Format your response as a JSON object where each key is the attribute path and each value is the generated attribute value (not exceeding 100 characters)."""


DEMOGRAPHIC_USER = """Base Information (for reference):
{base_info}

Life Story (for reference):
{life_story}

Instructions: Based on the `base_info` and `life_story` provided, **develop and elaborate on** the 'Demographic Information' section in English. Your task is to **appropriately expand upon and enrich** the existing information from `base_info` and incorporate relevant insights from the `life_story`. Focus on elaborating on the given data points, adding further relevant details, or providing context to make the demographic profile more comprehensive and insightful. While you should avoid simply repeating the `base_info` verbatim, ensure that all generated content is **directly built upon and logically extends** the information available in `base_info` and `life_story`, rather than introducing entirely new, unrelated demographic facts. The goal is a coherent, more descriptive, and enhanced version of the original data that reflects the person's life experiences."""


CAREER_USER = """Base Information (for reference):
{base_info}

Life Story (for reference):
{life_story}

Demographic Information (for reference):
{demographic_info}

Instructions: Based on the `base_info`, `life_story`, and `Demographic Information` provided above, **develop and elaborate on** the 'Career and Work Identity' section in English. Your aim is to distill and articulate the career identity, professional journey, and work-related aspirations that are **evident or can be reasonably inferred from the combined `base_info`, `life_story`, and `Demographic Information`**. Offer fresh insights by providing a **deeper, more nuanced interpretation or by highlighting connections within the provided data** that illuminate these aspects. Ensure that this elaboration is **logically consistent with and directly stems from** the provided information. **Do not introduce new career details or aspirations that are not grounded in or clearly supported by the source material.** The section should be an insightful and coherent expansion of what can be understood from the source material."""


CORE_VALUES_USER = """Life Story (for reference):
{life_story}

Demographic Information (for reference):
{demographic_info}

Career Information (for reference):
{career_info}

Personal Values (for reference):
{values_orientation}

Instructions: Based on the `life_story` and other information provided above, **develop and elaborate on** the 'Core Values, Beliefs, and Philosophy' section in English. Your aim is to distill and articulate the core values, beliefs, and philosophical outlook that are **evident or can be reasonably inferred from the `life_story` and other provided information**. Offer fresh insights by providing a **deeper, more nuanced interpretation or by highlighting connections within the provided data** that illuminate these guiding principles. Ensure that this elaboration is **logically consistent with and directly stems from** the provided information. **Do not introduce new values, beliefs, or philosophies that are not grounded in or clearly supported by the source material.** The section should be an insightful and coherent expansion of what can be understood from the source material. IMPORTANT: Avoid including anything related to community-building activities. Prohibit the use of words such as 'balance'."""


LIFESTYLE_USER = """Life Story (for reference):
{life_story}

Life Attitude (for reference):
{life_attitude}

Demographic Information (for reference):
{demographic_info}

Career Information (for reference):
{career_info}

Core Values (for reference):
{core_values}

Instructions: Based on the `life_story`, `life_attitude`, and other information provided above, generate detailed Lifestyle and Daily Routine section in English. Use the life story to inform realistic daily routines that align with the person's experiences and background. Prohibit the use of words such as 'balance'."""


CULTURAL_USER = """Life Story (for reference):
{life_story}

Life Attitude (for reference):
{life_attitude}

Demographic Information (for reference):
{demographic_info}

Career Information (for reference):
{career_info}

Core Values (for reference):
{core_values}

Lifestyle (for reference):
{lifestyle}

Instructions: Based on the `life_story`, `life_attitude`, and other information provided above, generate detailed Cultural and Social Context section in English. Use the life story to inform realistic cultural contexts that align with the person's experiences and background. Prohibit the use of words such as 'balance'."""


HOBBIES_USER = """Base Information (for reference):
{base_info}

Life Story (for reference):
{life_story}

Demographic Information (for reference):
{demographic_info}

Career Information (for reference):
{career_info}

Core Values, Beliefs, and Philosophy (for reference):
{core_values}

Lifestyle and Daily Routine (for reference):
{lifestyle}

Cultural and Social Context (for reference):
{cultural}

Ensure that all hobbies, interests, and lifestyle choices presented are:
1. **Firmly anchored to and primarily derived from the hobbies indicated in `base_info` and experiences from `life_story`.**
2. Logically consistent with all provided information.
3. Enriched by supplementary information where appropriate, without overshadowing the core hobbies from `base_info`.
**Do not introduce new primary hobbies or interests that are not clearly supported by or cannot be reasonably inferred from the `base_info` and `life_story` themselves.** Any lifestyle elements should logically flow from or align with these established hobbies and the overall profile. Prohibit the use of words such as 'balance'."""


OTHER_ATTRIBUTES_USER = """Life Story (for reference):
{life_story}

Complete Profile (for reference):
{complete_profile}

Instructions: Based on the `life_story` and complete profile, generate the remaining attributes for the user profile in English with refined details. Ensure that all attributes are consistent with the person's life experiences as described in the life story."""


# ============== FINAL SUMMARY PROMPTS ==============

SUMMARY_SYSTEM = """Your task: Based solely on the provided user attributes and personal story, create an objective and factual personal profile, strictly between 150–400 words.

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
	•	Prohibit the use of words such as 'balance'."""

SUMMARY_USER = """Complete Profile (in JSON format):
{profile_json}

Generate a first-person narrative of 100-400 words from the provided profile. Your primary goal is to make the person feel real, believable, and authentic.

To achieve this, strictly follow the 'Show, Don't Tell' principle:
1.  **Illustrate, Don't Declare:** Show values and traits through specific actions, stories, and decisions, rather than stating them directly.
2.  **Connect Actions to Motivation:** Briefly explain the 'why' behind key life choices and habits to reveal the person's inner logic and create narrative depth.
3.  **Maintain a Natural Voice:** The tone must be sincere and grounded—thoughtful but not overly abstract or dramatic.

Weave all elements into a cohesive story, not a simple list of facts."""


# ============== HELPER: Get all prompts as dict ==============

def get_all_prompts():
    """Return all prompts organized by step."""
    return {
        "step1_base_profile": {
            "career_info": {
                "system": CAREER_INFO_SYSTEM,
                "user": CAREER_INFO_USER,
                "young_context": CAREER_INFO_YOUNG_CONTEXT,
                "senior_context": CAREER_INFO_SENIOR_CONTEXT
            },
            "personal_values": {
                "system": PERSONAL_VALUES_SYSTEM,
                "user": PERSONAL_VALUES_USER
            },
            "life_attitude": {
                "system": LIFE_ATTITUDE_SYSTEM,
                "user": LIFE_ATTITUDE_USER
            },
            "personal_story": {
                "system": PERSONAL_STORY_SYSTEM,
                "user": PERSONAL_STORY_USER
            },
            "interests": {
                "system": INTERESTS_SYSTEM,
                "user": INTERESTS_USER
            }
        },
        "step2_attributes": {
            "career_needed": {
                "system": CAREER_NEEDED_SYSTEM,
                "user": CAREER_NEEDED_USER
            }
        },
        "step3_sections": {
            "section_generation": {
                "system": SECTION_GENERATION_SYSTEM
            },
            "demographic": {
                "user": DEMOGRAPHIC_USER
            },
            "career": {
                "user": CAREER_USER
            },
            "core_values": {
                "user": CORE_VALUES_USER
            },
            "lifestyle": {
                "user": LIFESTYLE_USER
            },
            "cultural": {
                "user": CULTURAL_USER
            },
            "hobbies": {
                "user": HOBBIES_USER
            },
            "other_attributes": {
                "user": OTHER_ATTRIBUTES_USER
            },
            "summary": {
                "system": SUMMARY_SYSTEM,
                "user": SUMMARY_USER
            }
        }
    }
