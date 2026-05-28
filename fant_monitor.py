import subprocess
import json
import re
import csv
import os
from datetime import datetime
from flask import Flask, jsonify

app = Flask(__name__)

# The HTML/React Dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Network Diagnostics Pro</title>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #05070a; color: white; font-family: ui-sans-serif, system-ui, sans-serif; }
        .glass { background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); }
        .stat-card { transition: all 0.3s ease; }
        .stat-card:hover { border-color: rgba(255, 255, 255, 0.2); transform: translateY(-2px); }
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
                localPing: 0,
                webPing: 0,
                diff: 0,
                gateway: '192.168.0.1'
            });
            
            const [history, setHistory] = useState({
                signal: [],
                local: [],
                web: [],
                diff: []
            });
            const [isLive, setIsLive] = useState(false);

            const fetchData = async () => {
                try {
                    const res = await fetch('/stats');
                    const data = await res.json();
                    
                    if (data.error) throw new Error(data.error);

                    const lines = data.raw.split('\\n');
                    let currentSsid = 'Unknown';
                    let currentSignal = 0;
                    
                    lines.forEach(line => {
                        if (line.includes('SSID')) currentSsid = line.split(':')[1]?.trim() || 'Unknown';
                        if (line.includes('Signal')) currentSignal = parseInt(line.split(':')[1]?.replace('%', '').trim()) || 0;
                    });

                    const diff = Math.max(0, data.webPing - data.localPing);

                    setStats({
                        ssid: currentSsid,
                        signal: currentSignal,
                        localPing: data.localPing,
                        webPing: data.webPing,
                        diff: diff,
                        gateway: data.gateway
                    });

                    setIsLive(true);
                    
                    setHistory(prev => ({
                        signal: [currentSignal, ...prev.signal].slice(0, 40),
                        local: [data.localPing, ...prev.local].slice(0, 40),
                        web: [data.webPing, ...prev.web].slice(0, 40),
                        diff: [diff, ...prev.diff].slice(0, 40)
                    }));
                } catch (e) {
                    setIsLive(false);
                }
            };

            useEffect(() => {
                const interval = setInterval(fetchData, 2000);
                fetchData();
                return () => clearInterval(interval);
            }, []);

            const getPingColor = (p, limit = 50) => {
                if (p >= 999) return 'text-red-800';
                if (p < limit) return 'text-emerald-400';
                if (p < limit * 2) return 'text-yellow-400';
                return 'text-red-500';
            };

            return (
                <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-6">
                    {/* Header */}
                    <div className="flex justify-between items-end">
                        <div>
                            <h1 className="text-3xl font-black tracking-tighter uppercase italic">
                                Network <span className="text-blue-500 underline decoration-4 underline-offset-8">Analyzer</span>
                            </h1>
                            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-[0.3em] mt-3">
                                Monitoring Local ({stats.gateway}) & Global (8.8.8.8)
                            </p>
                        </div>
                        <div className={`px-4 py-2 rounded-2xl border border-white/5 flex items-center gap-3 ${isLive ? 'bg-emerald-500/5' : 'bg-red-500/5'}`}>
                            <div className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></div>
                            <span className="text-xs font-black uppercase text-slate-300 tracking-widest">
                                {isLive ? 'Live Sync' : 'Offline'}
                            </span>
                        </div>
                    </div>

                    {/* Top Stats Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="glass stat-card rounded-[2.5rem] p-8 border-blue-500/10">
                            <p className="text-[10px] font-black text-blue-400 uppercase tracking-widest mb-2">Wi-Fi Signal</p>
                            <h2 className="text-2xl font-bold truncate mb-4">{stats.ssid}</h2>
                            <div className="flex items-baseline gap-2">
                                <span className="text-7xl font-black tracking-tighter">{stats.signal}</span>
                                <span className="text-xl font-bold opacity-20">%</span>
                            </div>
                        </div>

                        <div className="glass stat-card rounded-[2.5rem] p-8 border-emerald-500/10">
                            <p className="text-[10px] font-black text-emerald-400 uppercase tracking-widest mb-2">Home Latency</p>
                            <h2 className="text-2xl font-bold truncate mb-4">Local Router</h2>
                            <div className="flex items-baseline gap-2">
                                <span className={`text-7xl font-black tracking-tighter ${getPingColor(stats.localPing, 20)}`}>
                                    {stats.localPing >= 999 ? '!!' : stats.localPing}
                                </span>
                                <span className="text-xl font-bold opacity-20">ms</span>
                            </div>
                        </div>

                        <div className="glass stat-card rounded-[2.5rem] p-8 border-purple-500/10">
                            <p className="text-[10px] font-black text-purple-400 uppercase tracking-widest mb-2">Web Latency</p>
                            <h2 className="text-2xl font-bold truncate mb-4">Google (8.8.8.8)</h2>
                            <div className="flex items-baseline gap-2">
                                <span className={`text-7xl font-black tracking-tighter ${getPingColor(stats.webPing, 60)}`}>
                                    {stats.webPing >= 999 ? '!!' : stats.webPing}
                                </span>
                                <span className="text-xl font-bold opacity-20">ms</span>
                            </div>
                        </div>
                    </div>

                    {/* Graphs Section */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Signal Strength Graph */}
                        <div className="glass rounded-[2rem] p-8">
                            <div className="flex justify-between items-center mb-6">
                                <h3 className="text-xs font-black uppercase tracking-widest text-slate-400">Wi-Fi Stability</h3>
                                <span className="text-[10px] font-mono bg-blue-500/10 text-blue-400 px-2 py-1 rounded">Signal %</span>
                            </div>
                            <div className="h-32 flex items-end gap-1">
                                {[...history.signal].reverse().map((val, i) => (
                                    <div key={i} className="flex-1 bg-blue-500/40 rounded-t-sm" style={{ height: `${val}%` }}></div>
                                ))}
                            </div>
                        </div>

                        {/* ISP Difference Graph */}
                        <div className="glass rounded-[2rem] p-8 border-yellow-500/10">
                            <div className="flex justify-between items-center mb-6">
                                <h3 className="text-xs font-black uppercase tracking-widest text-slate-400">Internet Overhead (Web - Local)</h3>
                                <span className="text-[10px] font-mono bg-yellow-500/10 text-yellow-400 px-2 py-1 rounded">ISP Delay</span>
                            </div>
                            <div className="h-32 flex items-end gap-1">
                                {[...history.diff].reverse().map((val, i) => (
                                    <div key={i} className="flex-1 bg-yellow-500/40 rounded-t-sm" style={{ height: `${Math.min(val, 100)}%` }}></div>
                                ))}
                            </div>
                        </div>

                        {/* Multi-Ping Tracker */}
                        <div className="lg:col-span-2 glass rounded-[2rem] p-8">
                             <div className="flex justify-between items-center mb-6">
                                <h3 className="text-xs font-black uppercase tracking-widest text-slate-400">Response Comparison</h3>
                                <div className="flex gap-4">
                                    <div className="flex items-center gap-2"><div className="w-2 h-2 bg-emerald-500 rounded-full"></div><span className="text-[10px] font-bold uppercase opacity-50">Local</span></div>
                                    <div className="flex items-center gap-2"><div className="w-2 h-2 bg-purple-500 rounded-full"></div><span className="text-[10px] font-bold uppercase opacity-50">Web</span></div>
                                </div>
                            </div>
                            <div className="h-40 flex items-end gap-1 relative border-b border-white/5">
                                {[...history.web].reverse().map((val, i) => {
                                    const localVal = [...history.local].reverse()[i] || 0;
                                    return (
                                        <div key={i} className="flex-1 h-full flex flex-col justify-end gap-0.5">
                                            <div className="w-full bg-purple-500/60 rounded-t-sm" style={{ height: `${Math.min(val/2, 100)}%` }}></div>
                                            <div className="w-full bg-emerald-500/60 rounded-t-sm" style={{ height: `${Math.min(localVal/2, 100)}%` }}></div>
                                        </div>
                                    );
                                })}
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

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"pulse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

with open(LOG_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp", "ssid", "signal_pct", "local_ping_ms", "web_ping_ms", "isp_overhead_ms"])

def parse_wifi(raw):
    ssid, signal = "Unknown", 0
    for line in raw.split('\n'):
        if line.strip().startswith('SSID'):
            parts = line.split(':')
            if len(parts) > 1:
                ssid = parts[1].strip()
        if 'Signal' in line:
            parts = line.split(':')
            if len(parts) > 1:
                try:
                    signal = int(parts[1].replace('%', '').strip())
                except:
                    pass
    return ssid, signal

def get_ping(host):
    """Pings the host and returns latency in ms."""
    try:
        # Use a short timeout of 800ms to keep the UI snappy
        cmd = f"ping -n 1 -w 800 {host}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        output = result.stdout
        
        match = re.search(r"time[=<]([\d]+)ms", output, re.IGNORECASE)
        if match:
            return int(match.group(1))
        if "<1ms" in output:
            return 1
        return 999
    except:
        return 999

@app.route('/')
def home():
    return DASHBOARD_HTML

@app.route('/stats')
def get_stats():
    try:
        # Pinging both targets
        gateway = "192.168.0.1"
        local_p = get_ping(gateway)
        web_p = get_ping("8.8.8.8")
        
        wifi_data = subprocess.check_output("netsh wlan show interfaces", shell=True).decode('utf-8')
        
        # Log to CSV
        ssid, signal = parse_wifi(wifi_data)
        diff = max(0, web_p - local_p)
        try:
            with open(LOG_FILE, 'a', newline='') as f:
                csv.writer(f).writerow([datetime.now().isoformat(), ssid, signal, local_p, web_p, diff])
        except Exception:
            pass  # Don't break the UI if logging fails
        
        return jsonify({
            "raw": wifi_data,
            "localPing": local_p,
            "webPing": web_p,
            "gateway": gateway
        })
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    print("--- FULL DIAGNOSTIC SERVER STARTED ---")
    print(f"Open: http://127.0.0.1:5000")
    print(f"Logging to: {LOG_FILE}")
    print("--- Data logs every 2s. Press Ctrl+C to stop. ---")
    app.run(port=5000, debug=False, use_reloader=False)

