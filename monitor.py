import subprocess
import json
import time
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # This allows your browser to talk to this local script safely

def get_wifi_stats():
    try:
        # Runs the windows command and captures the text output
        result = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"], 
            encoding="cp437" # Standard Windows encoding
        )
        return result
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/stats')
def stats():
    # This creates a web address at http://127.0.0.1:5000/stats
    raw_data = get_wifi_stats()
    return jsonify({"raw": raw_data})

if __name__ == '__main__':
    print("--- WiFi Bridge is starting! ---")
    print("Keep this window open.")
    print("Listening at http://127.0.0.1:5000/stats")
    app.run(port=5000)

