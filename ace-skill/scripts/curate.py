#!/usr/bin/env python3
"""
ACE Playbook Curation Script

Deterministic curation logic for pruning, deduplicating, and optimizing playbook entries.
Run standalone or called by MCP server's curate_playbook() tool.

Usage:
    python curate.py <playbook_path> [--threshold 3] [--dry-run]
"""

import re
import argparse
from pathlib import Path
from difflib import SequenceMatcher
from collections import defaultdict

# Entry pattern: [id-00001] helpful=N harmful=M :: content
ENTRY_PATTERN = re.compile(
    r'^\[([a-z]{3}-\d{5})\]\s+helpful=(\d+)\s+harmful=(\d+)\s+::\s+(.+)$'
)

SECTION_PATTERN = re.compile(r'^##\s+(.+)$')

SIMILARITY_THRESHOLD = 0.85  # Entries above this are considered duplicates


def parse_playbook(content: str) -> dict:
    """Parse playbook into sections with entries."""
    sections = defaultdict(list)
    current_section = None
    
    for line in content.split('\n'):
        line = line.strip()
        
        section_match = SECTION_PATTERN.match(line)
        if section_match:
            current_section = section_match.group(1)
            continue
        
        entry_match = ENTRY_PATTERN.match(line)
        if entry_match and current_section:
            entry_id, helpful, harmful, text = entry_match.groups()
            sections[current_section].append({
                'id': entry_id,
                'helpful': int(helpful),
                'harmful': int(harmful),
                'content': text,
                'raw': line
            })
    
    return dict(sections)


def similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_duplicates(entries: list) -> list[set]:
    """Find groups of duplicate entries based on content similarity."""
    duplicate_groups = []
    processed = set()
    
    for i, entry_a in enumerate(entries):
        if entry_a['id'] in processed:
            continue
            
        group = {entry_a['id']}
        for j, entry_b in enumerate(entries[i+1:], start=i+1):
            if entry_b['id'] in processed:
                continue
            if similarity(entry_a['content'], entry_b['content']) >= SIMILARITY_THRESHOLD:
                group.add(entry_b['id'])
                processed.add(entry_b['id'])
        
        if len(group) > 1:
            duplicate_groups.append(group)
            processed.add(entry_a['id'])
    
    return duplicate_groups


def merge_duplicates(entries: list, duplicate_group: set) -> dict:
    """Merge duplicate entries, keeping highest helpful score and combining counters."""
    duplicates = [e for e in entries if e['id'] in duplicate_group]
    
    # Keep entry with highest helpful count
    best = max(duplicates, key=lambda e: e['helpful'])
    
    # Sum counters from all duplicates
    total_helpful = sum(e['helpful'] for e in duplicates)
    total_harmful = sum(e['harmful'] for e in duplicates)
    
    return {
        'id': best['id'],
        'helpful': total_helpful,
        'harmful': total_harmful,
        'content': best['content'],
        'raw': f"[{best['id']}] helpful={total_helpful} harmful={total_harmful} :: {best['content']}"
    }


def curate_section(entries: list, harmful_threshold: int) -> tuple[list, dict]:
    """
    Curate a section's entries.
    
    Returns:
        (curated_entries, stats)
    """
    stats = {
        'removed_harmful': 0,
        'merged_duplicates': 0,
        'kept': 0
    }
    
    # Step 1: Remove entries where harmful > helpful + threshold
    filtered = []
    for entry in entries:
        if entry['harmful'] > entry['helpful'] + harmful_threshold:
            stats['removed_harmful'] += 1
        else:
            filtered.append(entry)
    
    # Step 2: Find and merge duplicates
    duplicate_groups = find_duplicates(filtered)
    merged_ids = set()
    curated = []
    
    for group in duplicate_groups:
        merged = merge_duplicates(filtered, group)
        curated.append(merged)
        merged_ids.update(group)
        stats['merged_duplicates'] += len(group) - 1
    
    # Step 3: Keep non-duplicate entries
    for entry in filtered:
        if entry['id'] not in merged_ids:
            curated.append(entry)
            stats['kept'] += 1
    
    # Sort by helpful score descending
    curated.sort(key=lambda e: e['helpful'], reverse=True)
    
    return curated, stats


def rebuild_playbook(sections: dict, curated_sections: dict) -> str:
    """Rebuild playbook content from curated sections."""
    lines = []
    
    section_order = [
        'STRATEGIES & INSIGHTS',
        'FORMULAS & CALCULATIONS',
        'COMMON MISTAKES TO AVOID',
        'DOMAIN KNOWLEDGE'
    ]
    
    # Add sections in order, then any extras
    all_sections = section_order + [s for s in curated_sections if s not in section_order]
    
    for section in all_sections:
        if section not in curated_sections:
            continue
        entries = curated_sections[section]
        if not entries:
            continue
            
        lines.append(f"## {section}")
        for entry in entries:
            lines.append(entry['raw'])
        lines.append("")
    
    return '\n'.join(lines)


def curate_playbook(content: str, harmful_threshold: int = 3) -> tuple[str, dict]:
    """
    Main curation function.
    
    Args:
        content: Raw playbook content
        harmful_threshold: Remove entries where harmful > helpful + threshold
    
    Returns:
        (curated_content, overall_stats)
    """
    sections = parse_playbook(content)
    curated_sections = {}
    overall_stats = {
        'sections_processed': 0,
        'total_removed_harmful': 0,
        'total_merged_duplicates': 0,
        'total_kept': 0,
        'original_count': 0,
        'final_count': 0
    }
    
    for section_name, entries in sections.items():
        overall_stats['original_count'] += len(entries)
        curated, stats = curate_section(entries, harmful_threshold)
        curated_sections[section_name] = curated
        
        overall_stats['sections_processed'] += 1
        overall_stats['total_removed_harmful'] += stats['removed_harmful']
        overall_stats['total_merged_duplicates'] += stats['merged_duplicates']
        overall_stats['total_kept'] += stats['kept']
        overall_stats['final_count'] += len(curated)
    
    curated_content = rebuild_playbook(sections, curated_sections)
    return curated_content, overall_stats


def main():
    parser = argparse.ArgumentParser(description='Curate ACE playbook')
    parser.add_argument('playbook', type=Path, help='Path to playbook.md')
    parser.add_argument('--threshold', type=int, default=3, 
                        help='Harmful threshold (default: 3)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show changes without writing')
    args = parser.parse_args()
    
    if not args.playbook.exists():
        print(f"Error: {args.playbook} not found")
        return 1
    
    content = args.playbook.read_text()
    curated, stats = curate_playbook(content, args.threshold)
    
    print(f"Curation complete:")
    print(f"  Sections processed: {stats['sections_processed']}")
    print(f"  Entries removed (harmful): {stats['total_removed_harmful']}")
    print(f"  Entries merged (duplicates): {stats['total_merged_duplicates']}")
    print(f"  Original count: {stats['original_count']}")
    print(f"  Final count: {stats['final_count']}")
    
    if args.dry_run:
        print("\n--- Curated playbook (dry run) ---\n")
        print(curated)
    else:
        args.playbook.write_text(curated)
        print(f"\nWritten to {args.playbook}")
    
    return 0


if __name__ == '__main__':
    exit(main())
