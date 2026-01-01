# Deeppersona vs functions-python Step 2 Comparison Report

## Executive Summary

**Deeppersona** creates significantly richer, more psychologically-grounded personas through a multi-stage generation process that starts with a "base profile" containing personal values, life stories, and attitudes BEFORE selecting attributes. **functions-python** uses a simpler, more direct approach focused on role-based persona generation for interview validation.

---

## 1. Architecture Comparison

### functions-python (Current Approach)
```
Phase 1: Profile Generation (role titles only)
    ↓
Phase 2: User Selection + Target Count
    ↓
Phase 3: Attribute Generation (LLM decides attributes)
    ↓
Phase 4: Persona Generation (fill attribute values)
```

### Deeppersona (Enhanced Approach)
```
Stage 1: Base Profile Generation (rich psychological foundation)
    ↓
Stage 2: Vector-Based Attribute Selection (semantic search)
    ↓
Stage 3: Complete Persona Generation (7 sections with LLM)
    ↓
Stage 4: First-Person Summary Generation
```

---

## 2. Profile Generation Comparison

| Aspect | functions-python | Deeppersona |
|--------|------------------|-------------|
| **Output** | Role titles only (e.g., "Product Manager") | Rich base profile with 8 attributes |
| **LLM Calls** | 1 call | 5-6 calls |
| **Data Generated** | Just name/title | Age, gender, location, career, values, attitude, personal story, interests |
| **Personalization** | None at this stage | Deep psychological foundation established |

### functions-python Profile Generation
```json
{
  "1": "Product Manager",
  "2": "Software Engineer",
  "3": "Security Engineer"
}
```
**Prompt focus**: Generate 5-10 job titles based on idea description.

### Deeppersona Base Profile Generation
```json
{
  "age_info": {"age": 32, "age_group": "adult"},
  "gender": "male",
  "location": {"country": "India", "city": "Bangalore"},
  "career_info": {"status": "Senior Software Engineer"},
  "personal_values": {"values_orientation": "Pragmatic, values efficiency over formality"},
  "life_attitude": {
    "attitude": "Cautiously optimistic",
    "attitude_details": "Believes in incremental progress...",
    "coping_mechanism": "Uses humor and distraction"
  },
  "personal_story": {"personal_story": "Story 1: ... Story 2: ..."},
  "interests": {"interests": ["reading technical blogs", "hiking"]}
}
```

**Key Difference**: Deeppersona generates **1-3 personal stories** (150-200 words each) that become the foundation for ALL subsequent attribute generation. This creates narrative coherence.

---

## 3. Attribute Generation Comparison

| Aspect | functions-python | Deeppersona |
|--------|------------------|-------------|
| **Attribute Source** | LLM generates 6-10 attribute names | 2,297 pre-defined attributes in database |
| **Selection Method** | LLM decides what's relevant | Vector similarity (embeddings) + semantic search |
| **Attribute Count** | ~10 total (3-4 primary + 6 secondary) | 100-350 attributes selected |
| **Diversity Control** | None | Near/Mid/Far neighbor algorithm (50:30:20 ratio) |
| **LLM Calls** | 1 call per profile | 1 embedding call + optional career check |

### functions-python Attribute Generation
**Prompt** (`03-generate-attributes.md`):
```
Return attribute NAMES (no values):
- Primary (3-4): name, age, hobbies, location, industry, company_size
- Secondary (6): 3 role-specific + 3 idea-specific attributes
```

**Output**:
```json
{
  "primary": ["name", "age", "hobbies", "location"],
  "secondary": ["years_of_experience", "management_style", "tech_stack_preference",
                "decision_making_speed", "risk_tolerance", "team_size_managed"]
}
```

### Deeppersona Attribute Selection
**Process**:
1. Convert base profile to embedding vector (1536 dims)
2. Compute cosine similarity against 2,297 pre-computed attribute embeddings
3. Select using "interesting neighbors" algorithm:
   - **50%** from nearest neighbors (high relevance)
   - **30%** from mid-distance (moderate relevance)
   - **20%** from far neighbors (diversity injection)

**Output**: 150-350 hierarchical attribute paths like:
```
"Career and Work Identity.Business.Career Stage"
"Core Values, Beliefs, and Philosophy.PersonalGrowth.Orientation"
"Hobbies, Interests, and Lifestyle.Entertainment.Gaming"
```

**Key Difference**: Deeppersona's vector-based selection ensures:
1. **Relevance**: Attributes semantically match the profile
2. **Diversity**: Far neighbors prevent echo-chamber attributes
3. **Consistency**: All attributes trace back to a coherent base profile

---

## 4. Persona Generation Comparison

| Aspect | functions-python | Deeppersona |
|--------|------------------|-------------|
| **LLM Calls** | 1 call (generates all personas) | 7-8 calls (one per category) |
| **Attribute Filling** | All at once in single prompt | Section by section with context accumulation |
| **Context Passed** | Profile name + attribute list | Base profile + all previously generated sections |
| **Output** | Flat persona object | Nested hierarchical structure |
| **Summary** | No summary generated | 150-400 word first-person narrative |

### functions-python Persona Generation
**Single LLM call** generates all personas:
```json
{
  "personas": [
    {
      "name": "Alice Chen",
      "age": 32,
      "role": "Product Manager",
      "company": "Acme Corp",
      "location": "San Francisco, USA",
      "pain_points": "Managing cross-functional teams"
    }
  ]
}
```

### Deeppersona Persona Generation (7 Stages)

Each stage builds on previous, creating coherent depth:

| Stage | Section | Input Context | LLM Call |
|-------|---------|---------------|----------|
| 1 | Demographic Information | Base info + life story | Yes |
| 2 | Career and Work Identity | Above + Demographics | Yes |
| 3 | Core Values, Beliefs, Philosophy | Above + Career | Yes |
| 4 | Lifestyle and Daily Routine | Above + Values | Yes |
| 5 | Cultural and Social Context | Above + Lifestyle | Yes |
| 6 | Hobbies, Interests, Lifestyle | Above + Cultural | Yes |
| 7 | Other Attributes | Above + Complete profile | Yes |
| 8 | Final Summary | Complete profile | Yes |

**Final Output Structure**:
```json
{
  "Base Info": { /* original base profile */ },
  "Demographic Information": {
    "Education": {"Learner": "Graduate degree in Computer Science"},
    "Age": {"Range": "30-35"}
  },
  "Career and Work Identity": { /* 5-10 nested attributes */ },
  "Core Values, Beliefs, and Philosophy": { /* values */ },
  "Lifestyle and Daily Routine": { /* routines */ },
  "Cultural and Social Context": { /* cultural identity */ },
  "Hobbies, Interests, and Lifestyle": { /* interests */ },
  "Summary": "I am from Bangalore, India... [150-400 word first-person narrative]"
}
```

---

## 5. LLM Calls Comparison

### functions-python: Total ~3 LLM calls per persona

| Step | Calls | Purpose |
|------|-------|---------|
| Profile Generation | 1 | Generate role titles |
| Attribute Generation | 1 | Generate attribute names |
| Persona Generation | 1 | Fill all attribute values |
| **Total** | **~3** | |

### Deeppersona: Total ~13-14 LLM calls per persona

| Step | Calls | Purpose |
|------|-------|---------|
| Career Info | 1 | Age-appropriate occupation (if age <18 or >65) |
| Personal Values | 1 | Value orientation (positive/negative/neutral) |
| Life Attitude | 1 | Attitude, details, coping mechanism |
| Personal Story | 1 | 1-3 stories (150-200 words each) |
| Interests | 1 | Infer 2-3 hobbies from story |
| Profile Embedding | 1 | Convert profile to vector |
| Career Check | 1 | Determine if career attributes needed |
| Demographic Section | 1 | Fill demographic attributes |
| Career Section | 1 | Fill career attributes |
| Values Section | 1 | Fill values attributes |
| Lifestyle Section | 1 | Fill lifestyle attributes |
| Cultural Section | 1 | Fill cultural attributes |
| Hobbies Section | 1 | Fill hobby attributes |
| Final Summary | 1 | Generate first-person narrative |
| **Total** | **~13-14** | |

---

## 6. Key Differentiators

### What Deeppersona Does Better

1. **Narrative Foundation**: Personal stories (150-200 words) create psychological coherence
2. **Value Systems**: Explicitly generates positive/negative/neutral value orientations
3. **Semantic Attribute Selection**: 2,297 pre-computed embeddings ensure relevant attributes
4. **Diversity Injection**: Near/Mid/Far neighbor algorithm prevents homogeneous personas
5. **Contextual Building**: Each section builds on previous, creating coherent depth
6. **First-Person Summary**: 150-400 word narrative that "voices" the persona

### What functions-python Does Better

1. **Speed**: ~3 LLM calls vs ~14 calls
2. **Cost**: Significantly cheaper per persona
3. **Idea-Specificity**: Attributes are generated specific to the product idea
4. **Role Focus**: Optimized for interview validation use case
5. **Simplicity**: Easier to maintain and debug

---

## 7. Recommendations: What to Bring from Deeppersona

### High-Impact, Low-Effort Changes

1. **Add Personal Story Generation** (1 extra LLM call)
   ```python
   # Before generating personas, generate a brief story for context
   def generate_persona_backstory(profile_name, attributes):
       prompt = f"Generate a 100-word personal story for a {profile_name}..."
       # This story informs all attribute values
   ```

2. **Add Value Orientation** (modify existing call)
   - Add `values_orientation` (positive/negative/neutral) to persona attributes
   - This creates more diverse persona behaviors

3. **Add First-Person Summary** (1 extra LLM call)
   - After persona generation, create a 100-150 word first-person narrative
   - This helps during interview roleplay

### Medium-Impact Changes

4. **Pre-defined Attribute Database**
   - Create a curated list of ~100-200 common persona attributes
   - Select from this list based on profile type rather than generating new ones
   - More consistent attribute quality

5. **Sectioned Generation** (more LLM calls)
   - Instead of one big persona generation call, break into 2-3 sections:
     - Demographics + Career
     - Values + Lifestyle
     - Pain points + Behaviors
   - Each section gets context from previous

### Architectural Changes (Higher Effort)

6. **Vector-Based Attribute Selection**
   - Pre-compute embeddings for ~200 common attributes
   - Select attributes based on profile + idea similarity
   - Ensures semantic relevance

7. **Base Profile First**
   - Generate age, location, values, attitude BEFORE attribute selection
   - Use this base profile to inform attribute and persona generation

---

## 8. Implementation Priority

| Priority | Change | Effort | Impact |
|----------|--------|--------|--------|
| 1 | Add value orientation to persona | Low | High |
| 2 | Add brief personal story (50-100 words) | Low | High |
| 3 | Add first-person summary at end | Low | Medium |
| 4 | Create pre-defined attribute database | Medium | High |
| 5 | Section-based generation | Medium | Medium |
| 6 | Vector-based attribute selection | High | High |
| 7 | Full base profile generation first | High | Very High |

---

## 9. Quick Win: Enhanced Persona Prompt

Here's a modified prompt that incorporates Deeppersona concepts without architectural changes:

```markdown
You are a persona-generation agent inside a synthetic user engine.

## Enhanced Instructions

1. **First, generate a brief backstory** (2-3 sentences) that explains this person's
   journey to their current role. Include a formative experience.

2. **Assign a value orientation**: Randomly choose positive, neutral, or negative
   outlook on the product category being tested.

3. **Generate the persona** with all requested attributes.

4. **End with a first-person summary** (50-75 words) in the persona's voice.

## Output Format
{
  "personas": [
    {
      "backstory": "Brief 2-3 sentence background...",
      "value_orientation": "positive|neutral|negative",
      "name": "Full Name",
      "age": 32,
      ... other attributes ...,
      "first_person_summary": "Hi, I'm [name]. I've been..."
    }
  ]
}
```

This single prompt change brings ~60% of Deeppersona's benefits with minimal code changes.

---

## 10. Detailed Prompt Comparison

### Profile Generation Prompts

#### functions-python (`02-generate-profiles-system.md`)
- **Focus**: Generate role titles for interview validation
- **Output**: 5-10 job titles or consumer roles
- **B2B/B2C awareness**: Yes, classifies and applies different rules
- **Stakeholder diversity**: End user, buyer, adjacent roles

#### Deeppersona (`based_data.py`)
- **Focus**: Generate rich psychological foundation
- **Output**: Age, gender, location, career, values, attitude, story, interests
- **Value types**: Explicitly randomizes positive/negative/neutral
- **Story generation**: 1-3 personal narratives (150-200 words each)

### Attribute Generation Prompts

#### functions-python (`03-generate-attributes.md`)
- **Focus**: Generate attribute names relevant to role + idea
- **Anti-bias rules**: Avoids problem-leading and solution-leading words
- **Output**: 3-4 primary + 6 secondary attribute names
- **Dynamic**: LLM decides attributes each time

#### Deeppersona (`select_attributes.py`)
- **Focus**: Select from pre-defined attribute database
- **Method**: Vector similarity with cosine distance
- **Output**: 100-350 attribute paths
- **Diversity**: Near/Mid/Far neighbor algorithm

### Persona Generation Prompts

#### functions-python (`05-generate-personas.md`)
- **Focus**: Fill attribute values for interview personas
- **Diversity instruction**: Make personas distinct from each other
- **Output**: Flat JSON with all attributes

#### Deeppersona (`generate_profile.py`)
- **Focus**: Build coherent multi-dimensional profile
- **Method**: 7 sequential sections, each building on previous
- **Summary**: First-person 150-400 word narrative
- **Constraints**: Prohibits certain words ("balance"), enforces word limits

---

## Summary

**Deeppersona** produces deeper, more psychologically-grounded personas through narrative foundation and semantic attribute selection. **functions-python** is faster and more cost-effective but produces shallower personas.

**Recommended path**: Start with quick wins (value orientation, backstory, summary) that require minimal changes, then gradually adopt pre-defined attributes and sectioned generation as needs grow.

---

*Report generated: December 2024*
*Comparing: functions-python/step2 vs Deeppersona*
