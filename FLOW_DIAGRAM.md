# Deeppersona - System Architecture & Flow Diagram

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DEEPPERSONA SYSTEM                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌─────────────────────┐         ┌─────────────────────┐                       │
│   │  PROFILE GENERATION │         │ ATTRIBUTE PROCESSING│                       │
│   │     (Main Flow)     │         │    (Data Pipeline)  │                       │
│   └──────────┬──────────┘         └──────────┬──────────┘                       │
│              │                               │                                   │
│              ▼                               ▼                                   │
│   ┌─────────────────────┐         ┌─────────────────────┐                       │
│   │ generate_profiles.py│         │  process_attributes/│                       │
│   │ generate_profile.py │         │  (standalone tools) │                       │
│   │ select_attributes.py│         └─────────────────────┘                       │
│   │ based_data.py       │                                                        │
│   │ config.py           │                                                        │
│   └─────────────────────┘                                                        │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Main Profile Generation Flow

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                        generate_profiles.py                                       │
│                        ════════════════════                                       │
│                                                                                   │
│   run_complete_flow(attribute_count=150)                                         │
│         │                                                                         │
│         ├─────────────────────────────────────────────────────────────────────┐  │
│         │                                                                      │  │
│         ▼                                                                      │  │
│   ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│   │ STEP 1: Generate Base Profile                                            │ │  │
│   │ ─────────────────────────────────                                        │ │  │
│   │                                                                          │ │  │
│   │   generate_user_profile()  ──► select_attributes.py                      │ │  │
│   │         │                                                                │ │  │
│   │         ├──► generate_age_info()      ──► based_data.py                  │ │  │
│   │         ├──► generate_gender()        ──► based_data.py                  │ │  │
│   │         ├──► generate_location()      ──► based_data.py (India cities)   │ │  │
│   │         ├──► generate_career_info()   ──► based_data.py + GPT            │ │  │
│   │         ├──► generate_personal_values() ──► based_data.py + GPT          │ │  │
│   │         ├──► generate_life_attitude()   ──► based_data.py + GPT          │ │  │
│   │         ├──► generate_personal_story()  ──► based_data.py + GPT          │ │  │
│   │         └──► generate_interests_and_hobbies() ──► based_data.py + GPT    │ │  │
│   │                                                                          │ │  │
│   │   OUTPUT: base_profile dict                                              │ │  │
│   │   {age_info, gender, location, career_info, personal_values,             │ │  │
│   │    life_attitude, personal_story, interests}                             │ │  │
│   └─────────────────────────────────────────────────────────────────────────┘ │  │
│         │                                                                      │  │
│         ▼                                                                      │  │
│   ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│   │ STEP 2: Select Attributes                                                │ │  │
│   │ ─────────────────────────                                                │ │  │
│   │                                                                          │ │  │
│   │   get_selected_attributes(base_profile, 150)  ──► select_attributes.py   │ │  │
│   │         │                                                                │ │  │
│   │         ├──► _create_profile_embedding()                                 │ │  │
│   │         │         └──► OpenAI text-embedding-ada-002                     │ │  │
│   │         │                                                                │ │  │
│   │         ├──► Load attribute_embeddings.pkl                               │ │  │
│   │         │         └──► 2,297 pre-computed embeddings                     │ │  │
│   │         │                                                                │ │  │
│   │         ├──► _find_interesting_neighbors()                               │ │  │
│   │         │         ├──► Compute cosine similarity                         │ │  │
│   │         │         └──► Apply 5:3:2 ratio (near/mid/far)                  │ │  │
│   │         │                                                                │ │  │
│   │         └──► analyze_profile_for_attributes()                            │ │  │
│   │                   └──► GPT decides if career attributes needed           │ │  │
│   │                                                                          │ │  │
│   │   OUTPUT: selected_attributes list (150 X.Y.Z paths)                     │ │  │
│   └─────────────────────────────────────────────────────────────────────────┘ │  │
│         │                                                                      │  │
│         ▼                                                                      │  │
│   ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│   │ STEP 3: Generate Complete Persona                                        │ │  │
│   │ ─────────────────────────────────                                        │ │  │
│   │                                                                          │ │  │
│   │   generate_single_profile(base_profile, selected_attributes)             │ │  │
│   │         │                        ──► generate_profile.py                 │ │  │
│   │         │                                                                │ │  │
│   │         ├──► build_nested_dict(selected_attributes)                      │ │  │
│   │         │         └──► Convert paths to nested dict structure            │ │  │
│   │         │                                                                │ │  │
│   │         ├──► Generate each section via GPT:                              │ │  │
│   │         │    ┌────────────────────────────────────────────────────────┐  │ │  │
│   │         │    │  generate_category_attributes(template, prompt, name)  │  │ │  │
│   │         │    │                                                        │  │ │  │
│   │         │    │  Sections generated:                                   │  │ │  │
│   │         │    │  1. Demographic Information                            │  │ │  │
│   │         │    │  2. Career and Work Identity                           │  │ │  │
│   │         │    │  3. Core Values, Beliefs, and Philosophy               │  │ │  │
│   │         │    │  4. Lifestyle and Daily Routine                        │  │ │  │
│   │         │    │  5. Cultural and Social Context                        │  │ │  │
│   │         │    │  6. Hobbies, Interests, and Lifestyle                  │  │ │  │
│   │         │    │  7. Other Attributes                                   │  │ │  │
│   │         │    └────────────────────────────────────────────────────────┘  │ │  │
│   │         │                                                                │ │  │
│   │         └──► generate_final_summary(profile, base_info)                  │ │  │
│   │                   └──► GPT generates 100-400 word first-person narrative │ │  │
│   │                                                                          │ │  │
│   │   OUTPUT: complete_profile dict with all sections + Summary              │ │  │
│   └─────────────────────────────────────────────────────────────────────────┘ │  │
│         │                                                                      │  │
│         ▼                                                                      │  │
│   ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│   │ STEP 4: Save Results                                                     │ │  │
│   │ ────────────────────                                                     │ │  │
│   │                                                                          │ │  │
│   │   save_test_results(base_profile, attributes, complete_profile)          │ │  │
│   │         │                                                                │ │  │
│   │         ├──► test_base_profile_{timestamp}.json                          │ │  │
│   │         ├──► test_attributes_{timestamp}.json                            │ │  │
│   │         └──► test_complete_profile_{timestamp}.json                      │ │  │
│   │                                                                          │ │  │
│   │   OUTPUT: 3 JSON files in output/test_runs/                              │ │  │
│   └─────────────────────────────────────────────────────────────────────────┘ │  │
│                                                                               │  │
└───────────────────────────────────────────────────────────────────────────────┘  │
```

---

## 2. Function Call Hierarchy

```
generate_profiles.py
│
└── run_complete_flow(attribute_count)
    │
    ├── [STEP 1] select_attributes.generate_user_profile()
    │   │
    │   └── based_data.py functions:
    │       ├── generate_age_info()           → Random age 7-85, determine age_group
    │       ├── generate_gender()             → Random male/female
    │       ├── generate_location()           → Random Indian city (GeoNames)
    │       ├── get_occupations()             → Load occupations_english.json
    │       ├── generate_career_info(age)     → GPT or random occupation
    │       │   └── config.get_completion()   → OpenAI API call
    │       ├── generate_personal_values(...) → GPT generates values
    │       │   └── config.get_completion()   → OpenAI API call
    │       ├── generate_life_attitude(...)   → GPT generates attitude
    │       │   └── config.get_completion()   → OpenAI API call
    │       ├── generate_personal_story(...)  → GPT generates 1-3 stories
    │       │   └── config.get_completion()   → OpenAI API call
    │       └── generate_interests_and_hobbies(...) → GPT infers interests
    │           └── config.get_completion()   → OpenAI API call
    │
    ├── [STEP 2] select_attributes.get_selected_attributes(profile, count)
    │   │
    │   └── AttributeSelector class methods:
    │       ├── _load_json()                  → Load large_attributes.json
    │       ├── _load_embeddings()            → Load attribute_embeddings.pkl
    │       ├── _extract_profile_summary()    → Create text summary of profile
    │       ├── _create_profile_embedding()   → OpenAI embedding API
    │       ├── _compute_cosine_similarity()  → sklearn cosine_similarity
    │       ├── _find_interesting_neighbors() → 5:3:2 ratio selection
    │       ├── analyze_profile_for_attributes() → GPT decides categories
    │       │   └── config.get_completion()   → OpenAI API call
    │       └── get_top_attributes()          → Final attribute selection
    │
    ├── [STEP 3] generate_profile.generate_single_profile(base_profile, attributes)
    │   │
    │   ├── build_nested_dict()               → Convert paths to nested dict
    │   │
    │   ├── For each section:
    │   │   └── generate_category_attributes(template, prompt, name)
    │   │       └── config.get_completion()   → OpenAI API call
    │   │
    │   └── generate_final_summary(profile, base_info)
    │       └── config.get_completion()       → OpenAI API call
    │
    └── [STEP 4] save_test_results(base, attrs, complete, output_dir)
        ├── json.dump() → test_base_profile_{ts}.json
        ├── json.dump() → test_attributes_{ts}.json
        └── json.dump() → test_complete_profile_{ts}.json
```

---

## 3. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                           │
└─────────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │   INPUT DATA    │
                              └────────┬────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         │                             │                             │
         ▼                             ▼                             ▼
┌─────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│ large_attributes│      │attribute_embeddings │      │occupations_english  │
│     .json       │      │       .pkl          │      │      .json          │
│                 │      │                     │      │                     │
│ 2,297 attribute │      │ 2,297 vectors       │      │ ~1,000 occupations  │
│ paths in nested │      │ (1536 dimensions)   │      │ for random selection│
│ dict format     │      │                     │      │                     │
└────────┬────────┘      └──────────┬──────────┘      └──────────┬──────────┘
         │                          │                            │
         │                          │                            │
         └──────────────────────────┼────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │     PROFILE GENERATION        │
                    │                               │
                    │  1. Random demographics       │
                    │  2. GPT-generated content     │
                    │  3. Vector similarity search  │
                    │  4. GPT section generation    │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │        OUTPUT DATA            │
                    └───────────────┬───────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
         ▼                          ▼                          ▼
┌─────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│ test_base_      │      │ test_attributes_    │      │ test_complete_      │
│ profile_{ts}    │      │ {ts}.json           │      │ profile_{ts}.json   │
│ .json           │      │                     │      │                     │
│                 │      │ Selected 150        │      │ Full persona with   │
│ Demographics,   │      │ attribute paths     │      │ all sections +      │
│ values, story   │      │ grouped by category │      │ narrative summary   │
└─────────────────┘      └─────────────────────┘      └─────────────────────┘
```

---

## 4. API Calls Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           OPENAI API CALLS                                       │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: Base Profile Generation (~5 API calls)                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   generate_career_info()     ──► gpt-4.1-mini  (if age < 18 or > 65)            │
│   generate_personal_values() ──► gpt-4.1-mini  (values orientation)              │
│   generate_life_attitude()   ──► gpt-4.1-mini  (attitude + details + coping)     │
│   generate_personal_story()  ──► gpt-4.1-mini  (1-3 personal narratives)         │
│   generate_interests()       ──► gpt-4.1-mini  (infer 2-3 hobbies)               │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: Attribute Selection (~2 API calls)                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   _create_profile_embedding()        ──► text-embedding-ada-002                  │
│   analyze_profile_for_attributes()   ──► gpt-4.1-mini (career needed?)           │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Complete Profile Generation (~8 API calls)                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   generate_category_attributes() x7  ──► gpt-4.1-mini                            │
│       • Demographic Information                                                  │
│       • Career and Work Identity                                                 │
│       • Core Values, Beliefs, and Philosophy                                     │
│       • Lifestyle and Daily Routine                                              │
│       • Cultural and Social Context                                              │
│       • Hobbies, Interests, and Lifestyle                                        │
│       • Other Attributes                                                         │
│                                                                                  │
│   generate_final_summary()           ──► gpt-4.1-mini (100-400 word narrative)   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

TOTAL: ~15 API calls per profile generation
```

---

## 5. Attribute Processing Pipeline (Standalone)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    ATTRIBUTE PROCESSING PIPELINE                                 │
│                    (Separate from profile generation)                            │
└─────────────────────────────────────────────────────────────────────────────────┘

    This pipeline is used to BUILD the attribute database (large_attributes.json)
    It is NOT called during profile generation.

┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│   [1] extract_personalized_attributes.py                                         │
│       │                                                                          │
│       │   INPUT:  Question + Reason pairs                                        │
│       │   OUTPUT: X.Y.Z attribute paths                                          │
│       │                                                                          │
│       │   PersonalizedAttributeExtractor.extract_attributes()                    │
│       │       └── GPT-4o analyzes questions to extract attributes                │
│       │                                                                          │
│       ▼                                                                          │
│   [2] filter_personalized_attributes.py                                          │
│       │                                                                          │
│       │   INPUT:  Raw X.Y.Z paths                                                │
│       │   OUTPUT: Validated X.Y.Z paths                                          │
│       │                                                                          │
│       │   PersonalizedAttributeAnalyzer methods:                                 │
│       │       ├── check_last_segment()      → GPT validates leaf nodes           │
│       │       ├── check_top_level_category() → GPT corrects categories           │
│       │       └── check_if_personalized()   → GPT ensures user-centric           │
│       │                                                                          │
│       ▼                                                                          │
│   [3] merge_tree.py                                                              │
│       │                                                                          │
│       │   INPUT:  paths_to_merge.json                                            │
│       │   OUTPUT: attributes_merged.json                                         │
│       │                                                                          │
│       │   Functions:                                                             │
│       │       ├── json_to_tree()            → Convert JSON to TreeNode           │
│       │       ├── merge_level_nodes()       → GPT merges similar nodes           │
│       │       ├── validate_parent_attribute() → GPT validates hierarchy          │
│       │       └── tree_to_json()            → Convert back to JSON               │
│       │                                                                          │
│       ▼                                                                          │
│   [4] check_leaves.py                                                            │
│       │                                                                          │
│       │   INPUT:  attributes_merged.json                                         │
│       │   OUTPUT: filtered_attributes.json                                       │
│       │                                                                          │
│       │   PathFilter.filter_tree():                                              │
│       │       ├── Phase 1: Semantic similarity (sentence-transformers)           │
│       │       │       └── Remove paths with >85% similarity                      │
│       │       └── Phase 2: Quality validation (GPT)                              │
│       │               ├── check_attribute_quality()                              │
│       │               └── check_level_compatibility()                            │
│       │                                                                          │
│       ▼                                                                          │
│   [5] convert_to_X.Y.Z.py                                                        │
│       │                                                                          │
│       │   INPUT:  attributes_merged.json                                         │
│       │   OUTPUT: paths_X.Y.Z.json + paths_tree.txt                              │
│       │                                                                          │
│       │   Functions:                                                             │
│       │       ├── extract_paths()           → Flatten to X.Y.Z format            │
│       │       ├── build_parent_child_map()  → Build hierarchy                    │
│       │       └── generate_tree_text()      → Create visual tree                 │
│       │                                                                          │
│       ▼                                                                          │
│   [FINAL] data/large_attributes.json                                             │
│           (Used by profile generation)                                           │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. File Structure

```
Deeppersona/
│
├── generate_user_profile/           # MAIN PROFILE GENERATION
│   ├── config.py                    # OpenAI API config, get_completion()
│   ├── based_data.py                # Demographics & GPT content generation
│   ├── select_attributes.py         # Vector search & attribute selection
│   ├── generate_profile.py          # Complete profile orchestration
│   ├── generate_profiles.py         # Entry point - complete flow test
│   └── output/                      # Generated profiles
│       └── test_runs/
│
├── process_attributes/              # ATTRIBUTE PIPELINE (standalone)
│   ├── extract_personalized_attributes.py
│   ├── filter_personalized_attributes.py
│   ├── merge_tree.py
│   ├── check_leaves.py
│   ├── convert_to_X.Y.Z.py
│   ├── template.json                # Top-level category definitions
│   └── outputs/                     # Pipeline outputs
│
├── data/                            # DATA FILES
│   ├── large_attributes.json        # 2,297 attributes (nested dict)
│   ├── attribute_embeddings.pkl     # Pre-computed embeddings
│   ├── occupations_english.json     # Occupation list
│   ├── attributes_merged.json       # (for attribute pipeline)
│   └── regenerate_embeddings.py     # Utility to rebuild embeddings
│
└── PROJECT_ANALYSIS_REPORT.md       # Detailed documentation
```

---

## 7. Quick Reference - Entry Points

| Task | Command | Description |
|------|---------|-------------|
| Generate single profile | `python generate_profiles.py` | Full 3-step flow |
| Batch generate profiles | `python generate_profile.py` | Multiple rounds |
| Regenerate embeddings | `python data/regenerate_embeddings.py` | Rebuild .pkl file |
| Filter attributes | `python process_attributes/check_leaves.py` | Quality filter |
| Convert to paths | `python process_attributes/convert_to_X.Y.Z.py` | Flatten to paths |

---

*Generated: 2024-12-08*
