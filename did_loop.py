#!/usr/bin/env python3
"""
DID Reputation Checker - Continuous Loop Mode
Runs the scraper repeatedly until user exits.
"""

import subprocess
import sys
from rich.console import Console

console = Console()

def main():
    console.print("[bold cyan]DID Reputation Checker - Continuous Mode[/bold cyan]")
    console.print("Press Ctrl+C to exit at any time.\n")
    
    while True:
        console.print("[yellow]--- New Session ---[/yellow]")
        # Run the main CLI script
        result = subprocess.run([sys.executable, "did_cli.py"] + sys.argv[1:])
        
        if result.returncode != 0:
            console.print("[red]Scraper exited with error. Restarting in 5 seconds...[/red]")
            import time
            time.sleep(5)
        else:
            console.print("[green]Session completed. Starting new session in 3 seconds...[/green]")
            import time
            time.sleep(3)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Exiting continuous mode. Goodbye![/yellow]")
        sys.exit(0)