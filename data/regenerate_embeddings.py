#!/usr/bin/env python3
"""
Regenerate attribute embeddings using OpenAI's text-embedding-ada-002 model.

This script:
1. Loads attributes from large_attributes.json
2. Flattens them to X.Y.Z paths
3. Generates embeddings for each path using OpenAI API
4. Saves embeddings to attribute_embeddings.pkl
"""

import json
import pickle
import os
import sys
import numpy as np
from tqdm import tqdm
import time

# Add parent directory to path to access config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'generate_user_profile'))
from config import client

EMBEDDING_MODEL = "text-embedding-ada-002"
BATCH_SIZE = 100  # OpenAI allows up to 2048 inputs per request, but smaller batches are safer


def flatten_attributes(d: dict, prefix: str = '') -> list:
    """Flatten nested dict to list of X.Y.Z paths."""
    paths = []
    for k, v in d.items():
        path = f'{prefix}.{k}' if prefix else k
        if isinstance(v, dict) and v:
            paths.extend(flatten_attributes(v, path))
        else:
            paths.append(path)
    return paths


def get_embeddings_batch(texts: list) -> list:
    """Get embeddings for a batch of texts."""
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        print(f"Error getting embeddings: {e}")
        return None


def regenerate_embeddings(input_file: str, output_file: str):
    """Regenerate embeddings for all attribute paths."""

    # Load attributes
    print(f"Loading attributes from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        attributes = json.load(f)

    # Flatten to paths
    print("Flattening to X.Y.Z paths...")
    paths = flatten_attributes(attributes)
    print(f"Total paths: {len(paths)}")

    # Generate embeddings in batches
    print(f"Generating embeddings using {EMBEDDING_MODEL}...")
    all_embeddings = []

    for i in tqdm(range(0, len(paths), BATCH_SIZE), desc="Batches"):
        batch = paths[i:i + BATCH_SIZE]
        embeddings = get_embeddings_batch(batch)

        if embeddings is None:
            print(f"Failed to get embeddings for batch {i // BATCH_SIZE}")
            # Retry once after a delay
            time.sleep(2)
            embeddings = get_embeddings_batch(batch)
            if embeddings is None:
                raise RuntimeError(f"Failed to get embeddings after retry")

        all_embeddings.extend(embeddings)

        # Small delay to avoid rate limits
        time.sleep(0.1)

    # Convert to numpy array
    embeddings_array = np.array(all_embeddings)
    print(f"Embeddings shape: {embeddings_array.shape}")

    # Save to pickle
    print(f"Saving to {output_file}...")
    data = {
        'attribute_paths': paths,
        'paths': paths,  # Duplicate key for compatibility
        'embeddings': embeddings_array
    }

    with open(output_file, 'wb') as f:
        pickle.dump(data, f)

    # Verify the saved file
    print("Verifying saved file...")
    with open(output_file, 'rb') as f:
        loaded = pickle.load(f)

    print(f"Verification: {len(loaded['paths'])} paths, {loaded['embeddings'].shape} embeddings")
    print("Done!")


if __name__ == "__main__":
    data_dir = os.path.dirname(os.path.abspath(__file__))

    input_file = os.path.join(data_dir, 'large_attributes.json')
    output_file = os.path.join(data_dir, 'attribute_embeddings.pkl')

    # Backup old file if exists
    if os.path.exists(output_file):
        backup_file = output_file + '.bak'
        print(f"Backing up old file to {backup_file}")
        os.rename(output_file, backup_file)

    regenerate_embeddings(input_file, output_file)
