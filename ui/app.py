#!/usr/bin/env python3
"""
Deeppersona UI - Step-by-step persona generation interface with prompt editing.

Run with: streamlit run ui/app.py
"""

import streamlit as st
import json
import os
import sys
from datetime import datetime

# Add project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'generate_user_profile'))
sys.path.insert(0, os.path.dirname(__file__))

# Import generation functions
from select_attributes import generate_user_profile, get_selected_attributes, save_results
from generate_profile import generate_single_profile
from prompts import get_all_prompts

# Page config
st.set_page_config(
    page_title="Deeppersona - Profile Generator",
    page_icon="👤",
    layout="wide"
)

# Initialize session state
if 'base_profile' not in st.session_state:
    st.session_state.base_profile = None
if 'selected_attributes' not in st.session_state:
    st.session_state.selected_attributes = None
if 'complete_profile' not in st.session_state:
    st.session_state.complete_profile = None
if 'prompts' not in st.session_state:
    st.session_state.prompts = get_all_prompts()


def reset_all():
    """Reset all session state."""
    st.session_state.base_profile = None
    st.session_state.selected_attributes = None
    st.session_state.complete_profile = None


def format_profile_summary(profile: dict) -> str:
    """Format base profile for display."""
    if not profile:
        return "No profile generated"

    lines = []
    age_info = profile.get("age_info", {})
    lines.append(f"**Age:** {age_info.get('age', 'N/A')} ({age_info.get('age_group', 'N/A')})")
    lines.append(f"**Gender:** {profile.get('gender', 'N/A')}")
    location = profile.get("location", {})
    lines.append(f"**Location:** {location.get('city', 'N/A')}, {location.get('country', 'N/A')}")
    career = profile.get("career_info", {})
    lines.append(f"**Career:** {career.get('status', 'N/A')}")
    values = profile.get("personal_values", {})
    lines.append(f"**Values:** {values.get('values_orientation', 'N/A')}")
    attitude = profile.get("life_attitude", {})
    if isinstance(attitude, dict):
        lines.append(f"**Attitude:** {attitude.get('attitude', 'N/A')}")
        lines.append(f"**Coping:** {attitude.get('coping_mechanism', 'N/A')}")
    interests = profile.get("interests", {})
    if isinstance(interests, dict):
        interest_list = interests.get("interests", [])
        if interest_list:
            lines.append(f"**Interests:** {', '.join(interest_list)}")
    return "\n\n".join(lines)


def format_attributes_summary(attributes: list) -> dict:
    """Group attributes by category."""
    if not attributes:
        return {}
    categories = {}
    for attr in attributes:
        category = attr.split('.')[0] if '.' in attr else attr
        if category not in categories:
            categories[category] = []
        categories[category].append(attr)
    return categories


# Header
st.title("👤 Deeppersona - Profile Generator")
st.markdown("Generate realistic synthetic user profiles step by step with full prompt visibility.")

# Sidebar
with st.sidebar:
    st.header("Controls")

    attribute_count = st.slider(
        "Attribute Count",
        min_value=50,
        max_value=350,
        value=150,
        step=50,
        help="Number of attributes to select in Step 2"
    )

    st.divider()

    # Progress indicator
    st.subheader("Progress")
    step1_status = "✅" if st.session_state.base_profile else "⏳"
    step2_status = "✅" if st.session_state.selected_attributes else "⏳"
    step3_status = "✅" if st.session_state.complete_profile else "⏳"
    st.markdown(f"{step1_status} Step 1: Base Profile")
    st.markdown(f"{step2_status} Step 2: Select Attributes")
    st.markdown(f"{step3_status} Step 3: Complete Persona")

    st.divider()

    if st.button("🔄 Reset All", use_container_width=True):
        reset_all()
        st.rerun()

    st.divider()

    # Download section
    st.subheader("Download")
    if st.session_state.complete_profile:
        complete_json = json.dumps(st.session_state.complete_profile, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Complete Profile",
            data=complete_json,
            file_name=f"complete_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    if st.session_state.base_profile:
        base_json = json.dumps(st.session_state.base_profile, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Base Profile",
            data=base_json,
            file_name=f"base_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

# Main content - Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Step 1: Base Profile",
    "🎯 Step 2: Attributes",
    "👤 Step 3: Persona",
    "📝 Prompts",
    "📊 Full View"
])

# ============== STEP 1: Base Profile ==============
with tab1:
    st.header("Step 1: Generate Base Profile")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("""
        **Generates:**
        - Demographics (age, gender, location)
        - Career information
        - Personal values
        - Life attitude
        - Personal story (1-3 narratives)
        - Interests/hobbies

        **API Calls:** ~5 GPT calls
        """)

        if st.button("🎲 Generate Base Profile", use_container_width=True, type="primary"):
            with st.spinner("Generating base profile..."):
                try:
                    st.session_state.base_profile = generate_user_profile()
                    st.session_state.selected_attributes = None
                    st.session_state.complete_profile = None
                    st.success("Base profile generated!")
                except Exception as e:
                    st.error(f"Error: {e}")

    with col2:
        if st.session_state.base_profile:
            st.markdown("### Profile Summary")
            st.markdown(format_profile_summary(st.session_state.base_profile))

    if st.session_state.base_profile:
        story = st.session_state.base_profile.get("personal_story", {})
        if isinstance(story, dict) and story.get("personal_story"):
            with st.expander("📖 Personal Story", expanded=False):
                st.markdown(story.get("personal_story", ""))
        with st.expander("🔍 Raw JSON", expanded=False):
            st.json(st.session_state.base_profile)

# ============== STEP 2: Attributes ==============
with tab2:
    st.header("Step 2: Select Attributes")

    if not st.session_state.base_profile:
        st.warning("⚠️ Please generate a base profile first (Step 1)")
    else:
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown(f"""
            **Process:**
            - Create profile embedding
            - Vector similarity search
            - 5:3:2 ratio selection
            - Select **{attribute_count}** attributes

            **API Calls:** 1 embedding + 1 GPT
            """)

            if st.button(f"🎯 Select {attribute_count} Attributes", use_container_width=True, type="primary"):
                with st.spinner("Selecting attributes..."):
                    try:
                        st.session_state.selected_attributes = get_selected_attributes(
                            st.session_state.base_profile,
                            attribute_count=attribute_count
                        )
                        st.session_state.complete_profile = None
                        st.success(f"Selected {len(st.session_state.selected_attributes)} attributes!")
                    except Exception as e:
                        st.error(f"Error: {e}")

        with col2:
            if st.session_state.selected_attributes:
                st.metric("Total Attributes", len(st.session_state.selected_attributes))

        if st.session_state.selected_attributes:
            categories = format_attributes_summary(st.session_state.selected_attributes)
            st.markdown("### Attributes by Category")
            cols = st.columns(3)
            for i, (category, attrs) in enumerate(sorted(categories.items())):
                with cols[i % 3]:
                    with st.expander(f"**{category}** ({len(attrs)})", expanded=False):
                        for attr in attrs:
                            sub_path = '.'.join(attr.split('.')[1:]) if '.' in attr else attr
                            st.markdown(f"- {sub_path}")

# ============== STEP 3: Complete Persona ==============
with tab3:
    st.header("Step 3: Generate Complete Persona")

    if not st.session_state.base_profile:
        st.warning("⚠️ Please generate a base profile first (Step 1)")
    elif not st.session_state.selected_attributes:
        st.warning("⚠️ Please select attributes first (Step 2)")
    else:
        st.markdown("""
        **Generates sections:**
        Demographic Info • Career • Core Values • Lifestyle • Cultural Context • Hobbies • Other • Summary

        **API Calls:** ~8 GPT calls (1-2 minutes)
        """)

        if st.button("👤 Generate Complete Persona", use_container_width=True, type="primary"):
            with st.spinner("Generating complete persona..."):
                try:
                    st.session_state.complete_profile = generate_single_profile(
                        template=None,
                        profile_index=0,
                        attribute_count=attribute_count,
                        base_profile=st.session_state.base_profile,
                        selected_attributes=st.session_state.selected_attributes
                    )
                    st.success("Complete persona generated!")
                except Exception as e:
                    st.error(f"Error: {e}")

        if st.session_state.complete_profile:
            if "Summary" in st.session_state.complete_profile:
                st.markdown("### 📝 Narrative Summary")
                st.markdown(st.session_state.complete_profile["Summary"])
                st.divider()

            st.markdown("### Profile Sections")
            sections = [
                "Demographic Information", "Career and Work Identity",
                "Core Values, Beliefs, and Philosophy", "Lifestyle and Daily Routine",
                "Cultural and Social Context", "Hobbies, Interests, and Lifestyle",
                "Other Attributes"
            ]
            for section in sections:
                if section in st.session_state.complete_profile:
                    section_data = st.session_state.complete_profile[section]
                    if section_data:
                        with st.expander(f"**{section}**", expanded=False):
                            st.json(section_data)

# ============== PROMPTS TAB ==============
with tab4:
    st.header("📝 System & User Prompts")
    st.markdown("View the prompts used at each generation step.")

    # View-only mode
    edit_mode = False

    prompt_tab1, prompt_tab2, prompt_tab3 = st.tabs([
        "Step 1: Base Profile",
        "Step 2: Attributes",
        "Step 3: Sections"
    ])

    def prompt_display(key_path: str, label: str):
        """Display prompt as code block (view-only)."""
        # Navigate to the prompt value
        keys = key_path.split(".")
        value = st.session_state.prompts
        for k in keys:
            value = value[k]
        st.markdown(f"**{label}:**")
        st.code(value, language=None)

    # Step 1 Prompts
    with prompt_tab1:
        st.subheader("Base Profile Generation Prompts")

        # Career Info
        with st.expander("🏢 Career Info", expanded=False):
            prompt_display("step1_base_profile.career_info.system", "System Prompt")
            prompt_display("step1_base_profile.career_info.user", "User Prompt Template")
            prompt_display("step1_base_profile.career_info.young_context", "Context - Young (< 18)")
            prompt_display("step1_base_profile.career_info.senior_context", "Context - Senior (> 65)")

        # Personal Values
        with st.expander("💎 Personal Values", expanded=False):
            prompt_display("step1_base_profile.personal_values.system", "System Prompt")
            prompt_display("step1_base_profile.personal_values.user", "User Prompt Template")

        # Life Attitude
        with st.expander("🧠 Life Attitude", expanded=False):
            prompt_display("step1_base_profile.life_attitude.system", "System Prompt")
            prompt_display("step1_base_profile.life_attitude.user", "User Prompt Template")

        # Personal Story
        with st.expander("📖 Personal Story", expanded=False):
            prompt_display("step1_base_profile.personal_story.system", "System Prompt")
            prompt_display("step1_base_profile.personal_story.user", "User Prompt Template")

        # Interests
        with st.expander("🎯 Interests & Hobbies", expanded=False):
            prompt_display("step1_base_profile.interests.system", "System Prompt")
            prompt_display("step1_base_profile.interests.user", "User Prompt Template")

    # Step 2 Prompts
    with prompt_tab2:
        st.subheader("Attribute Selection Prompts")

        with st.expander("🎯 Career Attributes Needed Check", expanded=True):
            prompt_display("step2_attributes.career_needed.system", "System Prompt")
            prompt_display("step2_attributes.career_needed.user", "User Prompt Template")

    # Step 3 Prompts
    with prompt_tab3:
        st.subheader("Section Generation Prompts")

        # Common system prompt
        with st.expander("⚙️ Common System Prompt (All Sections)", expanded=False):
            prompt_display("step3_sections.section_generation.system", "System Prompt")

        # Demographic
        with st.expander("👤 Demographic Information", expanded=False):
            prompt_display("step3_sections.demographic.user", "User Prompt Template")

        # Career
        with st.expander("💼 Career and Work Identity", expanded=False):
            prompt_display("step3_sections.career.user", "User Prompt Template")

        # Core Values
        with st.expander("💡 Core Values, Beliefs, Philosophy", expanded=False):
            prompt_display("step3_sections.core_values.user", "User Prompt Template")

        # Lifestyle
        with st.expander("🏠 Lifestyle and Daily Routine", expanded=False):
            prompt_display("step3_sections.lifestyle.user", "User Prompt Template")

        # Cultural
        with st.expander("🌍 Cultural and Social Context", expanded=False):
            prompt_display("step3_sections.cultural.user", "User Prompt Template")

        # Hobbies
        with st.expander("🎨 Hobbies, Interests, Lifestyle", expanded=False):
            prompt_display("step3_sections.hobbies.user", "User Prompt Template")

        # Other Attributes
        with st.expander("📋 Other Attributes", expanded=False):
            prompt_display("step3_sections.other_attributes.user", "User Prompt Template")

        # Summary
        with st.expander("📝 Final Summary", expanded=False):
            prompt_display("step3_sections.summary.system", "System Prompt")
            prompt_display("step3_sections.summary.user", "User Prompt Template")

# ============== FULL VIEW ==============
with tab5:
    st.header("Full Profile View")

    if not st.session_state.complete_profile:
        st.info("Complete all 3 steps to see the full profile here.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Base Profile")
            st.markdown(format_profile_summary(st.session_state.base_profile))

            st.subheader("Attributes")
            categories = format_attributes_summary(st.session_state.selected_attributes)
            for category, attrs in sorted(categories.items()):
                st.markdown(f"**{category}:** {len(attrs)} attributes")

        with col2:
            st.subheader("Generated Persona")
            if "Summary" in st.session_state.complete_profile:
                st.markdown(st.session_state.complete_profile["Summary"])

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: gray; font-size: 12px;">
    Deeppersona - Synthetic User Profile Generator
</div>
""", unsafe_allow_html=True)
