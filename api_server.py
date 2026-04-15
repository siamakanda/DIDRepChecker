"""
Simple Flask API for the DID Reputation Checker.
Endpoint: POST /scrape  (JSON: {"numbers": ["2125551234", ...]})
Returns: JSON array of results.
"""

import asyncio
from flask import Flask, request, jsonify
from scraper_engine import RoboKillerScraper

app = Flask(__name__)
scraper = RoboKillerScraper()

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json()
    if not data or 'numbers' not in data:
        return jsonify({'error': 'Missing "numbers" field'}), 400
    numbers = data['numbers']
    if not isinstance(numbers, list):
        return jsonify({'error': 'Numbers must be a list'}), 400
    
    # Run async scraper synchronously
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(scraper.scrape_async(numbers))
    finally:
        loop.close()
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)