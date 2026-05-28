# Network Pulse

Real-time Windows network diagnostic dashboard that monitors WiFi signal strength, local gateway latency, and web latency — all served from a live updating web UI.

## Features

- **WiFi Signal Strength** — Reads signal percentage via `netsh wlan show interfaces`
- **Local Latency** — Ping to your router/gateway (default `192.168.0.1`)
- **Web Latency** — Ping to Google DNS (`8.8.8.8`)
- **Live Dashboard** — Real-time bar chart history with color-coded latency indicators
- **ISP Overhead** — Calculated difference between web and local ping

## Files

| File | Dashboard | Port | Details |
|------|-----------|------|---------|
| `server.py` | React | 5000 | Basic WiFi signal monitor |
| `monitor.py` | None (API only) | 5000 | Simple WiFi stats endpoint |
| `network.py` | React | 5000 | WiFi + Ping with gateway detection |
| `monitoring.py` | Vanilla JS | 5001 | v2.7 — Local + Web ping graphs |
| `monitoring2.py` | Vanilla JS | 5001 | v2.8 — Added dedicated local latency chart |
| `fant_monitor.py` | React | 5000 | Full diagnostic with comparison graphs |
| `net_mon_ng.py` | React | 5001 | v2.1 — Stable multi-ping monitor |

## Requirements

- Windows (uses `netsh` and `ping`)
- Python 3.13+

## Setup

```bash
pip install flask
```

## Usage

Pick a script and run it:

```bash
python server.py
```

Or try the latest version:

```bash
python monitoring2.py
```

Open your browser to the address shown in the terminal (usually `http://127.0.0.1:5000` or `http://127.0.0.1:5001`).
