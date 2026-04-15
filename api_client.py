#!/usr/bin/env python3
"""
DID Reputation API Client
Sends phone numbers to the API server and displays results.
"""

import sys
import json
import argparse
import requests
from pathlib import Path
from typing import List, Dict, Optional

# Optional: rich for pretty output (install with `pip install rich`)
try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Fallback to simple print
    Console = None

console = Console() if RICH_AVAILABLE else None

# ----------------------------------------------------------------------
# Helper: Parse numbers (same as did_cli.py)
# ----------------------------------------------------------------------
def clean_number(number) -> str:
    """Extract 10-digit phone number."""
    if not number or not isinstance(number, (str, int)):
        return ""
    cleaned = ''.join(filter(str.isdigit, str(number)))
    if cleaned.startswith('1') and len(cleaned) == 11:
        cleaned = cleaned[1:]
    return cleaned if len(cleaned) == 10 else ""


def parse_numbers(input_source: str, input_file: Optional[str]) -> List[str]:
    """Parse numbers from command line argument or file."""
    numbers = []
    if input_source:
        raw = input_source.replace(',', ' ').replace(';', ' ')
        for part in raw.split():
            cleaned = clean_number(part)
            if cleaned:
                numbers.append(cleaned)
    if input_file:
        path = Path(input_file)
        if not path.exists():
            print(f"Error: File '{input_file}' not found.")
            sys.exit(1)
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                first_col = line.split(',')[0].strip().strip('"').strip("'")
                cleaned = clean_number(first_col)
                if cleaned:
                    numbers.append(cleaned)
    if not numbers and not input_source and not input_file:
        print("Enter phone numbers (one per line, comma/space separated). Press Enter twice when done:")
        lines = []
        while True:
            line = sys.stdin.readline()
            if not line or line.strip() == "":
                break
            lines.append(line.strip())
        raw = "\n".join(lines)
        numbers = []
        for part in raw.replace(',', ' ').replace(';', ' ').split():
            cleaned = clean_number(part)
            if cleaned:
                numbers.append(cleaned)
    # Remove duplicates
    seen = set()
    unique = []
    for n in numbers:
        if n not in seen:
            seen.add(n)
            unique.append(n)
    return unique


# ----------------------------------------------------------------------
# API client
# ----------------------------------------------------------------------
def call_api(api_url: str, numbers: List[str]) -> Optional[List[Dict]]:
    """Send numbers to API and return results."""
    payload = {"numbers": numbers}
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            disable=not RICH_AVAILABLE,
        ) as progress:
            task = progress.add_task("[cyan]Sending request...", total=None)
            response = requests.post(api_url, json=payload, timeout=60)
            progress.update(task, completed=True)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print(f"Error: Cannot connect to API at {api_url}. Is the server running?")
        return None
    except requests.exceptions.Timeout:
        print("Error: Request timed out.")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e}")
        if response.status_code == 400:
            print("Invalid request. Check your numbers.")
        elif response.status_code == 500:
            print("Server error. Check API logs.")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


def display_results(results: List[Dict]):
    """Print results in a readable format."""
    if not results:
        print("No results returned.")
        return

    if RICH_AVAILABLE and console:
        table = Table(title="DID Reputation Results", show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Phone Number", style="cyan")
        table.add_column("Reputation", style="green")
        table.add_column("Robokiller", style="blue")
        table.add_column("User Reports", justify="right")
        table.add_column("Total Calls", justify="right")
        table.add_column("Last Call")

        for idx, res in enumerate(results, 1):
            rep = res.get('reputation', 'Unknown')
            if rep == 'Positive':
                rep_display = f"[green]✓ {rep}[/green]"
            elif rep == 'Negative':
                rep_display = f"[red]✗ {rep}[/red]"
            elif rep == 'Blocked':
                rep_display = f"[red]🚫 {rep}[/red]"
            else:
                rep_display = f"[yellow]? {rep}[/yellow]"

            rk_status = res.get('robokiller_status', '')
            if rk_status == 'Allowed':
                rk_display = f"[green]{rk_status}[/green]"
            elif rk_status == 'Blocked':
                rk_display = f"[red]{rk_status}[/red]"
            else:
                rk_display = rk_status or 'N/A'

            table.add_row(
                str(idx),
                res['phone_number'],
                rep_display,
                rk_display,
                res.get('user_reports', '0'),
                res.get('total_calls', '0'),
                res.get('last_call', 'N/A')
            )
        console.print(table)
    else:
        # Simple JSON output
        print(json.dumps(results, indent=2))


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Client for DID Reputation API")
    parser.add_argument("-n", "--numbers", help="Phone numbers (comma/space separated)")
    parser.add_argument("-f", "--file", help="Input file (CSV or text)")
    parser.add_argument("-u", "--url", default="http://localhost:5000/scrape", help="API endpoint URL")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of formatted table")
    args = parser.parse_args()

    numbers = parse_numbers(args.numbers, args.file)
    if not numbers:
        print("No valid phone numbers provided.")
        sys.exit(1)

    print(f"Sending {len(numbers)} number(s) to {args.url}...")
    results = call_api(args.url, numbers)
    if results is None:
        sys.exit(1)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        display_results(results)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)