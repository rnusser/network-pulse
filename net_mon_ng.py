import subprocess
import json
import re
import sys
from flask import Flask, jsonify

app = Flask(__name__)

# The HTML/React Dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Network Pulse v2.0</title>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #05070a; color: white; font-family: ui-sans-serif, system-ui, sans-serif; }
        .glass { background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); }
        .bar-transition { transition: height 0.4s ease-out; }
    </style>
</head>
<body>
    <div id="root"></div>

    <script type="text/babel">
        const { useState, useEffect } = React;

        const App = () => {
            const [stats, setStats] = useState({ 
                ssid: 'Scanning...', signal: 0, localPing: 0, webPing: 0, diff: 0, gateway: '192.168.0.1'
            });
            
            const [history, setHistory] = useState({
                signal: Array(40).fill(0),
                local: Array(40).fill(0),
                web: Array(40).fill(0),
                diff: Array(40).fill(0)
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

                    const diffVal = Math.max(0, data.webPing - data.localPing);
                    setStats({ ssid: currentSsid, signal: currentSignal, localPing: data.localPing, webPing: data.webPing, diff: diffVal, gateway: data.gateway });
                    setIsLive(true);
                    
                    setHistory(prev => ({
                        signal: [currentSignal, ...prev.signal].slice(0, 40),
                        local: [data.localPing, ...prev.local].slice(0, 40),
                        web: [data.webPing, ...prev.web].slice(0, 40),
                        diff: [diffVal, ...prev.diff].slice(0, 40)
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
                <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-6 pb-12">
                    <div className="flex justify-between items-center bg-slate-900/40 p-4 rounded-2xl border border-white/5">
                        <div>
                            <h1 className="text-xl font-black tracking-tighter uppercase italic text-blue-500">
                                Network Pulse <span className="text-white opacity-50 text-xs not-italic ml-2">v2.1 Stable</span>
                            </h1>
                            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Gateway: {stats.gateway} & Google DNS</p>
                        </div>
                        <div className={`px-3 py-1 rounded-full flex items-center gap-2 ${isLive ? 'bg-emerald-500/20' : 'bg-red-500/20'}`}>
                            <div className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></div>
                            <span className="text-[10px] font-bold uppercase text-slate-300">{isLive ? 'Active' : 'Syncing...'}</span>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div className="space-y-4">
                            <div className="glass rounded-3xl p-6 border-blue-500/20">
                                <p className="text-[10px] font-black text-blue-400 uppercase tracking-widest mb-1">Wi-Fi Signal</p>
                                <div className="flex items-baseline gap-2">
                                    <span className="text-5xl font-black">{stats.signal}</span>
                                    <span className="text-xl font-bold opacity-20">%</span>
                                </div>
                                <p className="text-[10px] text-slate-500 truncate mt-1 italic">{stats.ssid}</p>
                            </div>
                            <div className="glass rounded-3xl p-6 border-emerald-500/20">
                                <p className="text-[10px] font-black text-emerald-400 uppercase tracking-widest mb-1">Local (ms)</p>
                                <div className="flex items-baseline gap-2">
                                    <span className={`text-5xl font-black ${getPingColor(stats.localPing, 20)}`}>{stats.localPing >= 999 ? '!!' : stats.localPing}</span>
                                </div>
                            </div>
                            <div className="glass rounded-3xl p-6 border-purple-500/20">
                                <p className="text-[10px] font-black text-purple-400 uppercase tracking-widest mb-1">Web (ms)</p>
                                <div className="flex items-baseline gap-2">
                                    <span className={`text-5xl font-black ${getPingColor(stats.webPing, 60)}`}>{stats.webPing >= 999 ? '!!' : stats.webPing}</span>
                                </div>
                            </div>
                        </div>

                        <div className="lg:col-span-2 space-y-6">
                            <div className="glass rounded-3xl p-6">
                                <div className="flex justify-between items-center mb-4">
                                    <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400">Response Comparison</h3>
                                    <div className="flex gap-4">
                                        <div className="flex items-center gap-1.5 text-[9px] font-bold text-emerald-400"><div className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></div> LOCAL</div>
                                        <div className="flex items-center gap-1.5 text-[9px] font-bold text-purple-400"><div className="w-1.5 h-1.5 bg-purple-500 rounded-full"></div> WEB</div>
                                    </div>
                                </div>
                                <div className="h-32 flex items-end gap-1">
                                    {[...history.web].reverse().map((val, i) => (
                                        <div key={i} className="flex-1 h-full flex flex-col justify-end gap-0.5">
                                            <div className="w-full bg-purple-500/40 rounded-t-[1px] bar-transition" style={{ height: `${Math.min((val/200)*100, 100)}%` }}></div>
                                            <div className="w-full bg-emerald-500/60 rounded-t-[1px] bar-transition" style={{ height: `${Math.min(([...history.local].reverse()[i] || 0)/200)*100, 100)}%` }}></div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="glass rounded-3xl p-6"><h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4">Signal History</h3><div className="h-20 flex items-end gap-1">{[...history.signal].reverse().map((val, i) => (<div key={i} className="flex-1 bg-blue-500/30 rounded-t-sm" style={{ height: `${val}%` }}></div>))}</div></div>
                                <div className="glass rounded-3xl p-6 border-yellow-500/10"><h3 className="text-[10px] font-black uppercase tracking-widest text-yellow-500/50 mb-4">ISP Delay</h3><div className="h-20 flex items-end gap-1">{[...history.diff].reverse().map((val, i) => (<div key={i} className="flex-1 bg-yellow-500/40 rounded-t-sm" style={{ height: `${Math.min((val/150)*100, 100)}%` }}></div>))}</div></div>
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

def get_ping(host):
    try:
        cmd = f"ping -n 1 -w 800 {host}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        match = re.search(r"time[=<]([\d]+)ms", result.stdout, re.IGNORECASE)
        if match: return int(match.group(1))
        if "<1ms" in result.stdout: return 1
        return 999
    except:
        return 999

@app.route('/stats')
def get_stats():
    try:
        gateway = "192.168.0.1"
        local_p = get_ping(gateway)
        web_p = get_ping("8.8.8.8")
        wifi_data = subprocess.check_output("netsh wlan show interfaces", shell=True).decode('utf-8')
        return jsonify({"raw": wifi_data, "localPing": local_p, "webPing": web_p, "gateway": gateway})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/')
def home():
    return DASHBOARD_HTML

if __name__ == '__main__':
    try:
        print("--- MONITOR V2.1 STARTED ---")
        print("Open: http://127.0.0.1:5001")
        # Added port 5001 in case 5000 is stuck/blocked
        app.run(port=5001, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Server failed to start: {e}")




