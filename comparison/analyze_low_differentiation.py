"""
Analyze comparison files to identify criteria with low differentiation.

This script processes all comparison files and identifies evaluation criteria
where the difference between persona responses is less than 10% for more than
half of all comparisons within a research. This helps identify criteria that
may need improvement as they don't effectively differentiate between personas.
"""

import os
import json
import argparse
import sys
from typing import Dict, List, Any, Tuple
from collections import defaultdict
from datetime import datetime

# Add parent directory to path to import prompts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prompts import CRITERIA_DEFINITIONS


def load_comparison_files(output_dir: str) -> List[Dict[str, Any]]:
    """Load all comparison logprob JSON files from the output directory.
    
    Args:
        output_dir: Path to directory containing comparison files
        
    Returns:
        List of comparison data dictionaries
    """
    comparison_files = []
    
    if not os.path.exists(output_dir):
        raise ValueError(f"Output directory does not exist: {output_dir}")
    
    # Find all comparison_logprob_*.json files
    for filename in os.listdir(output_dir):
        if filename.startswith("comparison_logprob_") and filename.endswith(".json"):
            filepath = os.path.join(output_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    comparison_files.append(data)
            except Exception as e:
                print(f"Warning: Failed to load {filename}: {e}")
                continue
    
    return comparison_files


def analyze_criterion_differences(
    comparisons: List[Dict[str, Any]],
    threshold: float = 10.0
) -> Dict[str, Dict[str, Any]]:
    """Analyze differences for each criterion across all comparisons.
    
    Aggregates statistics across all research projects for each criterion.
    
    Args:
        comparisons: List of comparison data dictionaries
        threshold: Threshold percentage for low differentiation (default: 10%)
        
    Returns:
        Dictionary mapping criterion_key to analysis results
    """
    # Track statistics per criterion (aggregated across all research)
    criterion_stats = defaultdict(lambda: {
        "criterion_name": None,
        "total_comparisons": 0,
        "low_yes_diff_count": 0,
        "low_no_diff_count": 0,
        "low_diff_count": 0,  # Either yes or no difference < threshold
        "yes_differences": [],
        "no_differences": [],
        "research_ids": set()  # Track which research projects this criterion appears in
    })
    
    # Process all comparison files
    for comp in comparisons:
        research_id = comp.get("research_id")
        criteria_results = comp.get("criteria_results", [])
        
        for criterion_result in criteria_results:
            criterion_key = criterion_result.get("criterion_key")
            if not criterion_key:
                continue
            
            # Get criterion name
            criterion_name = criterion_result.get("criterion_name", criterion_key)
            criterion_stats[criterion_key]["criterion_name"] = criterion_name
            criterion_stats[criterion_key]["total_comparisons"] += 1
            if research_id:
                criterion_stats[criterion_key]["research_ids"].add(research_id)
            
            # Get comparison data
            comparison = criterion_result.get("comparison", {})
            yes_diff = comparison.get("yes_difference")
            no_diff = comparison.get("no_difference")
            
            # Check if differences are below threshold
            if yes_diff is not None:
                abs_yes_diff = abs(yes_diff)
                criterion_stats[criterion_key]["yes_differences"].append(abs_yes_diff)
                if abs_yes_diff < threshold:
                    criterion_stats[criterion_key]["low_yes_diff_count"] += 1
                    criterion_stats[criterion_key]["low_diff_count"] += 1
            
            if no_diff is not None:
                abs_no_diff = abs(no_diff)
                criterion_stats[criterion_key]["no_differences"].append(abs_no_diff)
                if abs_no_diff < threshold:
                    criterion_stats[criterion_key]["low_no_diff_count"] += 1
                    # Only count once if both are low
                    if yes_diff is None or abs(yes_diff) >= threshold:
                        criterion_stats[criterion_key]["low_diff_count"] += 1
    
    # Filter to only include individual criteria (not category-level aggregations)
    valid_criterion_keys = set(CRITERIA_DEFINITIONS.keys())
    
    # Calculate percentages and flag criteria
    results = {}
    for criterion_key, stats in criterion_stats.items():
        # Skip category-level criteria, only include individual criteria
        if criterion_key not in valid_criterion_keys:
            continue
            
        total = stats["total_comparisons"]
        if total > 0:
            low_diff_pct = (stats["low_diff_count"] / total) * 100
            low_yes_pct = (stats["low_yes_diff_count"] / total) * 100 if total > 0 else 0
            low_no_pct = (stats["low_no_diff_count"] / total) * 100 if total > 0 else 0
            
            # Flag if more than 50% show low differentiation
            needs_improvement = low_diff_pct > 50.0
            
            # Calculate average differences
            avg_yes_diff = sum(stats["yes_differences"]) / len(stats["yes_differences"]) if stats["yes_differences"] else None
            avg_no_diff = sum(stats["no_differences"]) / len(stats["no_differences"]) if stats["no_differences"] else None
            
            results[criterion_key] = {
                "criterion_key": criterion_key,
                "criterion_name": stats["criterion_name"],
                "total_comparisons": total,
                "research_count": len(stats["research_ids"]),
                "low_diff_count": stats["low_diff_count"],
                "low_yes_diff_count": stats["low_yes_diff_count"],
                "low_no_diff_count": stats["low_no_diff_count"],
                "low_diff_percentage": round(low_diff_pct, 2),
                "low_yes_diff_percentage": round(low_yes_pct, 2),
                "low_no_diff_percentage": round(low_no_pct, 2),
                "avg_yes_difference": round(avg_yes_diff, 2) if avg_yes_diff is not None else None,
                "avg_no_difference": round(avg_no_diff, 2) if avg_no_diff is not None else None,
                "needs_improvement": needs_improvement
            }
    
    return results


def generate_report(
    results: Dict[str, Dict[str, Any]],
    threshold: float = 10.0
) -> str:
    """Generate a markdown report from analysis results.
    
    Args:
        results: Dictionary mapping criterion_key to analysis results
        threshold: Threshold percentage used for analysis
        
    Returns:
        Markdown formatted report string
    """
    # Sort by criterion name
    sorted_results = sorted(
        results.values(),
        key=lambda x: x["criterion_name"]
    )
    
    report_lines = [
        "# Low Differentiation Analysis Report",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Threshold**: {threshold}% difference",
        "",
        f"This report identifies evaluation criteria where the difference between persona",
        f"responses is less than {threshold}% for more than half of all comparisons across all research projects.",
        "These criteria may need improvement as they don't effectively differentiate between personas.",
        "",
        "---",
        ""
    ]
    
    # Generate summary table
    report_lines.extend([
        "## Summary",
        "",
        "| Criterion | Total Comparisons | Research Count | Low Diff Count | Low Diff % | Needs Improvement |",
        "|-----------|-------------------|----------------|----------------|------------|-------------------|"
    ])
    
    flagged_count = 0
    total_criteria = len(sorted_results)
    
    for result in sorted_results:
        if result["needs_improvement"]:
            flagged_count += 1
        
        flag_marker = "⚠️ **YES**" if result["needs_improvement"] else "No"
        
        report_lines.append(
            f"| {result['criterion_name']} | {result['total_comparisons']} | "
            f"{result['research_count']} | {result['low_diff_count']} | "
            f"{result['low_diff_percentage']}% | {flag_marker} |"
        )
    
    report_lines.extend([
        "",
        f"**Total Criteria Analyzed**: {total_criteria}",
        f"**Criteria Needing Improvement**: {flagged_count}",
        "",
        "---",
        ""
    ])
    
    # Detailed section for criteria needing improvement
    flagged_results = [r for r in sorted_results if r["needs_improvement"]]
    
    if flagged_results:
        report_lines.extend([
            "## ⚠️ Criteria Needing Improvement",
            "",
            "These criteria show low differentiation (<10% difference) in more than 50% of comparisons:",
            ""
        ])
        
        for result in flagged_results:
            report_lines.extend([
                f"### {result['criterion_name']} (`{result['criterion_key']}`)",
                "",
                f"- **Total Comparisons**: {result['total_comparisons']}",
                f"- **Research Projects**: {result['research_count']}",
                f"- **Low Differentiation Count**: {result['low_diff_count']} ({result['low_diff_percentage']}%)",
                f"- **Low Yes Difference Count**: {result['low_yes_diff_count']} ({result['low_yes_diff_percentage']}%)",
                f"- **Low No Difference Count**: {result['low_no_diff_count']} ({result['low_no_diff_percentage']}%)",
                f"- **Average Yes Difference**: {result['avg_yes_difference']}%" if result['avg_yes_difference'] is not None else "- **Average Yes Difference**: N/A",
                f"- **Average No Difference**: {result['avg_no_difference']}%" if result['avg_no_difference'] is not None else "- **Average No Difference**: N/A",
                ""
            ])
    
    # Show all criteria
    report_lines.extend([
        "## All Criteria",
        "",
        "| Criterion | Total | Research | Low Diff Count | Low Diff % | Low Yes % | Low No % | Avg Yes Diff | Avg No Diff |",
        "|----------|-------|----------|----------------|------------|-----------|----------|--------------|-------------|"
    ])
    
    for result in sorted_results:
        avg_yes = f"{result['avg_yes_difference']}%" if result['avg_yes_difference'] is not None else "N/A"
        avg_no = f"{result['avg_no_difference']}%" if result['avg_no_difference'] is not None else "N/A"
        
        report_lines.append(
            f"| {result['criterion_name']} | {result['total_comparisons']} | "
            f"{result['research_count']} | {result['low_diff_count']} | "
            f"{result['low_diff_percentage']}% | {result['low_yes_diff_percentage']}% | "
            f"{result['low_no_diff_percentage']}% | {avg_yes} | {avg_no} |"
        )
    
    return "\n".join(report_lines)


def save_json_report(
    results: Dict[str, Dict[str, Any]],
    output_path: str,
    threshold: float = 10.0
) -> None:
    """Save analysis results as JSON with criteria aggregated across all research.
    
    Args:
        results: Dictionary mapping criterion_key to analysis results
        output_path: Path to save JSON file
        threshold: Threshold used for analysis
    """
    # Build JSON structure
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "threshold": threshold,
        "criteria": []
    }
    
    # Sort criteria by name
    sorted_results = sorted(
        results.values(),
        key=lambda x: x["criterion_name"]
    )
    
    for result in sorted_results:
        criterion_data = {
            "criterion_key": result["criterion_key"],
            "criterion_name": result["criterion_name"],
            "total_comparisons": result["total_comparisons"],
            "research_count": result["research_count"],
            "low_diff_count": result["low_diff_count"],
            "yes": {
                "low_diff_count": result["low_yes_diff_count"],
                "low_diff_percentage": result["low_yes_diff_percentage"],
                "avg_difference": result["avg_yes_difference"]
            },
            "no": {
                "low_diff_count": result["low_no_diff_count"],
                "low_diff_percentage": result["low_no_diff_percentage"],
                "avg_difference": result["avg_no_difference"]
            },
            "needs_improvement": result["needs_improvement"]
        }
        json_data["criteria"].append(criterion_data)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)


def main():
    """Main entry point for the analysis script."""
    parser = argparse.ArgumentParser(
        description="Analyze comparison files to identify criteria with low differentiation"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "output"),
        help="Directory containing comparison JSON files (default: comparison/output)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=10.0,
        help="Threshold percentage for low differentiation (default: 10.0)"
    )
    parser.add_argument(
        "--research-id",
        type=str,
        help="Filter analysis to a specific research ID (optional, analyzes all if not provided)"
    )
    parser.add_argument(
        "--json-output",
        type=str,
        help="Path to save JSON report (optional)"
    )
    parser.add_argument(
        "--markdown-output",
        type=str,
        help="Path to save Markdown report (optional)"
    )
    
    args = parser.parse_args()
    
    print(f"Loading comparison files from: {args.output_dir}")
    comparisons = load_comparison_files(args.output_dir)
    print(f"Loaded {len(comparisons)} comparison files")
    
    if not comparisons:
        print("No comparison files found. Exiting.")
        return
    
    # Filter by research_id if provided
    if args.research_id:
        original_count = len(comparisons)
        comparisons = [c for c in comparisons if c.get("research_id") == args.research_id]
        print(f"Filtered to research ID '{args.research_id}': {len(comparisons)} comparison files (from {original_count})")
        
        if not comparisons:
            print(f"No comparison files found for research ID '{args.research_id}'. Exiting.")
            return
    
    print(f"Analyzing differences with threshold: {args.threshold}%")
    results = analyze_criterion_differences(comparisons, threshold=args.threshold)
    print(f"Analyzed {len(results)} criteria (aggregated across all research projects)")
    
    # Count flagged criteria
    flagged = sum(1 for r in results.values() if r["needs_improvement"])
    print(f"Found {flagged} criteria needing improvement (>{50}% low differentiation)")
    
    # Generate reports
    output_dir = args.output_dir
    
    # Determine output file names
    if args.research_id:
        default_json_name = f"low_differentiation_analysis_{args.research_id}.json"
        default_md_name = f"LOW_DIFFERENTIATION_REPORT_{args.research_id}.md"
    else:
        default_json_name = "low_differentiation_analysis.json"
        default_md_name = "LOW_DIFFERENTIATION_REPORT.md"
    
    # Save JSON report
    json_path = args.json_output or os.path.join(output_dir, default_json_name)
    print(f"\nSaving JSON report to: {json_path}")
    save_json_report(results, json_path, threshold=args.threshold)
    
    # Generate and save Markdown report
    markdown_path = args.markdown_output or os.path.join(output_dir, default_md_name)
    print(f"Generating Markdown report...")
    report = generate_report(results, threshold=args.threshold)
    
    print(f"Saving Markdown report to: {markdown_path}")
    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\nAnalysis complete!")
    print(f"\nSummary:")
    if args.research_id:
        print(f"  - Research ID: {args.research_id}")
    print(f"  - Total criteria analyzed: {len(results)}")
    print(f"  - Criteria needing improvement: {flagged}")
    print(f"  - Reports saved to:")
    print(f"    - JSON: {json_path}")
    print(f"    - Markdown: {markdown_path}")


if __name__ == "__main__":
    main()
