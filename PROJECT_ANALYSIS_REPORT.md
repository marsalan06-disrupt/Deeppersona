# Deeppersona Project Analysis Report

## 1. Project Overview

**Deeppersona** is a Python-based system for generating realistic, synthetic user profiles with rich psychological, demographic, and behavioral attributes using GPT language models and vector-based semantic search.

### Purpose
- Generate deep, personalized personas that simulate authentic human characteristics
- Use cases: research, testing, simulation, user persona generation

### Technology Stack
- **Python 3.8+**
- **OpenAI API** (GPT-4.1-mini, text-embedding-ada-002)
- **SentenceTransformers** (all-MiniLM-L6-v2)
- **scikit-learn** (cosine similarity)
- **numpy**, **geonamescache**, **tqdm**

---

## 2. Project Structure

```
Deeppersona/
├── generate_user_profile/     # Main profile generation module
│   ├── config.py              # API configuration & utilities
│   ├── based_data.py          # Core demographic data generation
│   ├── select_attributes.py   # Vector-based attribute selection
│   ├── generate_profile.py    # Profile orchestration
│   └── generate_profiles.py   # Batch processing script
│
├── process_attributes/        # Attribute processing pipeline
│   ├── extract_personalized_attributes.py
│   ├── filter_personalized_attributes.py
│   ├── merge_tree.py
│   ├── check_leaves.py
│   ├── convert_to_X.Y.Z.py
│   └── process_attributes.py
│
└── data/                      # Data files
    ├── attribute_embeddings.pkl
    ├── attributes_merged.json
    ├── large_attributes.json
    └── occupations_english.json
```

---

## 3. Exposed Functions for Consumers

### Primary API (generate_user_profile module)

#### `select_attributes.py`
| Function | Description | Parameters | Returns |
|----------|-------------|------------|---------|
| `generate_user_profile()` | Generate complete base user profile | None | `Dict` with age, gender, location, career, values, attitude, story, interests |
| `get_selected_attributes(user_profile, attribute_count)` | Select relevant attributes using vector search | `user_profile: Dict`, `attribute_count: int = 200` | `List[str]` of attribute paths |
| `save_results(user_profile, selected_paths, output_dir)` | Save profile and attributes to JSON files | `user_profile: Dict`, `selected_paths: List[str]`, `output_dir: str` | None |

#### `generate_profile.py`
| Function | Description | Parameters | Returns |
|----------|-------------|------------|---------|
| `generate_single_profile(template, profile_index, attribute_count)` | Generate one complete profile | `template: Dict = None`, `profile_index: int = 0`, `attribute_count: int = 200` | `Dict` complete profile |
| `generate_multiple_profiles(num_rounds)` | Batch generate profiles | `num_rounds: int = 8` | None (saves to files) |

#### `based_data.py`
| Function | Description | Parameters | Returns |
|----------|-------------|------------|---------|
| `generate_age_info()` | Generate age and age group | None | `Dict` with `age`, `age_group` |
| `generate_gender()` | Random gender selection | None | `str` ("male" or "female") |
| `generate_location()` | Generate Indian city location | None | `Dict` with `country`, `city` |
| `generate_career_info(age)` | Generate occupation based on age | `age: int` | `Dict` with `status` |
| `generate_personal_values(age, gender, occupation, location)` | Generate value system using GPT | All demographics | `Dict` with `values_orientation` |
| `generate_life_attitude(age, gender, occupation, location, values_orientation)` | Generate life attitude | All demographics + values | `Dict` with `attitude`, `attitude_details`, `coping_mechanism` |
| `generate_personal_story(age, gender, occupation, location, values_orientation, life_attitude)` | Generate 1-3 personal narratives | All profile data | `Dict` with `personal_story` |
| `generate_interests_and_hobbies(personal_story)` | Infer hobbies from stories | `personal_story: Dict` | `Dict` with `interests` list |
| `get_occupations()` | Load occupation list from JSON | None | `List[str]` |

#### `config.py`
| Function | Description | Parameters | Returns |
|----------|-------------|------------|---------|
| `get_completion(messages, model, temperature, max_retries)` | Call OpenAI GPT API with retry | `messages: List[Dict]`, `model: str`, `temperature: float`, `max_retries: int` | `Optional[str]` |
| `extract_json_from_markdown(response)` | Extract JSON from markdown | `response: str` | `str` |
| `parse_json_response(response, default_value)` | Parse JSON safely | `response: str`, `default_value: Any` | `Any` |
| `parse_gpt_response(response, expected_fields, field_defaults)` | Parse GPT response with field extraction | `response: str`, fields, defaults | `Dict[str, Any]` |
| `parse_nested_json_response(response)` | Parse nested JSON | `response: str` | `Tuple[Dict, bool]` |

### Secondary API (process_attributes module)

#### `extract_personalized_attributes.py`
| Class/Function | Description |
|----------------|-------------|
| `PersonalizedAttributeExtractor` | Extract attributes from question-reason pairs |
| `extractor.extract_attributes(question, reason)` | Main extraction method |

#### `filter_personalized_attributes.py`
| Class/Function | Description |
|----------------|-------------|
| `PersonalizedAttributeAnalyzer` | Validate and filter attributes |
| `check_last_segment(segment)` | Check if segment is valid category |
| `check_top_level_category(attribute)` | Correct category classification |
| `check_if_personalized(attribute)` | Check if attribute is user-centric |

#### `merge_tree.py`
| Function | Description |
|----------|-------------|
| `json_to_tree(json_obj)` | Convert JSON to tree structure |
| `tree_to_json(tree)` | Convert tree back to JSON |
| `process_merge_response(response)` | Handle merge mapping |

#### `check_leaves.py`
| Class | Description |
|-------|-------------|
| `PathFilter` | Two-phase filtering (similarity + GPT validation) |

#### `convert_to_X.Y.Z.py`
| Function | Description |
|----------|-------------|
| `extract_paths(data)` | Flatten tree to X.Y.Z paths |
| `build_tree_text(paths)` | Generate tree visualization |

---

## 4. Usage Examples

### Generate a Single Profile
```python
from generate_user_profile.select_attributes import generate_user_profile, get_selected_attributes

# Generate base profile
user_profile = generate_user_profile()

# Get 200 relevant attributes
selected_attributes = get_selected_attributes(user_profile, attribute_count=200)
```

### Generate Complete Profile with All Details
```python
from generate_user_profile.generate_profile import generate_single_profile

# Generate complete profile with 250 attributes
complete_profile = generate_single_profile(attribute_count=250)
```

### Batch Generate Profiles
```python
from generate_user_profile.generate_profile import generate_multiple_profiles

# Generate 10 rounds of profiles (60 profiles total with varying attribute counts)
generate_multiple_profiles(num_rounds=10)
```

### Process Attributes
```python
from process_attributes.extract_personalized_attributes import PersonalizedAttributeExtractor

extractor = PersonalizedAttributeExtractor()
result = extractor.extract_attributes(
    question="What are some good restaurants nearby?",
    reason="User's location and food preferences affect recommendations"
)
```

---

## 5. Non-English Logs (Chinese) - Locations

The following files contain Chinese language comments and log messages that should be replaced with English:

### `generate_user_profile/generate_profile.py`
| Line | Chinese Text | Suggested English |
|------|--------------|-------------------|
| 15 | `# 添加当前目录到系统路径` | `# Add current directory to system path` |
| 27 | `"""获取项目根目录的路径"""` | `"""Get project root directory path"""` |
| 34-36 | `"""复制文件从源位置到目标位置"""` | `"""Copy files from source to target location"""` |
| 42 | `print(f"输出目录已设置为: {correct_output_dir}")` | `print(f"Output directory set to: {correct_output_dir}")` |
| 47-54 | Multiple docstring lines | Translate to English |
| 64-72 | Multiple docstring lines | Translate to English |
| 85 | `print(f"保存JSON文件时出错: {e}")` | `print(f"Error saving JSON file: {e}")` |
| 90-97 | Multiple docstring lines | Translate to English |
| 112-120 | Multiple docstring/parameter docs | Translate to English |
| 155 | `print(f"  正在一次性生成 {category_name} 下的 {len(leaf_paths)} 个属性值...")` | `print(f"  Generating {len(leaf_paths)} attribute values for {category_name}...")` |
| 158 | `print(f"  生成 {category_name} 属性值失败: 空响应")` | `print(f"  Failed to generate {category_name} attributes: empty response")` |
| 173 | `print(f"  成功生成 {len(generated_values)} 个属性值")` | `print(f"  Successfully generated {len(generated_values)} attribute values")` |
| 176-177 | JSON parsing error messages | Translate to English |
| 180 | Error message | Translate to English |
| 185-191 | Docstring | Translate to English |
| 246-250 | Docstring | Translate to English |
| 262-271 | Docstring | Translate to English |
| 276 | `print(f"{indent_str}正在生成 {section_name} 部分...")` | `print(f"{indent_str}Generating {section_name} section...")` |
| 329-337 | Docstring | Translate to English |
| 358 | Error message | Translate to English |
| 674-678 | Docstring | Translate to English |
| 680 | `print(f"开始生成 {num_rounds} 轮个人资料...")` | `print(f"Starting generation of {num_rounds} rounds of profiles...")` |
| 717 | `print(f"\n===== 开始生成第 {round_num+1}/{num_rounds} 轮用户资料 =====\n")` | `print(f"\n===== Starting round {round_num+1}/{num_rounds} =====\n")` |
| 723 | Similar print statements | Translate to English |
| 730-757 | Multiple print statements | Translate to English |

### `generate_user_profile/select_attributes.py`
| Line | Chinese Text | Suggested English |
|------|--------------|-------------------|
| 4-5 | `# 属性选择器脚本` | `# Attribute selector script` |
| 26 | `"""使用OpenAI API生成文本完成"""` | `"""Generate text completion using OpenAI API"""` |
| 72-85 | Class docstrings | Translate to English |
| 116-118 | Logger messages | Translate to English |
| 125 | `logger.error(f"从 {file_path} 加载JSON时出错: {e}")` | `logger.error(f"Error loading JSON from {file_path}: {e}")` |
| 128-162 | Multiple docstrings and logger messages | Translate to English |
| 175-202 | Multiple docstrings | Translate to English |
| 204-233 | Docstrings and comments | Translate to English |
| 239-297 | Method docstrings | Translate to English |
| 299-371 | Multiple docstrings | Translate to English |
| 373-396 | Docstrings | Translate to English |
| 398-401 | Docstrings | Translate to English |
| 434-471 | Docstrings | Translate to English |
| 473-494 | Docstrings | Translate to English |
| 496-517 | Docstrings | Translate to English |
| 521-601 | Multiple docstrings | Translate to English |
| 604-691 | Multiple docstrings and comments | Translate to English |
| 693-769 | Multiple docstrings | Translate to English |
| 827-856 | Comments | Translate to English |
| 869-899 | Docstrings and logger messages | Translate to English |

### `process_attributes/check_leaves.py`
| Line | Chinese Text | Suggested English |
|------|--------------|-------------------|
| 11 | `# 初始化sentence transformer模型` | `# Initialize sentence transformer model` |
| 14 | `# 设置OpenAI客户端` | `# Set up OpenAI client` |
| 23 | `"""获取同级路径"""` | `"""Get sibling paths"""` |
| 27-40 | Comments | Translate to English |
| 46-65 | Docstrings and comments | Translate to English |
| 73-102 | Docstrings and comments | Translate to English |
| 222 | `# 使用列表而不是集合` | `# Use list instead of set` |
| 338-354 | Docstrings and comments | Translate to English |
| 361-425 | Print statements | Translate to English |

### `process_attributes/merge_tree.py`
| Line | Chinese Text | Suggested English |
|------|--------------|-------------------|
| 16-24 | Comments | Translate to English |
| 250-312 | Print statements and comments | Translate to English |
| 325-379 | Docstrings and comments | Translate to English |

### `process_attributes/filter_personalized_attributes.py`
| Line | Chinese Text | Suggested English |
|------|--------------|-------------------|
| 11-291 | Multiple docstrings, print statements, and comments | Translate to English |

### `process_attributes/convert_to_X.Y.Z.py`
| Line | Chinese Text | Suggested English |
|------|--------------|-------------------|
| 8-149 | Multiple docstrings and comments | Translate to English |

### `process_attributes/process_attributes.py`
| Line | Chinese Text | Suggested English |
|------|--------------|-------------------|
| 3-16 | Comments and print statements | Translate to English |

### `process_attributes/extract_personalized_attributes.py`
| Line | Chinese Text | Suggested English |
|------|--------------|-------------------|
| 72-199 | Multiple comments | Translate to English |

---

## 6. Profile Generation Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROFILE GENERATION FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. BASE PROFILE GENERATION (based_data.py)                     │
│     ├── Age (7-85) & Age Group                                  │
│     ├── Gender (male/female)                                    │
│     ├── Location (Indian cities via GeoNames)                   │
│     ├── Career Status (GPT or occupation list)                  │
│     ├── Personal Values (GPT - positive/negative/neutral)       │
│     ├── Life Attitude (GPT)                                     │
│     ├── Personal Story (1-3 narratives, 150-200 words each)     │
│     └── Interests & Hobbies (inferred from stories)             │
│                                                                  │
│  2. ATTRIBUTE SELECTION (select_attributes.py)                  │
│     ├── Create embedding for profile (text-embedding-ada-002)   │
│     ├── Find neighbors using cosine similarity                  │
│     ├── Apply 5:3:2 ratio (near/mid/far neighbors)              │
│     └── Select target count (100-350 attributes)                │
│                                                                  │
│  3. PROFILE DETAIL GENERATION (generate_profile.py)             │
│     ├── Demographic Information                                 │
│     ├── Career and Work Identity                                │
│     ├── Core Values, Beliefs, Philosophy                        │
│     ├── Lifestyle and Daily Routine                             │
│     ├── Cultural and Social Context                             │
│     ├── Hobbies, Interests, and Lifestyle                       │
│     ├── Other Attributes                                        │
│     └── Final Narrative Summary (100-400 words)                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Key Configuration

| Setting | Location | Value |
|---------|----------|-------|
| OpenAI API Key | `config.py:24` | Hardcoded (should use env var) |
| GPT Model | `config.py:27` | `gpt-4.1-mini` |
| Embedding Model | `select_attributes.py:191` | `text-embedding-ada-002` |
| GeoNames Username | `config.py:20` | `demo` (limited) |
| Geographic Focus | `based_data.py:167` | India only |
| Attribute Embeddings | `select_attributes.py:61` | `data/attribute_embeddings.pkl` |
| Attributes Database | `select_attributes.py:58` | `data/large_attributes.json` |

---

## 8. Output Format

### Profile JSON Structure
```json
{
  "Demographic Information": { ... },
  "Career and Work Identity": { ... },
  "Core Values, Beliefs, and Philosophy": { ... },
  "Lifestyle and Daily Routine": { ... },
  "Cultural and Social Context": { ... },
  "Hobbies, Interests, and Lifestyle": { ... },
  "Other Attributes": { ... },
  "Summary": "First-person narrative (100-400 words)"
}
```

---

## 9. Recommendations

1. **Security**: Move API key from hardcoded value to environment variable
2. **Internationalization**: Replace all Chinese logs/comments with English
3. **Configuration**: Make geographic focus configurable (currently India-only)
4. **Error Handling**: Add more robust error handling for API failures
5. **Documentation**: Add type hints to all functions for better IDE support

---

*Report generated: 2025-12-08*
