"""Production-cycle schematic generated from simulation metrics, not GPS."""
from html import escape


def render_cycle(operations, title='Модельный цикл карьера'):
    tonnes = float(operations['tonnes'])
    trips = int(operations['trips'])
    queue_loader = float(operations['loader_queue_minutes'])
    queue_crusher = float(operations['crusher_queue_minutes'])
    cycle = float(operations['average_cycle_minutes'])
    return f'''<!doctype html><html lang="ru"><meta charset="utf-8"><style>
    body{{background:#091624;color:#eef8ff;margin:0;font-family:system-ui,sans-serif}}
    .a{{background:#0b2638;border:1px solid #35566d;border-radius:17px;padding:20px}}
    .grid{{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}}
    .node{{background:#153f4b;border:1px solid #4993a5;border-radius:14px;text-align:center;padding:20px;min-width:165px;flex:1}}
    .number{{color:#8df5d4;font-size:22px;font-weight:700}} .sub{{color:#a9c5d8;font-size:12px}}
    .arrow{{font-size:28px;color:#8df5d4}} .stats{{margin-top:24px;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}}
    </style><div class="a"><h2>{escape(title)}</h2>
    <p class="sub">Схема технологических этапов, не координаты машин и не измеренный цикл предприятия</p>
    <div class="grid"><div class="node">⛏️ Погрузка<br><span class="sub">Очередь: {queue_loader:.1f} мин</span></div>
    <div class="arrow">→</div><div class="node">🚛 Перевозка<br><span class="sub">2 самосвала, 3,2 км</span></div>
    <div class="arrow">→</div><div class="node">⚙️ Дробилка<br><span class="sub">Очередь: {queue_crusher:.1f} мин</span></div></div>
    <div class="stats"><span>Рейсы: <span class="number">{trips}</span></span>
    <span>Добыча: <span class="number">{tonnes:,.0f} т</span></span>
    <span>Время до завершения разгрузки: <span class="number">{cycle:.1f} мин</span></span></div>
    <p class="sub">Показанное время — от начала погрузки до разгрузки, без обратного пути.</p></div></html>'''
