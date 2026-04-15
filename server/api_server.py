"""
DID Reputation Checker - Production API Server with CORS
Supports Waitress (Windows) and Gunicorn (Linux/macOS)
"""

import os
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from scraper_engine import RoboKillerScraper

app = Flask(__name__)

# Allow CORS for Chrome extension origin and localhost
CORS(app, 
     origins=["chrome-extension://*", "http://localhost:*", "http://127.0.0.1:*"],
     supports_credentials=True,
     allow_headers=["Content-Type"])

scraper = RoboKillerScraper()

@app.route('/scrape', methods=['POST'])
def scrape():
    """Scrape reputation for a list of phone numbers."""
    data = request.get_json()
    if not data or 'numbers' not in data:
        return jsonify({'error': 'Missing "numbers" field'}), 400
    numbers = data['numbers']
    if not isinstance(numbers, list):
        return jsonify({'error': 'Numbers must be a list'}), 400
    
    # Run async scraper within the request
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(scraper.scrape_async(numbers))
    finally:
        loop.close()
    
    return jsonify(results)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for load balancers."""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # Use Waitress for production (recommended for Windows)
    from waitress import serve
    host = os.environ.get('API_HOST', '0.0.0.0')
    port = int(os.environ.get('API_PORT', 5000))
    threads = int(os.environ.get('API_THREADS', 4))
    print(f"Starting Waitress server on {host}:{port} with {threads} threads")
    serve(app, host=host, port=port, threads=threads)