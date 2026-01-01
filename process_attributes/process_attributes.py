import json
import os

# Project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

# Read JSON file
input_file = os.path.join(DATA_DIR, 'personalized_attributes.json')
with open(input_file, 'r', encoding='utf-8') as file:
    data = json.load(file)

# Get personalized_attributes and deduplicate
personalized_attributes = list(set(data['personalized_attributes']))

# Sort alphabetically
personalized_attributes.sort()

# Print results
print(f"Attribute count before deduplication: {len(data['personalized_attributes'])}")
print(f"Attribute count after deduplication: {len(personalized_attributes)}")
print("\nDeduplicated attribute list:")
for attr in personalized_attributes:
    print(attr)
