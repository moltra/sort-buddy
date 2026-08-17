#!/usr/bin/env python3
"""
Analyze sort-buddy classification history and feedback.

This script processes ~/.sort-buddy-history.jsonl and optionally
~/.sort-buddy-feedback.jsonl to generate analytics reports.
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def load_jsonl(filepath: str) -> list[dict[str, Any]]:
    """Load a JSONL file (one JSON object per line)."""
    if not os.path.exists(filepath):
        return []
    
    records = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Warning: Invalid JSON on line {line_num}: {e}", file=sys.stderr)
    except IOError as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return []
    
    return records


def extract_domain(email_address: str) -> str:
    """Extract domain from email address."""
    if '@' not in email_address:
        return "unknown"
    return email_address.split('@')[1].lower()


def get_hour_from_timestamp(timestamp: str | None) -> int | None:
    """Extract hour from ISO timestamp if present."""
    if not timestamp:
        return None
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.hour
    except (ValueError, AttributeError):
        return None


def analyze_history(history: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze classification history records."""
    total = len(history)
    
    # Messages per account
    messages_per_account = Counter()
    # Messages per folder
    messages_per_folder = Counter()
    # Messages per model and mode
    messages_per_model_mode = Counter()
    # Sender domains per folder
    domains_per_folder: dict[str, Counter] = defaultdict(Counter)
    # Classifications by hour
    classifications_by_hour = Counter()
    
    for record in history:
        # Account
        account = record.get('account', 'unknown')
        messages_per_account[account] += 1
        
        # Folder
        folder = record.get('folder', 'unknown')
        messages_per_folder[folder] += 1
        
        # Model and mode
        model = record.get('model', 'unknown')
        mode = record.get('mode', 'unknown')
        messages_per_model_mode[f"{model} ({mode})"] += 1
        
        # Sender domain
        from_field = record.get('from', '')
        domain = extract_domain(from_field)
        domains_per_folder[folder][domain] += 1
        
        # Hour of day
        timestamp = record.get('timestamp')
        hour = get_hour_from_timestamp(timestamp)
        if hour is not None:
            classifications_by_hour[hour] += 1
    
    # Top 20 sender domains per folder
    top_domains_per_folder = {}
    for folder, domain_counter in domains_per_folder.items():
        top_domains_per_folder[folder] = domain_counter.most_common(20)
    
    return {
        'total': total,
        'messages_per_account': dict(messages_per_account),
        'messages_per_folder': dict(messages_per_folder),
        'messages_per_model_mode': dict(messages_per_model_mode),
        'top_domains_per_folder': top_domains_per_folder,
        'classifications_by_hour': dict(classifications_by_hour),
    }


def analyze_feedback(feedback: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze feedback records for corrections."""
    corrections = Counter()
    
    for record in feedback:
        original = record.get('original_folder', 'unknown')
        corrected = record.get('corrected_folder', 'unknown')
        corrections[f"{original} → {corrected}"] += 1
    
    return {
        'total': len(feedback),
        'corrections': dict(corrections),
    }


def find_potential_issues(history: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Find potential misclassifications using heuristics."""
    issues = {
        'automated_in_important_personal': [],
        'urgent_in_newsletters_personal': [],
        'promotional_in_important_personal': [],
    }
    
    # Heuristic 1: Automated senders in Important/Personal
    automated_keywords = [
        'postmaster', 'mailer-daemon', 'no-reply', 'noreply',
        'notifications', 'alerts', 'newsletter', 'deals',
        'coupons', 'jobalerts'
    ]
    
    # Heuristic 2: Suspicious subjects in Newsletters/Personal
    urgent_keywords = ['past due', 'urgent', 'account current', 'immediate action']
    
    # Heuristic 3: Promotional content in Important/Personal
    promotional_keywords = ['unsubscribe', 'promotional', 'deals', 'sale', '% off']
    
    for record in history:
        folder = record.get('folder', '')
        from_field = record.get('from', '').lower()
        subject = record.get('subject', '').lower()
        
        # Heuristic 1
        if folder in ('Important', 'Personal'):
            for keyword in automated_keywords:
                if keyword in from_field:
                    issues['automated_in_important_personal'].append({
                        'from': record.get('from', ''),
                        'subject': record.get('subject', ''),
                        'folder': folder,
                        'keyword': keyword,
                    })
                    break
        
        # Heuristic 2
        if folder in ('Newsletters', 'Personal'):
            for keyword in urgent_keywords:
                if keyword in subject:
                    issues['urgent_in_newsletters_personal'].append({
                        'from': record.get('from', ''),
                        'subject': record.get('subject', ''),
                        'folder': folder,
                        'keyword': keyword,
                    })
                    break
        
        # Heuristic 3
        if folder in ('Important', 'Personal'):
            for keyword in promotional_keywords:
                if keyword in subject:
                    issues['promotional_in_important_personal'].append({
                        'from': record.get('from', ''),
                        'subject': record.get('subject', ''),
                        'folder': folder,
                        'keyword': keyword,
                    })
                    break
    
    return issues


def generate_recommendations(
    analysis: dict[str, Any],
    feedback_analysis: dict[str, Any] | None,
    issues: dict[str, list[dict[str, Any]]]
) -> list[str]:
    """Generate recommendations based on analysis."""
    recommendations = []
    
    # Get most common folders
    folders = analysis.get('messages_per_folder', {})
    top_folders = sorted(folders.items(), key=lambda x: x[1], reverse=True)[:5]
    
    if top_folders:
        recommendations.append(
            f"Top folders by volume: {', '.join(f'{f} ({c})' for f, c in top_folders)}"
        )
    
    # Check for automated sender issues
    automated_issues = issues.get('automated_in_important_personal', [])
    if automated_issues:
        count = len(automated_issues)
        recommendations.append(
            f"Found {count} messages from automated senders in Important/Personal. "
            "Add rule: 'If sender contains postmaster, no-reply, notifications, etc., "
            "classify as Updates or Notifications, not Important/Personal.'"
        )
    
    # Check for urgent subject issues
    urgent_issues = issues.get('urgent_in_newsletters_personal', [])
    if urgent_issues:
        count = len(urgent_issues)
        recommendations.append(
            f"Found {count} messages with urgent subjects in Newsletters/Personal. "
            "Add rule: 'If subject contains urgent terms (Past Due, Urgent, etc.), "
            "classify as Important or Spam, not Newsletters/Personal.'"
        )
    
    # Check for promotional content issues
    promotional_issues = issues.get('promotional_in_important_personal', [])
    if promotional_issues:
        count = len(promotional_issues)
        recommendations.append(
            f"Found {count} messages with promotional content in Important/Personal. "
            "Add rule: 'If subject contains promotional terms (unsubscribe, sale, etc.), "
            "classify as Newsletters or Promotions, not Important/Personal.'"
        )
    
    # If feedback exists, suggest using it
    if feedback_analysis and feedback_analysis.get('total', 0) > 0:
        corrections = feedback_analysis.get('corrections', {})
        top_corrections = sorted(corrections.items(), key=lambda x: x[1], reverse=True)[:3]
        if top_corrections:
            recommendations.append(
                f"User feedback available with {feedback_analysis['total']} corrections. "
                "Add these as few-shot examples to the prompt:"
            )
            for correction, count in top_corrections:
                recommendations.append(f"  - {correction} ({count} times)")
    
    # Add general recommendations if we have few
    if len(recommendations) < 3:
        recommendations.append(
            "Consider adding few-shot examples for your most common folder classifications."
        )
        recommendations.append(
            "Review the top sender domains per folder to ensure they match expectations."
        )
    
    return recommendations


def format_report(
    analysis: dict[str, Any],
    feedback_analysis: dict[str, Any] | None,
    issues: dict[str, list[dict[str, Any]]],
    recommendations: list[str]
) -> str:
    """Format the complete report."""
    lines = []
    
    lines.append("=" * 80)
    lines.append("SORT-BUDDY CLASSIFICATION ANALYTICS REPORT")
    lines.append("=" * 80)
    lines.append("")
    
    # Summary
    lines.append("SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Total messages processed: {analysis['total']}")
    lines.append("")
    
    # Messages per account
    lines.append("MESSAGES PER ACCOUNT")
    lines.append("-" * 80)
    for account, count in sorted(analysis['messages_per_account'].items()):
        lines.append(f"  {account}: {count}")
    lines.append("")
    
    # Messages per folder
    lines.append("MESSAGES PER CLASSIFIED FOLDER")
    lines.append("-" * 80)
    for folder, count in sorted(analysis['messages_per_folder'].items(), key=lambda x: x[1], reverse=True):
        lines.append(f"  {folder}: {count}")
    lines.append("")
    
    # Messages per model and mode
    lines.append("MESSAGES PER MODEL AND MODE")
    lines.append("-" * 80)
    for model_mode, count in sorted(analysis['messages_per_model_mode'].items(), key=lambda x: x[1], reverse=True):
        lines.append(f"  {model_mode}: {count}")
    lines.append("")
    
    # Top 20 sender domains per folder
    lines.append("TOP 20 SENDER DOMAINS PER FOLDER")
    lines.append("-" * 80)
    for folder, domains in sorted(analysis['top_domains_per_folder'].items()):
        lines.append(f"  {folder}:")
        for domain, count in domains[:20]:
            lines.append(f"    {domain}: {count}")
    lines.append("")
    
    # Classifications by hour
    if analysis['classifications_by_hour']:
        lines.append("CLASSIFICATIONS BY HOUR OF DAY")
        lines.append("-" * 80)
        for hour in sorted(analysis['classifications_by_hour'].keys()):
            count = analysis['classifications_by_hour'][hour]
            lines.append(f"  {hour:02d}:00: {count}")
        lines.append("")
    
    # Feedback analysis
    if feedback_analysis and feedback_analysis['total'] > 0:
        lines.append("FEEDBACK CORRECTION SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total corrections: {feedback_analysis['total']}")
        for correction, count in sorted(feedback_analysis['corrections'].items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {correction}: {count}")
        lines.append("")
    
    # Potential issues
    lines.append("POTENTIAL ISSUES (HEURISTIC FLAGS)")
    lines.append("-" * 80)
    
    automated_issues = issues.get('automated_in_important_personal', [])
    if automated_issues:
        lines.append(f"Automated senders in Important/Personal ({len(automated_issues)} found):")
        for issue in automated_issues[:10]:  # Show first 10
            lines.append(f"  - From: {issue['from'][:60]}...")
            lines.append(f"    Subject: {issue['subject'][:60]}...")
            lines.append(f"    Folder: {issue['folder']}, Keyword: {issue['keyword']}")
        if len(automated_issues) > 10:
            lines.append(f"  ... and {len(automated_issues) - 10} more")
        lines.append("")
    
    urgent_issues = issues.get('urgent_in_newsletters_personal', [])
    if urgent_issues:
        lines.append(f"Urgent subjects in Newsletters/Personal ({len(urgent_issues)} found):")
        for issue in urgent_issues[:10]:
            lines.append(f"  - From: {issue['from'][:60]}...")
            lines.append(f"    Subject: {issue['subject'][:60]}...")
            lines.append(f"    Folder: {issue['folder']}, Keyword: {issue['keyword']}")
        if len(urgent_issues) > 10:
            lines.append(f"  ... and {len(urgent_issues) - 10} more")
        lines.append("")
    
    promotional_issues = issues.get('promotional_in_important_personal', [])
    if promotional_issues:
        lines.append(f"Promotional content in Important/Personal ({len(promotional_issues)} found):")
        for issue in promotional_issues[:10]:
            lines.append(f"  - From: {issue['from'][:60]}...")
            lines.append(f"    Subject: {issue['subject'][:60]}...")
            lines.append(f"    Folder: {issue['folder']}, Keyword: {issue['keyword']}")
        if len(promotional_issues) > 10:
            lines.append(f"  ... and {len(promotional_issues) - 10} more")
        lines.append("")
    
    if not any(issues.values()):
        lines.append("No potential issues found based on heuristics.")
        lines.append("")
    
    # Recommendations
    lines.append("RECOMMENDATIONS")
    lines.append("-" * 80)
    for i, rec in enumerate(recommendations, 1):
        lines.append(f"{i}. {rec}")
    lines.append("")
    
    lines.append("=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze sort-buddy classification history and feedback"
    )
    parser.add_argument(
        '--history-file',
        default=os.path.expanduser('~/.sort-buddy-history.jsonl'),
        help='Path to history JSONL file (default: ~/.sort-buddy-history.jsonl)'
    )
    parser.add_argument(
        '--feedback-file',
        default=os.path.expanduser('~/.sort-buddy-feedback.jsonl'),
        help='Path to feedback JSONL file (default: ~/.sort-buddy-feedback.jsonl)'
    )
    parser.add_argument(
        '--output',
        default='/tmp/sort-analytics-report.txt',
        help='Output report path (default: /tmp/sort-analytics-report.txt)'
    )
    parser.add_argument(
        '--print',
        action='store_true',
        help='Print report to stdout in addition to saving to file'
    )
    
    args = parser.parse_args()
    
    # Load history
    if not os.path.exists(args.history_file):
        print(f"No history file found: {args.history_file}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading history from: {args.history_file}")
    history = load_jsonl(args.history_file)
    
    if not history:
        print("No records found in history file.", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loaded {len(history)} history records")
    
    # Load feedback
    feedback_analysis = None
    if os.path.exists(args.feedback_file):
        print(f"Loading feedback from: {args.feedback_file}")
        feedback = load_jsonl(args.feedback_file)
        print(f"Loaded {len(feedback)} feedback records")
        feedback_analysis = analyze_feedback(feedback)
    else:
        print(f"No feedback file found: {args.feedback_file}")
    
    # Analyze history
    print("Analyzing history...")
    analysis = analyze_history(history)
    
    # Find potential issues
    print("Finding potential issues...")
    issues = find_potential_issues(history)
    
    # Generate recommendations
    print("Generating recommendations...")
    recommendations = generate_recommendations(analysis, feedback_analysis, issues)
    
    # Format report
    print("Formatting report...")
    report = format_report(analysis, feedback_analysis, issues, recommendations)
    
    # Save report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Report saved to: {args.output}")
    
    if args.print:
        print("\n" + report)
    
    print("Analysis complete.")


if __name__ == '__main__':
    main()
