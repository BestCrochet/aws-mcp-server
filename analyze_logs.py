#!/usr/bin/env python3
"""Example script demonstrating request logging functionality.

This script shows how to view and analyze the requests.log file.
"""

import json
from pathlib import Path


def analyze_log_file(log_file="requests.log"):
    """Analyze the request log file and display statistics.
    
    Args:
        log_file: Path to the log file
    """
    log_path = Path(log_file)
    
    if not log_path.exists():
        print(f"Log file not found: {log_file}")
        print("Run the MCP server and execute some commands to generate logs.")
        return
    
    print(f"Analyzing log file: {log_path.absolute()}\n")
    
    # Read all log entries
    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError as e:
                print(f"Warning: Invalid JSON on line {line_num}: {e}")
    
    if not entries:
        print("No valid log entries found.")
        return
    
    # Calculate statistics
    total_requests = len(entries)
    successful = sum(1 for e in entries if e.get("status") == "success")
    errors = sum(1 for e in entries if e.get("status") == "error")
    
    # Tool usage
    tools = {}
    for entry in entries:
        tool = entry.get("tool_name", "unknown")
        tools[tool] = tools.get(tool, 0) + 1
    
    # Duration statistics
    durations = [e.get("duration_ms", 0) for e in entries]
    avg_duration = sum(durations) / len(durations) if durations else 0
    max_duration = max(durations) if durations else 0
    min_duration = min(durations) if durations else 0
    
    # Display statistics
    print("=" * 60)
    print("REQUEST LOG STATISTICS")
    print("=" * 60)
    print(f"\nTotal Requests: {total_requests}")
    print(f"Successful:     {successful} ({successful/total_requests*100:.1f}%)")
    print(f"Errors:         {errors} ({errors/total_requests*100:.1f}%)")
    
    print("\n" + "-" * 60)
    print("TOOL USAGE")
    print("-" * 60)
    for tool, count in sorted(tools.items(), key=lambda x: x[1], reverse=True):
        print(f"{tool:30} {count:5} calls")
    
    print("\n" + "-" * 60)
    print("DURATION STATISTICS (milliseconds)")
    print("-" * 60)
    print(f"Average: {avg_duration:10.2f} ms")
    print(f"Maximum: {max_duration:10.2f} ms")
    print(f"Minimum: {min_duration:10.2f} ms")
    
    # Show recent requests
    print("\n" + "-" * 60)
    print("RECENT REQUESTS (last 5)")
    print("-" * 60)
    for entry in entries[-5:]:
        timestamp = entry.get("timestamp", "unknown")
        tool_name = entry.get("tool_name", "unknown")
        status = entry.get("status", "unknown")
        duration = entry.get("duration_ms", 0)
        
        status_symbol = "✓" if status == "success" else "✗"
        print(f"{status_symbol} [{timestamp}] {tool_name} - {duration:.2f}ms - {status}")
        
        # Show input command if available
        if "input" in entry and "command" in entry["input"]:
            cmd = entry["input"]["command"]
            if len(cmd) > 70:
                cmd = cmd[:67] + "..."
            print(f"  Command: {cmd}")
        
        # Show error if present
        if entry.get("error"):
            error = entry["error"]
            if len(error) > 70:
                error = error[:67] + "..."
            print(f"  Error: {error}")
        print()
    
    print("=" * 60)


def tail_log_file(log_file="requests.log", num_lines=10):
    """Display the last N lines of the log file.
    
    Args:
        log_file: Path to the log file
        num_lines: Number of lines to display
    """
    log_path = Path(log_file)
    
    if not log_path.exists():
        print(f"Log file not found: {log_file}")
        return
    
    print(f"Last {num_lines} entries from {log_path.absolute()}:\n")
    
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    for line in lines[-num_lines:]:
        try:
            entry = json.loads(line)
            print(json.dumps(entry, indent=2))
            print("-" * 60)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}")


def search_log_file(log_file="requests.log", search_term="", field=None):
    """Search the log file for specific terms.
    
    Args:
        log_file: Path to the log file
        search_term: Term to search for
        field: Specific field to search in (e.g., 'tool_name', 'status')
    """
    log_path = Path(log_file)
    
    if not log_path.exists():
        print(f"Log file not found: {log_file}")
        return
    
    print(f"Searching for '{search_term}' in {log_path.absolute()}")
    if field:
        print(f"Searching in field: {field}\n")
    
    matches = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                entry = json.loads(line)
                
                # Search in specific field or entire entry
                if field:
                    if field in entry and search_term.lower() in str(entry[field]).lower():
                        matches.append((line_num, entry))
                else:
                    if search_term.lower() in line.lower():
                        matches.append((line_num, entry))
            except json.JSONDecodeError:
                pass
    
    if not matches:
        print("No matches found.")
        return
    
    print(f"Found {len(matches)} matches:\n")
    for line_num, entry in matches[:20]:  # Limit to first 20 matches
        print(f"Line {line_num}:")
        print(json.dumps(entry, indent=2))
        print("-" * 60)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "analyze":
            log_file = sys.argv[2] if len(sys.argv) > 2 else "requests.log"
            analyze_log_file(log_file)
        elif command == "tail":
            log_file = sys.argv[2] if len(sys.argv) > 2 else "requests.log"
            num_lines = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            tail_log_file(log_file, num_lines)
        elif command == "search":
            if len(sys.argv) < 3:
                print("Usage: python analyze_logs.py search <term> [log_file] [field]")
                sys.exit(1)
            search_term = sys.argv[2]
            log_file = sys.argv[3] if len(sys.argv) > 3 else "requests.log"
            field = sys.argv[4] if len(sys.argv) > 4 else None
            search_log_file(log_file, search_term, field)
        else:
            print("Unknown command. Available commands: analyze, tail, search")
            sys.exit(1)
    else:
        # Default: analyze
        analyze_log_file()
