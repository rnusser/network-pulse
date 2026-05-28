import subprocess
import json
import re
import sys
from flask import Flask, jsonify

app = Flask(__name__)

# The HTML Dashboard - v2.8 Stable
# Added a dedicated Local Latency graph and refined layout.
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Network Pulse v2.8</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #05070a; color: white; font-family: ui-sans-serif, system-ui, sans-serif; margin: 0; padding: 0; overflow-x: hidden; }
        .glass { background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); }
        .bar { transition: height 0.4s ease-out; width: 100%; border-radius: 2px 2px 0 0; }
        .grid-container { display: grid; grid-template-columns: repeat(40, 1fr); gap: 2px; align-items: end; height: 100%; }
    </style>
</head>
<body class="p-4 md:p-8">
    <div class="max-w-6xl mx-auto space-y-6 pb-12">
        <!-- Header -->
        <div class="flex justify-between items-center bg-slate-900/60 p-5 rounded-2xl border border-white/10 shadow-2xl">
            <div>
                <h1 class="text-2xl font-black tracking-tighter uppercase italic text-blue-500">
                    Network Pulse <span class="text-white opacity-40 text-xs not-italic ml-2 tracking-normal font-medium">v2.8</span>
                </h1>
                <p class="text-[10px] text-slate-500 font-bold uppercase tracking-[0.2em] mt-1">Status: Monitoring Active</p>
            </div>
            <div id="status-badge" class="px-4 py-1.5 rounded-full flex items-center gap-2 border bg-emerald-500/10 border-emerald-500/20">
                <div id="status-dot" class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                <span id="status-text" class="text-[10px] font-black uppercase tracking-widest text-emerald-400">System Live</span>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Stats Column -->
            <div class="space-y-4">
                <div class="glass rounded-3xl p-6 border-blue-500/20">
                    <p class="text-[10px] font-black text-blue-400 uppercase tracking-widest mb-1 opacity-70">Wi-Fi Signal</p>
                    <div class="flex items-baseline gap-2">
                        <span id="stat-signal" class="text-6xl font-black tracking-tighter">0</span>
                        <span class="text-xl font-bold opacity-20">%</span>
                    </div>
                    <p id="stat-ssid" class="text-[10px] text-slate-500 truncate mt-2 font-mono italic">Scanning...</p>
                </div>
                <div class="glass rounded-3xl p-6 border-emerald-500/20">
                    <p class="text-[10px] font-black text-emerald-400 uppercase tracking-widest mb-1 opacity-70">Local Latency (Gateway)</p>
                    <div class="flex items-baseline gap-2">
                        <span id="stat-local" class="text-6xl font-black tracking-tighter text-emerald-400">0</span>
                        <span class="text-xl font-bold opacity-20">ms</span>
                    </div>
                </div>
                <div class="glass rounded-3xl p-6 border-purple-500/20">
                    <p class="text-[10px] font-black text-purple-400 uppercase tracking-widest mb-1 opacity-70">Web Latency (Google)</p>
                    <div class="flex items-baseline gap-2">
                        <span id="stat-web" class="text-6xl font-black tracking-tighter text-purple-400">0</span>
                        <span class="text-xl font-bold opacity-20">ms</span>
                    </div>
                </div>
            </div>

            <!-- Graphs Column -->
            <div class="lg:col-span-2 space-y-6">
                <!-- Main Comparison Chart -->
                <div class="glass rounded-3xl p-6 border-white/5">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-xs font-black uppercase tracking-widest text-slate-400">Response History (Web vs Local)</h3>
                        <div class="flex gap-4">
                            <div class="flex items-center gap-1.5 text-[10px] font-black text-emerald-500">LOCAL</div>
                            <div class="flex items-center gap-1.5 text-[10px] font-black text-purple-500">WEB</div>
                        </div>
                    </div>
                    <div id="main-chart" class="h-40 grid-container border-b border-white/5 pb-1">
                        <!-- Bars injected by JS -->
                    </div>
                </div>

                <!-- Secondary Charts Grid -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="glass rounded-3xl p-5">
                        <h3 class="text-[10px] font-black uppercase tracking-widest text-blue-400 mb-4 text-center">Signal Stability %</h3>
                        <div id="signal-chart" class="h-20 grid-container"></div>
                    </div>
                    <div class="glass rounded-3xl p-5">
                        <h3 class="text-[10px] font-black uppercase tracking-widest text-emerald-400 mb-4 text-center">Local Latency (ms)</h3>
                        <div id="local-chart" class="h-20 grid-container"></div>
                    </div>
                    <div class="glass rounded-3xl p-5 border-yellow-500/10">
                        <h3 class="text-[10px] font-black uppercase tracking-widest text-yellow-500/50 mb-4 text-center">ISP Overhead (Delay)</h3>
                        <div id="diff-chart" class="h-20 grid-container"></div>
                    </div>
                    <div class="glass rounded-3xl p-5 border-purple-500/10">
                        <h3 class="text-[10px] font-black uppercase tracking-widest text-purple-400 mb-4 text-center">Web Latency (ms)</h3>
                        <div id="web-chart" class="h-20 grid-container"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const MAX_DATA = 40;
        let history = { local: [], web: [], signal: [], diff: [] };

        // Configuration for the different chart containers
        const chartsConfig = [
            { id: 'main-chart', type: 'dual' },
            { id: 'signal-chart', type: 'single', color: 'bg-blue-500/30' },
            { id: 'local-chart', type: 'single', color: 'bg-emerald-500/30' },
            { id: 'web-chart', type: 'single', color: 'bg-purple-500/30' },
            { id: 'diff-chart', type: 'single', color: 'bg-yellow-500/30' }
        ];

        function initCharts() {
            chartsConfig.forEach(config => {
                const el = document.getElementById(config.id);
                el.innerHTML = '';
                for (let i = 0; i < MAX_DATA; i++) {
                    const col = document.createElement('div');
                    col.className = 'flex flex-col justify-end h-full gap-0.5';
                    if (config.type === 'dual') {
                        col.innerHTML = `
                            <div class="bar bg-purple-500/40" id="web-${config.id}-${i}" style="height:0%"></div>
                            <div class="bar bg-emerald-500/60" id="loc-${config.id}-${i}" style="height:0%"></div>
                        `;
                    } else {
                        col.innerHTML = `<div class="bar ${config.color}" id="val-${config.id}-${i}" style="height:0%"></div>`;
                    }
                    el.appendChild(col);
                }
            });
        }

        async function updateData() {
            try {
                const res = await fetch('/stats');
                const data = await res.json();
                
                const lines = (data.raw || '').split('\\n');
                let ssid = 'N/A';
                let signal = 0;
                lines.forEach(l => {
                    if (l.includes('SSID')) ssid = l.split(':')[1]?.trim();
                    if (l.includes('Signal')) signal = parseInt(l.split(':')[1]?.replace('%','').trim()) || 0;
                });

                const diff = Math.max(0, data.webPing - data.localPing);

                // Update text elements
                document.getElementById('stat-signal').innerText = signal;
                document.getElementById('stat-ssid').innerText = ssid;
                document.getElementById('stat-local').innerText = data.localPing >= 900 ? '!!' : data.localPing;
                document.getElementById('stat-web').innerText = data.webPing >= 900 ? '!!' : data.webPing;

                // Push to history
                history.local.push(data.localPing);
                history.web.push(data.webPing);
                history.signal.push(signal);
                history.diff.push(diff);
                
                if (history.local.length > MAX_DATA) {
                    history.local.shift();
                    history.web.shift();
                    history.signal.shift();
                    history.diff.shift();
                }

                renderCharts();
                
                // Status indicator
                document.getElementById('status-badge').className = "px-4 py-1.5 rounded-full flex items-center gap-2 border bg-emerald-500/10 border-emerald-500/20";
                document.getElementById('status-dot').className = "w-2 h-2 rounded-full bg-emerald-500 animate-pulse";
                document.getElementById('status-text').innerText = "System Live";
                document.getElementById('status-text').className = "text-[10px] font-black uppercase tracking-widest text-emerald-400";
            } catch (e) {
                document.getElementById('status-badge').className = "px-4 py-1.5 rounded-full flex items-center gap-2 border bg-red-500/10 border-red-500/20";
                document.getElementById('status-dot').className = "w-2 h-2 rounded-full bg-red-500";
                document.getElementById('status-text').innerText = "Link Lost";
                document.getElementById('status-text').className = "text-[10px] font-black uppercase tracking-widest text-red-400";
            }
        }

        function renderCharts() {
            const len = history.local.length;
            for (let i = 0; i < len; i++) {
                // Main Dual Chart
                document.getElementById(`web-main-chart-${i}`).style.height = Math.min((history.web[i] / 250) * 100, 100) + '%';
                document.getElementById(`loc-main-chart-${i}`).style.height = Math.min((history.local[i] / 250) * 100, 100) + '%';
                
                // Signal Chart
                document.getElementById(`val-signal-chart-${i}`).style.height = history.signal[i] + '%';

                // Local Chart
                document.getElementById(`val-local-chart-${i}`).style.height = Math.min((history.local[i] / 150) * 100, 100) + '%';
                
                // Web Chart
                document.getElementById(`val-web-chart-${i}`).style.height = Math.min((history.web[i] / 250) * 100, 100) + '%';
                
                // Diff Chart
                document.getElementById(`val-diff-chart-${i}`).style.height = Math.min((history.diff[i] / 150) * 100, 100) + '%';
            }
        }

        window.onload = () => {
            initCharts();
            updateData();
            setInterval(updateData, 2000);
        };
    </script>
</body>
</html>
"""

def get_ping(host):
    try:
        # Standard Windows ping command
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
        # WiFi details via netsh
        wifi_data = subprocess.check_output("netsh wlan show interfaces", shell=True).decode('utf-8', errors='ignore')
        return jsonify({
            "raw": wifi_data, 
            "localPing": local_p, 
            "webPing": web_p, 
            "gateway": gateway
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/')
def home():
    return DASHBOARD_HTML

if __name__ == '__main__':
    print("--- NETWORK MONITOR v2.8 READY ---")
    print("Link: http://127.0.0.1:5001")
    app.run(port=5001, debug=False, use_reloader=False)
