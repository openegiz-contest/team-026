"""Self-contained offline-capable SVG visualization of Ditto twin states.

The layout is a *schematic* haulage circuit, not geographic coordinates.
Every displayed telemetry/risk value is read from Eclipse Ditto by the UI.
"""
from html import escape


def _num(data, key, default=0.0):
    try:
        return float(data.get(key, default))
    except (ValueError, TypeError):
        return float(default)


def render_mine_map(truck1, truck2, crusher, road, mine, *, title="MineGuard haulage cell"):
    slowdown = _num(road, "slowdown_pct")
    ore = _num(mine, "shift_tonnes")
    throughput = _num(crusher, "throughput_tph")
    risk1 = _num(truck1, "risk_score")
    risk2 = _num(truck2, "risk_score")

    def truck(twin, row, label, risk):
        pos = max(0, min(3.2, _num(twin, "route_km")))
        x = 260 + 500 * pos / 3.2
        y = 156 if row == 0 else 217
        risk_color = "#f45d66" if risk >= 70 else "#e4a84a" if risk >= 35 else "#60e1b9"
        payload = _num(twin, "payload_t")
        state = escape(str(twin.get("state", "unknown")))[:40]
        return f'''<g transform="translate({x:.1f},{y})">
        <rect x="-31" y="-23" width="62" height="40" rx="11" fill="#16344a" stroke="{risk_color}" stroke-width="2.5"/>
        <path d="M-20 -8 H12 L22 5 H-20 Z" fill="#4e9dca"/><circle cx="-13" cy="18" r="5" fill="#b2cde2"/><circle cx="15" cy="18" r="5" fill="#b2cde2"/>
        <text x="0" y="-32" text-anchor="middle" font-size="13" font-weight="700" fill="#e5f3ff">{label} · {risk:.0f}/100</text>
        <text x="0" y="41" text-anchor="middle" font-size="11" fill="#a7c7da">{payload:.0f}t · {state}</text>
        </g>'''

    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><style>
    html,body{{margin:0;padding:0;background:#091624;font-family:system-ui,Segoe UI,sans-serif;color:#eaf4fb}}
    .outer{{border-radius:18px;border:1px solid #2a4a61;background:linear-gradient(160deg,#0b2133,#102739 60%,#0a202c);overflow:hidden}}
    .hdr{{padding:18px 22px 5px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px}}
    .title{{font-size:18px;font-weight:750}}.sub{{font-size:12px;color:#9fb9c9}}
    .foot{{display:flex;flex-wrap:wrap;justify-content:space-between;gap:6px;padding:0 20px 17px;font-size:12px;color:#b7d4e2}}
    .v{{color:#75e4c2;font-weight:700}} svg{{width:100%;display:block}}
    </style></head><body><div class="outer"><div class="hdr"><div class="title">{escape(title)}</div>
    <div class="sub">План-схема · параметры получены из Eclipse Ditto</div></div>
    <svg viewBox="0 0 1000 330" role="img" aria-label="Схема карьерной дороги с самосвалами, погрузчиком и дробилкой">
      <defs><linearGradient id="ground" x2="1" y2="1"><stop stop-color="#14374c"/><stop offset="1" stop-color="#10304a"/></linearGradient></defs>
      <rect x="28" y="43" width="945" height="245" rx="19" fill="url(#ground)" opacity="0.52"/>
      <path d="M217 180 H795" fill="none" stroke="#50718d" stroke-width="67" stroke-linecap="round" opacity="0.62"/>
      <path d="M217 180 H795" fill="none" stroke="#d9e8d7" stroke-width="3" stroke-dasharray="12 13" opacity="0.7"/>
      <rect x="38" y="105" width="182" height="130" rx="14" fill="#17473b" stroke="#47ad90" stroke-width="2"/>
      <text x="129" y="151" text-anchor="middle" fill="#ceffdf" font-size="22">⛏</text>
      <text x="129" y="177" text-anchor="middle" fill="white" font-size="15" font-weight="700">Погрузка</text>
      <text x="129" y="196" text-anchor="middle" fill="#add9c8" font-size="12">Экскаватор</text>
      <rect x="793" y="105" width="177" height="130" rx="14" fill="#4b3334" stroke="#d89e84" stroke-width="2"/>
      <text x="882" y="151" text-anchor="middle" fill="#f2d3ab" font-size="25">⚙</text>
      <text x="882" y="177" text-anchor="middle" fill="white" font-size="15" font-weight="700">Дробилка</text>
      <text x="882" y="196" text-anchor="middle" fill="#f2d3ab" font-size="12">{throughput:.0f} т/ч</text>
      {truck(truck1, 0, "HT-01", risk1)}
      {truck(truck2, 1, "HT-02", risk2)}
      <g transform="translate(330,273)"><rect x="-69" y="-14" width="138" height="28" rx="10" fill="#12393f" stroke="#428899"/><text text-anchor="middle" y="5" fill="#afe3ed" font-size="12">⛽ Заправка</text></g>
      <text x="498" y="69" text-anchor="middle" fill="#c7e9fc" font-size="15">3,2 км · дорога</text>
      <text x="498" y="91" text-anchor="middle" fill="#9fbed1" font-size="12">Замедление: {slowdown:.0f}%</text>
    </svg><div class="foot"><span>Добыча за смену: <span class="v">{ore:,.0f} т</span></span>
    <span>🟢 LOW &nbsp; 🟠 MEDIUM &nbsp; 🔴 HIGH</span><span>Team 026 · OpenEgiz</span></div></div></body></html>'''
