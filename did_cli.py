#!/usr/bin/env python3
"""
DID Reputation Checker - Professional CLI with Real-time Stats & Retry
"""

import sys
import csv
import json
import argparse
import time
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False

from scraper_engine import scrape_numbers_sync, clean_number

console = Console()

class DIDScraperCLI:
    def __init__(self):
        self.numbers: List[str] = []
        self.results: List[Dict[str, str]] = []
        self.failed_numbers: List[str] = []
        self.stats = {"positive": 0, "negative": 0, "other": 0, "errors": 0}
        self.default_filter = "positive"
        self.default_sort = "total_calls"
        self.default_order = "asc"
        self.default_limit = "all"
    
    # ---------- Input Parsing ----------
    def parse_input(self, input_source: str, input_file: Optional[str]) -> List[str]:
        """Parse phone numbers from various sources"""
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
                console.print(f"[red]Error: File '{input_file}' not found.[/red]")
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
            console.print("[bold cyan]📋 Paste Phone Numbers[/bold cyan]")
            console.print("[dim]Supported formats: one per line, comma-separated, spaces, or mixed.[/dim]")
            console.print("[dim]Press Enter twice when done.[/dim]\n")
            lines = []
            while True:
                line = sys.stdin.readline()
                if not line or line.strip() == "":
                    break
                lines.append(line.strip())
            raw = "\n".join(lines)
            numbers = self._parse_mixed_input(raw)
        # Remove duplicates
        seen = set()
        unique = []
        for n in numbers:
            if n not in seen:
                seen.add(n)
                unique.append(n)
        if len(numbers) != len(unique):
            console.print(f"[dim]Removed {len(numbers)-len(unique)} duplicate(s).[/dim]")
        return unique
    
    def _parse_mixed_input(self, text: str) -> List[str]:
        numbers = set()
        text = text.replace(',', '\n').replace(';', '\n')
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            for part in line.split():
                cleaned = clean_number(part)
                if cleaned:
                    numbers.add(cleaned)
        return list(numbers)
    
    # ---------- Scraping with Real-time Stats ----------
    def run_scraper(self):
        """Run scraper with real-time statistics display"""
        if not self.numbers:
            console.print("[red]No numbers to scrape. Please provide input.[/red]")
            sys.exit(1)
        
        console.print(f"\n[bold]Starting Scrape[/bold]")
        console.print(f"Total numbers: {len(self.numbers)}")
        console.print(f"Concurrency: {self._get_concurrency()} | Rate limit: {self._get_rate_limit()}/s\n")
        
        # Reset stats
        self.stats = {"positive": 0, "negative": 0, "other": 0, "errors": 0}
        self.results = []
        self.failed_numbers = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        ) as progress:
            task = progress.add_task("[cyan]Processing", total=len(self.numbers))
            
            # Custom callback to update stats and progress
            async def async_progress_callback(phone_number: str, result: Dict[str, str]):
                # Update stats based on result
                rep = result.get('reputation', '')
                if rep == 'Positive':
                    self.stats['positive'] += 1
                elif rep == 'Negative':
                    self.stats['negative'] += 1
                elif rep in ('Error', 'Timeout', 'Blocked', 'HTTP 429', 'HTTP 403', 'HTTP 404', 'Parse Error'):
                    self.stats['errors'] += 1
                    self.failed_numbers.append(phone_number)
                else:
                    self.stats['other'] += 1
                
                # Update progress bar description with live stats
                progress.update(
                    task,
                    advance=1,
                    description=f"[cyan]Processing | ✅ Pos:{self.stats['positive']} ❌ Neg:{self.stats['negative']} ⚠️ Err:{self.stats['errors']}"
                )
                self.results.append(result)
                return True
            
            # Run scraper
            from scraper_engine import scrape_numbers_sync
            self.results = scrape_numbers_sync(self.numbers, async_progress_callback)
        
        # Final summary
        console.print("\n[bold green]✓ Scraping completed[/bold green]")
        self._show_summary()
    
    def _show_summary(self):
        """Display summary table"""
        table = Table(title="Scraping Summary", title_style="bold cyan")
        table.add_column("Category", style="cyan")
        table.add_column("Count", justify="right", style="green")
        table.add_column("%", justify="right", style="dim")
        
        total = len(self.results)
        pos_pct = (self.stats['positive']/total*100) if total else 0
        neg_pct = (self.stats['negative']/total*100) if total else 0
        err_pct = (self.stats['errors']/total*100) if total else 0
        other_pct = (self.stats['other']/total*100) if total else 0
        
        table.add_row("✅ Positive", str(self.stats['positive']), f"{pos_pct:.1f}%")
        table.add_row("❌ Negative", str(self.stats['negative']), f"{neg_pct:.1f}%")
        table.add_row("⚠️ Errors / Blocked", str(self.stats['errors']), f"{err_pct:.1f}%")
        table.add_row("📭 Other / No Data", str(self.stats['other']), f"{other_pct:.1f}%")
        table.add_row("📞 Total", str(total), "100%")
        console.print(table)
    
    def _get_concurrency(self) -> int:
        # Retrieve from scraper_engine config
        from scraper_engine import CONFIG
        return CONFIG.get("concurrent_requests", 30)
    
    def _get_rate_limit(self) -> float:
        from scraper_engine import CONFIG
        return CONFIG.get("requests_per_second", 5.0)
    
    # ---------- Retry Failed Numbers ----------
    def retry_failed(self):
        """Offer to retry failed numbers"""
        if not self.failed_numbers:
            console.print("[green]No failed numbers to retry.[/green]")
            return False
        
        console.print(f"\n[yellow]⚠️ {len(self.failed_numbers)} number(s) failed or returned errors.[/yellow]")
        if not Confirm.ask("Retry failed numbers?", default=True):
            return False
        
        # Backup current results
        old_results = self.results.copy()
        old_failed = self.failed_numbers.copy()
        
        # Clear stats and results for retry
        self.numbers = self.failed_numbers
        self.results = []
        self.failed_numbers = []
        self.stats = {"positive": 0, "negative": 0, "other": 0, "errors": 0}
        
        console.print(f"\n[bold]Retrying {len(self.numbers)} number(s)...[/bold]")
        self.run_scraper()
        
        # Merge results: keep old successful ones + new retry results
        # But we must avoid duplicates: old results already have the failed numbers with error status
        # We'll replace those with new results
        successful_old = [r for r in old_results if r['phone_number'] not in old_failed]
        self.results = successful_old + self.results
        # Update stats
        self.stats['positive'] = sum(1 for r in self.results if r.get('reputation') == 'Positive')
        self.stats['negative'] = sum(1 for r in self.results if r.get('reputation') == 'Negative')
        self.stats['errors'] = sum(1 for r in self.results if r.get('reputation') in ('Error', 'Timeout', 'Blocked', 'HTTP 429', 'HTTP 403', 'Parse Error'))
        self.stats['other'] = len(self.results) - self.stats['positive'] - self.stats['negative'] - self.stats['errors']
        
        console.print("\n[bold green]Retry completed. Updated summary:[/bold green]")
        self._show_summary()
        return True
    
    # ---------- Post-processing ----------
    def apply_post_processing(self):
        """Interactive post-processing with professional prompts"""
        if not self.results:
            console.print("[yellow]No results to process.[/yellow]")
            return []
        
        console.print("\n[bold cyan]📊 Post-Processing Options[/bold cyan]")
        console.print(f"[dim]Default: filter={self.default_filter}, sort={self.default_sort}, order={self.default_order}, limit={self.default_limit}[/dim]\n")
        
        filter_choice = Prompt.ask(
            "Filter by reputation",
            choices=["positive", "negative", "all"],
            default=self.default_filter
        )
        sort_by = Prompt.ask(
            "Sort field",
            choices=["total_calls", "user_reports", "last_call", "phone_number"],
            default=self.default_sort
        )
        order = Prompt.ask(
            "Sort order",
            choices=["asc", "desc"],
            default=self.default_order
        )
        limit_input = Prompt.ask(
            "Number of results (or 'all')",
            default=self.default_limit
        )
        
        # Apply filter
        if filter_choice == "positive":
            filtered = [r for r in self.results if r.get('reputation') == 'Positive']
        elif filter_choice == "negative":
            filtered = [r for r in self.results if r.get('reputation') == 'Negative']
        else:
            filtered = self.results.copy()
        
        # Sort
        reverse = (order == "desc")
        if sort_by == "total_calls":
            filtered.sort(key=lambda x: self._safe_int(x.get('total_calls', '0')), reverse=reverse)
        elif sort_by == "user_reports":
            filtered.sort(key=lambda x: self._safe_int(x.get('user_reports', '0')), reverse=reverse)
        elif sort_by == "last_call":
            filtered.sort(key=lambda x: self._safe_date(x.get('last_call', '')), reverse=reverse)
        else:
            filtered.sort(key=lambda x: x.get('phone_number', ''), reverse=reverse)
        
        # Limit
        if limit_input.lower() != "all":
            try:
                limit = int(limit_input)
                filtered = filtered[:limit]
            except ValueError:
                pass
        
        return filtered
    
    def _safe_int(self, value: str) -> int:
        try:
            return int(value) if value else 0
        except:
            return 0
    
    def _safe_date(self, date_str: str) -> str:
        import re
        match = re.search(r'(\w+)\s+(\d+),\s+(\d{4})', date_str)
        if match:
            month_name, day, year = match.groups()
            month_map = {'January':1,'February':2,'March':3,'April':4,'May':5,'June':6,'July':7,'August':8,'September':9,'October':10,'November':11,'December':12}
            month = month_map.get(month_name, 0)
            return f"{year}-{month:02d}-{int(day):02d}"
        return date_str
    
    def output_results(self, filtered_results: List[Dict[str, str]]):
        """Print DIDs and copy to clipboard"""
        if not filtered_results:
            console.print("[yellow]No results to display.[/yellow]")
            return
        
        dids = [r['phone_number'] for r in filtered_results]
        console.print(f"\n[bold]--- Extracted DIDs ({len(dids)}) ---[/bold]")
        for did in dids:
            console.print(did)
        
        if CLIPBOARD_AVAILABLE:
            try:
                pyperclip.copy("\n".join(dids))
                console.print(f"\n[green]✅ Copied {len(dids)} DID(s) to clipboard.[/green]")
            except Exception as e:
                console.print(f"[red]Clipboard error: {e}[/red]")
        else:
            console.print("[yellow]Clipboard unavailable. Install pyperclip: pip install pyperclip[/yellow]")
    
    def export_full_results(self, output_file: str, format: str = "csv"):
        """Export full results to file"""
        if not self.results:
            console.print("[yellow]No results to export.[/yellow]")
            return
        try:
            if format == "csv":
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    fieldnames = ['phone_number', 'reputation', 'robokiller_status', 'user_reports', 'total_calls', 'last_call', 'scraped_at']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for row in self.results:
                        out_row = {k: row.get(k, '') for k in fieldnames}
                        writer.writerow(out_row)
            elif format == "json":
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(self.results, f, indent=2, default=str)
            else:
                console.print(f"[red]Unsupported format: {format}[/red]")
                return
            console.print(f"[green]✓ Exported full results to {output_file}[/green]")
        except Exception as e:
            console.print(f"[red]Export failed: {e}[/red]")
    
    # ---------- Main Flow ----------
    def run(self, args):
        # Parse input
        self.numbers = self.parse_input(args.numbers, args.file)
        if not self.numbers:
            console.print("[red]No valid phone numbers provided. Exiting.[/red]")
            sys.exit(1)
        
        # Scrape
        self.run_scraper()
        
        # Offer retry if any errors
        if self.stats['errors'] > 0:
            self.retry_failed()
        
        # Post-processing (interactive unless --no-interactive)
        if not args.no_interactive:
            filtered = self.apply_post_processing()
            self.output_results(filtered)
        else:
            # Non-interactive: use flags or defaults
            filter_choice = args.filter or self.default_filter
            sort_by = args.sort or self.default_sort
            order = args.order or self.default_order
            limit_input = args.limit or self.default_limit
            
            if filter_choice == "positive":
                filtered = [r for r in self.results if r.get('reputation') == 'Positive']
            elif filter_choice == "negative":
                filtered = [r for r in self.results if r.get('reputation') == 'Negative']
            else:
                filtered = self.results.copy()
            
            reverse = (order == "desc")
            if sort_by == "total_calls":
                filtered.sort(key=lambda x: self._safe_int(x.get('total_calls', '0')), reverse=reverse)
            elif sort_by == "user_reports":
                filtered.sort(key=lambda x: self._safe_int(x.get('user_reports', '0')), reverse=reverse)
            elif sort_by == "last_call":
                filtered.sort(key=lambda x: self._safe_date(x.get('last_call', '')), reverse=reverse)
            else:
                filtered.sort(key=lambda x: x.get('phone_number', ''), reverse=reverse)
            
            if limit_input != "all":
                try:
                    limit = int(limit_input)
                    filtered = filtered[:limit]
                except:
                    pass
            self.output_results(filtered)
        
        # Export if requested
        if args.export:
            self.export_full_results(args.export, args.export_format)


def main():
    parser = argparse.ArgumentParser(
        description="DID Reputation Checker - Professional CLI",
        epilog="Examples:\n  python did_cli.py\n  python did_cli.py -f numbers.txt\n  python did_cli.py -n \"2125551234,2125555678\" --filter positive --sort total_calls --order asc --limit 70"
    )
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("-n", "--numbers", help="Phone numbers (comma/space separated)")
    input_group.add_argument("-f", "--file", help="Input file (CSV or text)")
    parser.add_argument("--no-interactive", action="store_true", help="Skip interactive post-processing prompts")
    parser.add_argument("--filter", choices=["positive", "negative", "all"], help="Filter by reputation")
    parser.add_argument("--sort", choices=["total_calls", "user_reports", "last_call", "phone_number"], help="Sort field")
    parser.add_argument("--order", choices=["asc", "desc"], help="Sort order")
    parser.add_argument("--limit", help="Number of results or 'all'")
    parser.add_argument("--export", help="Export full results to file (CSV/JSON)")
    parser.add_argument("--export-format", choices=["csv", "json"], default="csv")
    args = parser.parse_args()
    
    app = DIDScraperCLI()
    try:
        app.run(args)
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Interrupted by user. Exiting...[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()