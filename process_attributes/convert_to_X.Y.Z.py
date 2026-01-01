#!/usr/bin/env python3
"""
Convert nested attribute JSON to X.Y.Z path format.

This script:
1. Reads a nested attribute JSON file
2. Extracts all paths in X.Y.Z format
3. Generates a tree visualization
"""
import os
import json
from collections import defaultdict

# Get project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'outputs')


def extract_paths(data, prefix=""):
    """
    Recursively extract all paths from nested dict, separated by dots.
    If node value is None or non-dict, it's considered a leaf node.
    """
    paths = []
    if isinstance(data, dict):
        # 如果字典为空(如叶子节点存为None), 返回当前prefix（如果有的话）
        if not data:
            if prefix:
                paths.append(prefix)
            return paths
        for key, value in data.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            # 如果value为字典，则进一步递归
            if isinstance(value, dict):
                # 如果该字典为 None 或为空，则认为是叶子
                child_paths = extract_paths(value, new_prefix)
                if child_paths:
                    paths.extend(child_paths)
                else:
                    paths.append(new_prefix)
            else:
                paths.append(new_prefix)
    else:
        # 如果data不是字典，则直接返回prefix作为路径
        if prefix:
            paths.append(prefix)
    return paths

def build_parent_child_map(paths):
    """
    构建父子关系映射，每个点号分隔的部分都成为独立节点
    例如：user_preferences.individual_personal_attributes.budget 会生成：
    - user_preferences
      - individual_personal_attributes
        - budget
    """
    parent_child_map = defaultdict(set)
    
    for path in paths:
        parts = path.split('.')
        
        # 为每个路径构建完整的层次结构
        current_path = ""
        for i, part in enumerate(parts):
            # 构建当前节点的完整路径
            if current_path:
                current_path = f"{current_path}.{part}"
            else:
                current_path = part
                
            # 如果不是第一个组件，将其添加为父节点的子节点
            if i > 0:
                parent_path = '.'.join(parts[:i])
                parent_child_map[parent_path].add(current_path)
            
            # 如果是最后一个组件，将其添加为叶子节点
            if i == len(parts) - 1:
                parent_child_map[current_path] = set()  # 叶子节点没有子节点
    
    # 将set转换为排序后的list
    return {k: sorted(v) for k, v in parent_child_map.items()}

def generate_tree_text(parent_child_map):
    """
    生成树形文本结构
    """
    tree_lines = []
    
    # 获取所有根节点（没有父节点的节点）
    all_children = set()
    for children in parent_child_map.values():
        all_children.update(children)
    root_nodes = set(parent_child_map.keys()) - all_children
    
    def add_node(node, prefix="", seen=None):
        if seen is None:
            seen = set()
            
        # 避免循环引用
        if node in seen:
            return
        seen.add(node)
        
        # 获取节点的最后一个组件作为显示名称
        display_name = node.split('.')[-1]
        
        # 添加当前节点
        tree_lines.append(f"{prefix}- {display_name}")
        
        # 处理子节点
        children = sorted(parent_child_map.get(node, []))
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            child_prefix = prefix + ('  └─ ' if is_last else '  ├─ ')
            next_prefix = prefix + ('  ' if is_last else '  │ ')
            add_node(child, next_prefix, seen)
    
    # 从每个根节点开始构建树
    for root in sorted(root_nodes):
        add_node(root)
        tree_lines.append('')  # 添加空行分隔不同的树
    
    return tree_lines

def main():
    # Use project data directory for input, outputs directory for output
    input_file = os.path.join(DATA_DIR, "attributes_merged.json")

    # Create outputs directory if not exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_json = os.path.join(OUTPUT_DIR, "paths_X.Y.Z.json")
    output_txt = os.path.join(OUTPUT_DIR, "paths_tree.txt")

    # Read JSON data
    try:
        print(f"Reading input file: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to read file: {e}")
        return

    # Extract all X.Y.Z paths
    paths = extract_paths(data)
    print(f"Extracted {len(paths)} paths")

    # Save as JSON
    result = {"paths": sorted(paths)}
    try:
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Path info saved to: {output_json}")
    except Exception as e:
        print(f"Failed to save JSON: {e}")
        return

    # Generate tree text structure
    try:
        parent_child_map = build_parent_child_map(paths)
        tree_lines = generate_tree_text(parent_child_map)

        # Save tree text
        with open(output_txt, 'w', encoding='utf-8') as f:
            f.write('\n'.join(tree_lines))
        print(f"Tree structure saved to: {output_txt}")
    except Exception as e:
        print(f"Failed to save tree text: {e}")

if __name__ == "__main__":
    main()