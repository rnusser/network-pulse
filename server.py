import subprocess
import json
import time
from flask import Flask, jsonify

app = Flask(__name__)

# The HTML/React Dashboard (This is the code you saw in the browser)
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WiFi Signal Monitor Pro</title>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background-color: #05070a; color: white; font-family: sans-serif; }
        .glass { background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); }
    </style>
</head>
<body>
    <div id="root"></div>

    <script type="text/babel">
        const { useState, useEffect, useCallback } = React;

        const App = () => {
            const [stats, setStats] = useState({ ssid: 'Scanning...', signal: 0, state: 'disconnected' });
            const [history, setHistory] = useState([]);
            const [isLive, setIsLive] = useState(false);

            const fetchData = async () => {
                try {
                    const res = await fetch('/stats');
                    const data = await res.json();
                    
                    // Simple parsing for the dashboard
                    const lines = data.raw.split('\\n');
                    const newStats = { ...stats };
                    lines.forEach(line => {
                        if (line.includes('SSID')) newStats.ssid = line.split(':')[1].trim();
                        if (line.includes('Signal')) newStats.signal = parseInt(line.split(':')[1].replace('%', '').trim());
                        if (line.includes('State')) newStats.state = line.split(':')[1].trim();
                    });

                    setStats(newStats);
                    setIsLive(true);
                    setHistory(prev => [newStats.signal, ...prev].slice(0, 30));
                } catch (e) {
                    setIsLive(false);
                }
            };

            useEffect(() => {
                const interval = setInterval(fetchData, 2000);
                fetchData();
                return () => clearInterval(interval);
            }, []);

            return (
                <div className="p-8 max-w-4xl mx-auto">
                    <div className="flex justify-between items-center mb-10">
                        <h1 className="text-3xl font-black italic">WIFI <span className="text-blue-500">MONITOR</span></h1>
                        <div className="flex items-center gap-2">
                            <div className={`w-3 h-3 rounded-full ${isLive ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                            <span className="text-xs font-bold uppercase tracking-widest text-slate-400">
                                {isLive ? 'Live System Connected' : 'System Offline'}
                            </span>
                        </div>
                    </div>

                    <div className={`glass rounded-[3rem] p-12 mb-8 transition-all duration-500 ${stats.signal > 70 ? 'border-green-500/30' : 'border-yellow-500/30'}`}>
                        <p className="text-xs font-bold text-blue-400 uppercase tracking-widest mb-2">Current Network</p>
                        <h2 className="text-5xl font-black mb-8">{stats.ssid}</h2>
                        
                        <div className="flex items-baseline gap-4">
                            <span className="text-[12rem] font-black leading-none">{stats.signal}</span>
                            <span className="text-4xl font-bold opacity-20">%</span>
                        </div>

                        <div className="w-full h-4 bg-slate-900 rounded-full mt-6 overflow-hidden">
                            <div 
                                className="h-full bg-blue-500 transition-all duration-1000" 
                                style={{ width: `${stats.signal}%` }}
                            ></div>
                        </div>
                    </div>

                    <div className="glass rounded-[2rem] p-8">
                        <h3 className="text-sm font-bold uppercase tracking-widest text-slate-500 mb-6">Signal History</h3>
                        <div className="h-32 flex items-end gap-1">
                            {history.map((val, i) => (
                                <div 
                                    key={i} 
                                    className="flex-1 bg-blue-500/40 rounded-t-sm" 
                                    style={{ height: `${val}%` }}
                                ></div>
                            ))}
                        </div>
                    </div>
                </div>
            );
        };

        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(<App />);
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    # This serves the actual dashboard webpage
    return DASHBOARD_HTML

@app.route('/stats')
def get_stats():
    # This provides the data the dashboard needs
    try:
        result = subprocess.check_output("netsh wlan show interfaces", shell=True).decode('utf-8')
        return jsonify({"raw": result})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    print("--- WIFI MONITOR SERVER STARTED ---")
    print("Go to: http://127.0.0.1:5000 in your browser")
    app.run(port=5000)
