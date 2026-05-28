
import subprocess
import json
import re
import platform
from flask import Flask, jsonify

app = Flask(__name__)

# The HTML/React Dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WiFi & Ping Monitor Pro</title>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #05070a; color: white; font-family: ui-sans-serif, system-ui, sans-serif; }
        .glass { background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); }
    </style>
</head>
<body>
    <div id="root"></div>

    <script type="text/babel">
        const { useState, useEffect } = React;

        const App = () => {
            const [stats, setStats] = useState({
                ssid: 'Scanning...',
                signal: 0,
                ping: 0,
                gateway: 'Detecting...'
            });
            const [signalHistory, setSignalHistory] = useState([]);
            const [pingHistory, setPingHistory] = useState([]);
            const [isLive, setIsLive] = useState(false);

            const fetchData = async () => {
                try {
                    const res = await fetch('/stats');
                    const data = await res.json();

                    if (data.error) throw new Error(data.error);

                    const lines = data.raw.split('\\n');
                    const newStats = { ...stats, ping: data.ping, gateway: data.gateway };

                    lines.forEach(line => {
                        if (line.includes('SSID')) newStats.ssid = line.split(':')[1]?.trim() || 'Unknown';
                        if (line.includes('Signal')) newStats.signal = parseInt(line.split(':')[1]?.replace('%', '').trim()) || 0;
                    });

                    setStats(newStats);
                    setIsLive(true);
                    setSignalHistory(prev => [newStats.signal, ...prev].slice(0, 40));
                    setPingHistory(prev => [data.ping, ...prev].slice(0, 40));
                } catch (e) {
                    setIsLive(false);
                }
            };

            useEffect(() => {
                const interval = setInterval(fetchData, 2000);
                fetchData();
                return () => clearInterval(interval);
            }, []);

            const getPingColor = (p) => {
                if (p === 999) return 'text-red-800';
                if (p < 20) return 'text-cyan-400';
                if (p < 50) return 'text-emerald-400';
                if (p < 150) return 'text-yellow-400';
                return 'text-red-500';
            };

            const getPingBarColor = (p) => {
                if (p === 999) return 'bg-red-900';
                if (p < 20) return 'bg-cyan-500';
                if (p < 50) return 'bg-emerald-500';
                if (p < 150) return 'bg-yellow-500';
                return 'bg-red-500';
            };

            return (
                <div className="p-4 md:p-8 max-w-5xl mx-auto space-y-6">
                    <div className="flex justify-between items-center">
                        <div>
                            <h1 className="text-2xl font-black italic tracking-tighter uppercase">
                                Network <span className="text-blue-500">Pulse</span>
                            </h1>
                            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">
                                Target: {stats.gateway}
                            </p>
                        </div>
                        <div className={`px-3 py-1 rounded-full border border-white/5 flex items-center gap-2 ${isLive ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
                            <div className={`w-2 h-2 rounded-full ${isLive ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                            <span className="text-[10px] font-bold uppercase text-slate-300">
                                {isLive ? 'Connected' : 'Bridge Offline'}
                            </span>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="glass rounded-[2.5rem] p-8">
                            <p className="text-[10px] font-bold text-blue-400 uppercase tracking-[0.2em] mb-1">WiFi Strength</p>
                            <h2 className="text-3xl font-black mb-6 truncate">{stats.ssid}</h2>
                            <div className="flex items-baseline gap-2">
                                <span className="text-8xl font-black tracking-tighter">{stats.signal}</span>
                                <span className="text-2xl font-bold opacity-20">%</span>
                            </div>
                        </div>

                        <div className="glass rounded-[2.5rem] p-8">
                            <p className="text-[10px] font-bold text-purple-400 uppercase tracking-[0.2em] mb-1">Router Ping</p>
                            <h2 className="text-3xl font-black mb-6 italic text-slate-300">Latency</h2>
                            <div className="flex items-baseline gap-2">
                                <span className={`text-8xl font-black tracking-tighter ${getPingColor(stats.ping)}`}>
                                    {stats.ping === 999 ? '!!' : stats.ping}
                                </span>
                                <span className="text-2xl font-bold opacity-20">{stats.ping === 999 ? 'ERR' : 'ms'}</span>
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="glass rounded-[2rem] p-6">
                            <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-4 text-center">Signal History</h3>
                            <div className="h-24 flex items-end gap-1 px-2">
                                {[...signalHistory].reverse().map((val, i) => (
                                    <div
                                        key={i}
                                        className="flex-1 bg-blue-500/30 rounded-t-sm"
                                        style={{ height: `${val}%` }}
                                    ></div>
                                ))}
                            </div>
                        </div>

                        <div className="glass rounded-[2rem] p-6">
                            <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-4 text-center">Latency Stability</h3>
                            <div className="h-24 flex items-end gap-1 px-2">
                                {[...pingHistory].reverse().map((val, i) => (
                                    <div
                                        key={i}
                                        className={`flex-1 rounded-t-sm transition-all duration-500 ${getPingBarColor(val)} opacity-40`}
                                        style={{ height: `${Math.min((val/200)*100, 100)}%` }}
                                    ></div>
                                ))}
                            </div>
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

def get_gateway():
    """Finds the router's IP address (Default Gateway) for Windows."""
    return "192.168.0.1"

def get_ping(host):
    """Pings the host and returns ms as an integer, with terminal debug info."""
    try:
        print(f"[DEBUG] Attempting to ping: {host}")

        # Use -n 1 for one packet, -w 1000 for a 1s timeout
        output = subprocess.check_output(f"ping -n 1 -w 1000 {host}", shell=True).decode('utf-8')

        # Print the raw output to terminal for debugging
        print(f"[DEBUG] Raw Ping Output: {output.strip()}")

        # Search for time=Xms or time<1ms (case insensitive)
        match = re.search(r"time[=<]([\d]+)ms", output, re.IGNORECASE)
        if match:
            val = int(match.group(1))
            print(f"[DEBUG] Parsed Ping: {val}ms")
            return val

        if "<1ms" in output:
            print(f"[DEBUG] Parsed Ping: <1ms (returning 1)")
            return 1

        print("[DEBUG] Regex failed to find time in output.")
        return 999
    except Exception as e:
        print(f"[DEBUG] Ping Exception: {e}")
        return 999

@app.route('/')
def home():
    return DASHBOARD_HTML

@app.route('/stats')
def get_stats():
    try:
        gateway = get_gateway()
        ping_val = get_ping(gateway)
        wifi_data = subprocess.check_output("netsh wlan show interfaces", shell=True).decode('utf-8')

        return jsonify({
            "raw": wifi_data,
            "ping": ping_val,
            "gateway": gateway
        })
    except Exception as e:
        print(f"[DEBUG] Stats Error: {e}")
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    print("--- MONITOR SERVER STARTED ---")
    print("Go to: http://127.0.0.1:5000")
    print("Check this terminal for [DEBUG] messages!")
    app.run(port=5000, debug=False)

