"""MineGuard AI — interactive safety + transparent haul-cycle what-if studies."""
import json
import time
import urllib.error
from dataclasses import asdict
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from operations_sim import Scenario, run_haul_shift
from what_if import simulate
from ditto_bridge import (NAMESPACE, EXAMPLE_NAMESPACE, fetch_twin,
                          read_twin_values, build_scenario_updates, publish_messages)
from mine_map import render_mine_map
from monte_carlo import run_monte_carlo
from quarry_view import render_cycle

st.set_page_config(page_title="MineGuard AI | Decision Lab", page_icon="🚛", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
  .block-container {max-width: 1350px; padding-top: 1.8rem;}
  #MainMenu, footer {visibility: hidden;}
  .hero {background: linear-gradient(110deg,#0b1e30,#143c50 65%,#096f69); border:1px solid #276072;
    padding:25px 30px; border-radius:20px; color:white; margin-bottom:20px;}
  .hero .kicker {color:#72f3d0; font-size:0.76rem; font-weight:700; letter-spacing:0.15em;}
  .hero h1 {color:white; font-size:2.3rem; margin:5px 0 8px 0;}
  .hero p {color:#c8e1e6; margin:0;}
  div[data-testid="stMetric"] {background:rgba(84,132,141,.09);border:1px solid rgba(126,155,172,.24);
    border-radius:16px;padding:14px 18px;}
  .small-note {font-size:.83rem;color:#9aaebd;}
</style>""", unsafe_allow_html=True)

PRESETS = {
    "Перегрузка + мало топлива": {"payload": 95, "fuel": 12, "speed": 35, "road": 0, "crusher": 0, "repair": 0},
    "ML-аномалия · нетипичный рейс": {"payload": 10, "fuel": 50, "speed": 25, "road": 0, "crusher": 0, "repair": 0},
    "Скользкая дорога": {"payload": 70, "fuel": 60, "speed": 25, "road": 45, "crusher": 0, "repair": 0},
    "Очередь на дробилке": {"payload": 70, "fuel": 60, "speed": 25, "road": 0, "crusher": 240, "repair": 0},
    "Ремонт одного самосвала": {"payload": 70, "fuel": 60, "speed": 25, "road": 0, "crusher": 0, "repair": 120},
    "Низкий уровень топлива": {"payload": 70, "fuel": 10, "speed": 25, "road": 0, "crusher": 0, "repair": 0},
    "Пользовательский сценарий": None,
}
DEFAULTS = {"b_payload":70, "b_fuel":60, "b_speed":25, "a_payload":95, "a_fuel":12,
            "a_speed":35, "road":0, "crusher":0, "repair":0, "shift":8}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)


def set_preset():
    p = PRESETS[st.session_state.preset]
    if p is not None:
        st.session_state.update({"a_payload":p["payload"], "a_fuel":p["fuel"], "a_speed":p["speed"],
                                 "road":p["road"], "crusher":p["crusher"], "repair":p["repair"]})


with st.sidebar:
    st.header("⚙️ Центр сценариев")
    st.selectbox("Готовый сценарий", list(PRESETS), key="preset", on_change=set_preset)
    st.caption("Меняйте исходные условия и сравнивайте результаты. Модель не посылает команды оборудованию.")
    st.markdown("**Настройки производственной модели**")
    st.slider("Продолжительность смены · часы", 1, 24, key="shift")
    st.slider("Замедление транспорта на дороге · %", 0, 80, step=5, key="road")
    st.slider("Дополнительное время разгрузки · сек", 0, 900, step=30, key="crusher")
    st.slider("Ремонт первого самосвала · мин", 0, 240, step=10, key="repair")
    st.info("Тестовая шахта: **2 самосвала**, 1 экскаватор, 1 дробилка, рейс 3,2 км. Допущения доступны внизу.")
    st.caption("Team 026 · OpenEgiz 1.0.4 · synthetic telemetry")

st.markdown("""<div class="hero"><div class="kicker">TEAM 026 / OPENEGIZ DIGITAL MINE</div>
<h1>🚛 MineGuard AI · Decision Lab</h1><p>What-if: безопасность самосвалов + производственные последствия изменений</p></div>""", unsafe_allow_html=True)
st.caption("Демонстрационная цифровая модель. Значения Risk Score — эвристика, тоннаж — результат упрощённой симуляции, не прогноз реальной шахты.")

col1, col2 = st.columns(2, gap="large")
with col1:
    st.subheader("01 / BEFORE · Базовый режим")
    st.slider("Загрузка · тонны", 0, 120, key="b_payload")
    st.slider("Топливо · %", 0, 100, key="b_fuel")
    st.slider("Скорость · км/ч", 1, 80, key="b_speed")
with col2:
    st.subheader("02 / AFTER · Изменённый режим")
    st.slider("Загрузка · тонны", 0, 120, key="a_payload")
    st.slider("Топливо · %", 0, 100, key="a_fuel")
    st.slider("Скорость · км/ч", 1, 80, key="a_speed")

before = simulate(st.session_state.b_payload, st.session_state.b_fuel, st.session_state.b_speed)
after = simulate(st.session_state.a_payload, st.session_state.a_fuel, st.session_state.a_speed)
reference_cfg = Scenario(name="BEFORE", payload_t=before["payload"], fuel_pct=before["fuel"],
                         loaded_speed_kmh=before["speed"], shift_hours=st.session_state.shift)
scenario_cfg = Scenario(name="AFTER", payload_t=after["payload"], fuel_pct=after["fuel"],
                        loaded_speed_kmh=after["speed"], road_slowdown_pct=st.session_state.road,
                        crusher_delay_seconds=st.session_state.crusher,
                        maintenance_minutes=st.session_state.repair, shift_hours=st.session_state.shift)
base_ops = run_haul_shift(reference_cfg)
new_ops = run_haul_shift(scenario_cfg)

st.divider()
st.subheader("03 / Сравнение решений")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Risk Score · BEFORE", f"{before['risk']}/100")
c2.metric("Risk Score · AFTER", f"{after['risk']}/100", f"{after['risk']-before['risk']:+} пунктов", delta_color="inverse")
c3.metric("Руда за смену · BEFORE", f"{base_ops['tonnes']:,.0f} т".replace(",", " "))
c4.metric("Руда за смену · AFTER", f"{new_ops['tonnes']:,.0f} т".replace(",", " "),
          f"{new_ops['tonnes']-base_ops['tonnes']:+,.0f} т".replace(",", " "))

if after["risk"] >= 70:
    st.error("🔴 HIGH RISK — модель сигнализирует о необходимости проверки выбранных условий.")
elif after["risk"] >= 35:
    st.warning("🟠 MEDIUM RISK — модель показывает повышенный риск.")
else:
    st.success("🟢 LOW RISK — по текущим эвристическим правилам высокий риск не обнаружен.")

map_tab, risk_tab, ops_tab, mc_tab, cycle_tab, evidence_tab = st.tabs([
    "🗺️ Карта цифрового рудника", "🛡️ Безопасность и ML",
    "🏭 Работа шахты", "🎲 Неопределённость", "⛏ Цикл карьера",
    "📋 Доказательства и допущения"])

with map_tab:
    st.markdown("### OpenEgiz / Eclipse Ditto · connected digital twins")
    st.caption("Карта показывает цифровые двойники, сохранённые в Ditto через MQTT. "
               "Изменение ползунков само по себе ничего не публикует: нажмите «Применить».")
    a, b, c = st.columns([1, 1, 1])
    with a:
        apply_pressed = st.button("🚀 Применить AFTER в Ditto", use_container_width=True, type="primary")
    with b:
        reset_pressed = st.button("↩ Вернуть базовый режим", use_container_width=True)
    with c:
        st.button("🔄 Считать текущие двойники", use_container_width=True)

    if apply_pressed or reset_pressed:
        try:
            if reset_pressed:
                reset_cfg = Scenario(name="BASELINE / RESET", payload_t=before["payload"],
                                     fuel_pct=before["fuel"], loaded_speed_kmh=before["speed"],
                                     shift_hours=st.session_state.shift)
                payloads = build_scenario_updates(before, before, base_ops, base_ops, reset_cfg)
            else:
                payloads = build_scenario_updates(before, after, base_ops, new_ops, scenario_cfg)
            publish_messages(payloads)
            st.success("Опубликовано 7 связанных состояний через MQTT → Ditto. "
                       "Это только демонстрационные двойники, не управление техникой.")
            time.sleep(0.8)  # Ditto consumes MQTT asynchronously.
        except (OSError, RuntimeError, ValueError) as exc:
            st.error(f"Не удалось отправить сценарий в Ditto: {exc}")

    try:
        scenario_twins = {name: read_twin_values(name) for name in (
            "pit-01", "truck-01", "truck-02", "crusher-01", "haul-road-01", "loader-01", "fuel-bay-01")}
        components.html(render_mine_map(
            scenario_twins["truck-01"], scenario_twins["truck-02"],
            scenario_twins["crusher-01"], scenario_twins["haul-road-01"],
            scenario_twins["pit-01"], title="WHAT-IF · состояние сценарных двойников в Ditto"),
            height=510, scrolling=False)
        summary = scenario_twins["pit-01"]
        st.info(f"Ditto: **{summary.get('mode', 'baseline')}** · "
                f"добыча {summary.get('shift_tonnes', 0)} т · "
                f"Risk {summary.get('risk_level', 'LOW')} · "
                f"все 7 связанных объектов обновляются одним сценарием")
        with st.expander("Подтверждение: значения двойников из Ditto"):
            st.dataframe(pd.DataFrame([
                {"Двойник": f"{NAMESPACE}:{name}", **values}
                for name, values in scenario_twins.items()
            ]), hide_index=True, use_container_width=True)
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        st.warning(f"Не удалось прочитать сценарные двойники Ditto: {exc}. "
                   "Убедитесь, что mineguard-setup завершился успешно и OpenEgiz запущен.")

    st.markdown("#### LIVE · оперативные данные из OpenEgiz")
    st.caption("Ниже — наблюдаемые состояния самосвалов и AI-оценки. "
               "Данные получаются с сервера Ditto, не из локальных ползунков.")
    try:
        live = {name: read_twin_values(name) for name in ("live-truck-01", "live-truck-02")}
        base = {name: read_twin_values(name, EXAMPLE_NAMESPACE) for name in
                ("crusher-01", "mine-01")}
        if not all(live[name].get("updated_utc") for name in live):
            st.warning("Некоторые live-двойники ещё не получали новых данных AI-мониторинга. "
                       "Дождитесь MQTT-телеметрии и нажмите обновление.")
        # Bridge original Example Mine's feature schema into visual schema.
        live_mine = {"shift_tonnes": base["mine-01"].get("tonnes_mined", 0)}
        live_crusher = {"throughput_tph": base["crusher-01"].get("throughput", 0)}
        components.html(render_mine_map(live["live-truck-01"], live["live-truck-02"],
                                        live_crusher, {"slowdown_pct": 0}, live_mine,
                                        title="LIVE · телеметрия и ML-оценка из Ditto"),
                        height=510, scrolling=False)
        rows = [{"Грузовик": truck, "Груз, т": values.get("payload_t"),
                 "Скорость, км/ч": values.get("speed_kmh"),
                 "Топливо, %": values.get("fuel_pct"),
                 "Risk Score": values.get("risk_score"),
                 "Оценка ML": "Выполнена" if values.get("ml_scored") else "Не применялась",
                 "ML score": values.get("ml_score"),
                 "Состояние": values.get("state")}
                for truck, values in live.items()]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        st.warning(f"Данные реальных цифровых двойников пока недоступны: {exc}")
    st.caption("Схема пространственная, но не географическая. What-if изменяет только "
               "org.mineguard.team026, без команд производственному оборудованию.")

with risk_tab:
    a, b = st.columns([1, 1.2], gap="large")
    with a:
        st.markdown("**Что формирует Risk Score**")
        data = pd.DataFrame({"BEFORE":before["factors"], "AFTER":after["factors"]})
        st.bar_chart(data, height=275)
        st.caption("Пороговая оценка: загрузка, топливо, +35 при ML-аномалии; итог ограничен 100.")
    with b:
        st.markdown("**Результат IsolationForest**")
        table = pd.DataFrame([
            {"Сценарий":"BEFORE", "Аномалия":before["anomaly"], "Decision function":before["ml_decision_score"],
             "Risk":before["risk"], "Уровень":before["level"]},
            {"Сценарий":"AFTER", "Аномалия":after["anomaly"], "Decision function":after["ml_decision_score"],
             "Risk":after["risk"], "Уровень":after["level"]},
        ])
        st.dataframe(table, hide_index=True, use_container_width=True)
        st.caption("What-if оценивает гипотетический рейс с грузом (hauling). "
                   "LIVE-монитор пропускает ML-оценку при погрузке/простое/разгрузке; "
                   "Risk Score по правилам продолжает рассчитываться. "
                   "Скорость влияет на ML, но не добавляет прямой штраф к Risk Score.")
    st.markdown("**Возможные действия оператора (не автоматическое управление):**")
    actions=[]
    if after["payload"] > 90: actions.append("Убрать перегрузку: запрос выше модельной вместимости 90 т.")
    elif after["payload"] >= 81: actions.append("Проверить загрузку и соответствие ограничению 90 т.")
    if after["fuel"] < 25: actions.append("Запланировать заправку до следующего рейса.")
    if after["anomaly"]: actions.append("Проверить аномальное сочетание телеметрических показателей.")
    if not actions: actions.append("Сохранять наблюдение за техникой и базовые проверки.")
    for item in actions: st.write("• " + item)

with ops_tab:
    st.markdown("**Накопленная добыча по времени (модельные тонны)**")
    plot = pd.DataFrame({
        "Час смены":[x["hour"] for x in base_ops["timeline"]],
        "BEFORE, т":[x["tonnes"] for x in base_ops["timeline"]],
        "AFTER, т":[x["tonnes"] for x in new_ops["timeline"]],
    }).set_index("Час смены")
    st.line_chart(plot, height=330)
    x,y,z,w=st.columns(4)
    x.metric("Рейсы AFTER", new_ops["trips"], f"{new_ops['trips']-base_ops['trips']:+} рейсов")
    y.metric("Производительность AFTER", f"{new_ops['tonnes_per_hour']:.0f} т/ч")
    z.metric("Очередь на дробилке AFTER", f"{new_ops['crusher_queue_minutes']:.1f} мин")
    w.metric("Простой на ремонте AFTER", f"{new_ops['maintenance_minutes']:.0f} мин")
    st.dataframe(pd.DataFrame([
        {"Показатель":label, "BEFORE":base_ops[key], "AFTER":new_ops[key]}
        for label,key in [("Руда за смену, т", "tonnes"),("Рейсы", "trips"),
                          ("Средний цикл, мин", "average_cycle_minutes"),
                          ("Очередь на погрузку, мин", "loader_queue_minutes"),
                          ("Очередь на дробилку, мин", "crusher_queue_minutes"),
                          ("Заправка, мин", "refuel_minutes"),
                          ("Ремонт, мин", "maintenance_minutes"),
                          ("Условный расход топлива, процентные пункты", "fuel_consumed_pct_points")]
    ]), use_container_width=True, hide_index=True)
    if after["payload"] > 90:
        st.warning("Запрошенный груз выше 90 т. Для производственной модели он ограничен вместимостью 90 т; Risk Score оценивает запрошенный перегруз отдельно.")
    st.caption("Модель считает завершённые рейсы двух машин за смену. Потери / прирост рассчитаны относительно сценария BEFORE, не доказаны полевыми испытаниями.")

@st.cache_data(show_spinner=False)
def cached_mc(cfg, plan):
    return run_monte_carlo(cfg, n=200, seed=42, plan_tonnes=plan)

mc_result = cached_mc(scenario_cfg, base_ops["tonnes"])
with mc_tab:
    st.markdown("### Разброс результата смены в демонстрационной модели")
    st.caption("200 воспроизводимых прогонов; seed=42. Скорость ±10%, "
               "время погрузки и разгрузки ±15%, допущение MTBF=24 ч. "
               "Это не вероятности для настоящего карьера.")
    p1, p2, p3 = st.columns(3)
    p1.metric("Нижний дециль · P10", f"{mc_result['p10_tonnes']:,.0f} т".replace(",", " "))
    p2.metric("Медиана · P50", f"{mc_result['p50_tonnes']:,.0f} т".replace(",", " "))
    p3.metric("Верхний дециль · P90", f"{mc_result['p90_tonnes']:,.0f} т".replace(",", " "))
    st.markdown(f"**Выполнение плана ({base_ops['tonnes']:,.0f} т):** "
                f"{mc_result['plan_met_pct']:.1f}% модельных прогонов".replace(",", " "))
    st.progress(mc_result['plan_met_pct']/100)
    st.bar_chart(pd.DataFrame({"Тоннаж, т": mc_result["samples_tonnes"]}), height=240)
    st.caption("Порядок значений на диаграмме соответствует номеру прогона, не времени. "
               "Детерминированный вариант может быть оптимистичнее медианы.")

with cycle_tab:
    st.markdown("### Процесс перевозки руды · AFTER")
    components.html(render_cycle(new_ops, title="Погрузка → перевозка → разгрузка"),
                    height=345, scrolling=False)
    st.caption("Отдельная технологическая схема по результатам симуляции. "
               "LIVE-карта цифровых двойников находится на первой вкладке.")

with evidence_tab:
    st.markdown("**Воспроизводимость и границы модели**")
    st.markdown("""
    - Live: Example Mine → MQTT → Ditto; MineGuard публикует рассчитанный Risk Score обратно в **собственные** двойники по MQTT.
    - ML: IsolationForest оценивает **только движение с грузом** (hauling, speed > 1, payload > 0). Другие режимы: `ml_scored=false`, а не «безопасно».
    - What-if: обновляет 7 связанных *сценарных* двойников в `org.mineguard.team026` (дорога, погрузчик, техника, дробилка, заправка, рудник).
    - What-if Safety: **тот же** `risk_model.joblib` (IsolationForest), что и в `monitor.py`, и та же функция `calculate_risk()`.
    - Operations: независимая **детерминированная упрощённая модель** рейсов, очередей у одного экскаватора и одной дробилки.
    - Транспорт: 2 самосвала, маршрут 3,2 км в одну сторону, вместимость до 90 т, ковш 22 т, 35 с на ковш.
    - Время разгрузки: 60 с + выбранная задержка. Скорость возвращения: 35 км/ч до применения замедления дороги.
    - Заправка: 10 минут при уровне ниже 15%. Ремонт: разовая задержка первого самосвала после четверти смены.
    - Уровень топлива измеряется в %, а расход в процентных пунктах; **не** в литрах. Нет расчёта денежных потерь.
    - Простая модель очередей **не калибрована** реальными данными предприятия и не является промышленным прогнозом.
    - Монте-Карло: 200 запусков с seed=42, допущения: скорость ±10%, этапы погрузки/разгрузки ±15%, MTBF 24 ч (не калиброванная оценка).
    - «Применить» и «Вернуть» публикуют значения в отдельные *демонстрационные* двойники Ditto; реальные управляющие команды технике не посылаются.
    - Изменения сценариев не меняют Example Mine / live-телеметрию и не подменяют измерения в Grafana.
    """)
    report={"generated_utc":datetime.now(timezone.utc).isoformat(), "team":"026",
            "safety":{"before":before,"after":after},"operations":{"before":base_ops,"after":new_ops},
            "inputs":{"before":asdict(reference_cfg),"after":asdict(scenario_cfg)},
            "monte_carlo":mc_result}
    st.download_button("⬇️ Скачать протокол эксперимента (JSON)",
                       data=json.dumps(report,ensure_ascii=False,indent=2),
                       file_name="mineguard_whatif_result.json",mime="application/json",use_container_width=True)

st.divider()
st.caption("MineGuard AI · Team 026 | Transparent demo for Digital Mine on OpenEgiz | Risk Score ≠ probability of accident")
