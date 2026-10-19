# MineGuard AI 2.1 — Team 026

## Замысел (Intent)

**Объект:** учебный цифровой двойник транспортного участка открытого карьера: один погрузчик, два автосамосвала грузоподъёмностью до 90 т, дорога длиной 3,2 км в одну сторону, первичная дробилка и пункт заправки. Это **вымышленный полигон**, построенный на платформе OpenEgiz, а не модель реального действующего месторождения.

**Кто использует:** диспетчер автотранспорта и инженер по промышленной безопасности. **Какое решение:** при росте нагрузок, ухудшении дороги, очереди у дробилки или ремонте оценить компромисс между рассчитанной добычей и предупреждениями безопасности. **Почему:** отдельные показания телеметрии не раскрывают связанных последствий для дороги, погрузки, очереди и производства. Один набор связанных двойников показывает эти зависимости на пространственной схеме.

Параметры и рамки: 90 т — учебное округление близкого класса техники (Komatsu HD785-7: 91 т; CAT 777: 91,7 т); 3,2 км, ковш 22 т, 35 с/ковш и базовая модель движения взяты из `examples/mine/simulator.py` OpenEgiz. Остальные ограничения показаны в README и коде `operations_sim.py`. Это **не калибровка промышленного рудника**. Производственные результаты не являются прогнозом реального предприятия.

## Team

- **Team 026** · сольное участие
- **GitHub user:** `zhanibekoralbekuly-lang`
- **Repository:** https://github.com/openegiz-contest/team-026
- **Platform:** OpenEgiz v1.0.4 / Eclipse Ditto / MQTT

## Mine & connected twins

В собственном пространстве имён **`org.mineguard.team026`** автоматически создаются девять цифровых двойников с именами и отношениями `attributes.connected_to`: `pit-01`, `loader-01`, `truck-01`, `truck-02`, `haul-road-01`, `crusher-01`, `fuel-bay-01`, `live-truck-01`, `live-truck-02`.

Семь связаны с контрфактическим What-if; два зеркалируют наблюдаемую телеметрию и Risk Score, рассчитанный MineGuard. **Все обновления MineGuard идут через MQTT → Ditto**. Streamlit читает текущие состояния **из Ditto**, а не из локального CSV. За пространственную схему отвечает оригинальный `mineguard/mine_map.py`. Reference Example Mine — только источник событий, не заявляем его неизменённый дашборд как командную работу.

## Modules / What-if scenarios

| Модуль или сценарий | Функция | Как увидеть на Стенде | Как отменить |
|---|---|---|---|
| Live AI Fleet | MQTT → IsolationForest → Risk Score → новые live-truck двойники Ditto, InfluxDB и Grafana | `localhost:8501` → 🗺️ LIVE; Grafana `localhost:3000/d/team026-mineguard` | Наблюдение, не управление |
| 2D Connected Mine | Схема погрузчик → два самосвала → дорога → дробилка, заправка, добыча; значения из Ditto | `localhost:8501` → 🗺️; таблица двойников | Автоматическое обновление LIVE, What-if Reset |
| Overload / low fuel | Пересчёт ML, риска и добычи, публикация в 7 двойников | Пресет «Перегрузка + мало топлива» → Apply → карта / Safety | Кнопка «Вернуть базовый режим» |
| Slippery road | Замедление дороги, новые данные самосвалов, дробилка и добыча, 7 twin updates | «Скользкая дорога» → Apply → карта / Production | «Вернуть базовый режим» |
| Crusher congestion | Очередь на дробилке, тоннаж и продолжительность цикла | «Очередь на дробилке» → Apply → карта / Production | «Вернуть базовый режим» |
| Truck repair | Один самосвал на ремонте, меняются рейсы и тоннаж | «Ремонт одного самосвала» → Apply → карта / Production | «Вернуть базовый режим» |
| Low fuel / refuel | Низкое топливо и 10-минутная модель заправки | «Низкий уровень топлива» → Apply → Production | «Вернуть базовый режим» |
| ML atypical trip | Реальная классификация признаков загруженной модели IsolationForest | «ML-аномалия · нетипичный рейс» → Safety | Переключить пресет / Reset |
| Evidence export | Исходные настройки, Risk Score и модельные результаты JSON | `localhost:8501` → Evidence → Download | Удалить локальный файл |

**Управление:** изменение ползунков НЕ посылает команды. Только явная кнопка **Apply** обновляет **песочницу MineGuard** в Ditto, а **Reset** публикует базовый режим. Эти действия не управляют карьерным оборудованием, не меняют Example Mine и live-поток Grafana.

## Clean boot in Judge Environment

```bash
sudo apt-get update
sudo apt-get install -y make
make mineguard
```

Выполнять из корня клонированного репозитория. Скрипт `make mineguard` генерирует секреты, запускает OpenEgiz, исходный Example Mine, оригинальный job `mineguard-setup` (9 twins), `mineguard-ai` и `mineguard-web`. Никаких ручных шагов внутри установки не предусмотрено.

**Проверка:** после запуска открыть `http://localhost:8501`; переключить сценарий, нажать Apply, посмотреть изменения связанных двойников; открыть `http://localhost:3000/d/team026-mineguard`.

## What works, evidence and limits

- **Подтверждено пользовательскими логами:** локальный ML-мониторинг получает сообщения двух самосвалов, пишет в InfluxDB, обновляет Risk Score; прежний Streamlit был Healthy и интерактивен; ранее 16/16 тестов и Docker-сборка пройдены, данные persist в Docker Volume.
- **Подтверждено автономными тестами новой версии:** правила риска, синтетические сценарии, формат нативных Ditto MQTT-команд, список девяти связанных двойников и семи сценических обновлений. См. `CONTEST_EVIDENCE.md`.
- **Требует финальной проверки на машине с Docker:** новая связка `mineguard-setup → MQTT → Ditto GET → 2D map`. Самостоятельно имитировать скриншот нового полного запуска нельзя; это отмечено как ограничение.

## Данные и допущения

Все входы телеметрии **синтетические**, без персональных или конфиденциальных промышленных данных. Модель `risk_model.joblib` обучена на синтетических (payload, fuel, speed) и выявляет статистические выбросы, **не аварии**. Risk Score — воспроизводимая эвристика от 0 до 100, **не процент вероятности аварии**. Операционная модель дискретна (10 с), одна очередь погрузки и одна дробилки, условный расход топлива в процентных пунктах, объём 90 т. Реальные зависимости могут отличаться.

**Источники параметров:**
- [OpenEgiz Example Mine](examples/mine/simulator.py) — длина рейса 3,2 км, груз 90 т, ковш 22 т, 35 с на проход, 60 с разгрузка (демонстрационные значения проекта).
- [Komatsu HD785-7](https://www.komatsu.eu/en/Product-Archive/Rigid-Dump-Trucks/HD785-7) — реальный rated payload 91 т как ориентир класса техники, не как источник всех параметров.
- [CAT 777](https://www.cat.com/en_US/products/new/equipment/off-highway-trucks/off-highway-trucks/115560.html) — 91,7 т target payload, ориентир класса.

Собственные модели, графика и код Team 026 — MIT. Стороннее ПО и исходники OpenEgiz сохраняют свои лицензии. Внешние датасеты, требующие загрузки на стенд, отсутствуют.

## Visualization and presentation

- **Space / processes:** `localhost:8501` → 🗺️; карта живых и сценарных двойников, привязанные к объектам риски, местоположение, скорость, тоннаж, загрузка и очередь.
- **Operational charts / linked outcomes:** `localhost:8501` → 🏭; график накопленной добычи и узкие места процесса.
- **Live time series:** `localhost:3000/d/team026-mineguard` Grafana.
- **Presentation:** `presentation.pdf` в корне; инструкция демонстрации — `README.md`.

## Known limitations

Модель учебная: два виртуальных самосвала, без маршрутизации по реальным дорогам, физических происшествий, финансовых эффектов и статистически обоснованных доверительных интервалов. Map — **технологическая план-схема, а не географическая карта**. Сценарные позиции на карте условны; LIVE позиции берутся из Ditto. Что-если обновляет согласованные данные 7 двойников только при нажатии Apply; это не интеграция с PLC/SCADA. Калибровки на фактическом руднике нет.

## Jury-ready incremental features (requires Docker revalidation)

- The live ML engine runs IsolationForest **only on moving, loaded `hauling` observations**; other states are explicitly `ml_scored=false`. Rule-based Risk Score still reports overload and low fuel independently. This reduces off-domain alerts, not proof of accident detection accuracy.
- Streamlit adds a reproducible **Monte-Carlo** tab (default 200 samples, seed 42) using transparent *assumed* speed, service-time and failure variability. P10/P50/P90 and percent meeting the baseline plan are **model outcomes only** and should never be interpreted as industrial reliability probabilities.
- The **Cycle** tab is a process flow schematic generated from simulation metrics. The connected live/scenario Ditto map remains in the original first tab.
- For a judge-equivalent machine: `make mineguard`, then `RUN_TESTS=1 make mineguard-smoke`.
- Update `presentation.pdf` with the verified final test count and new screenshot before submission. The current PDF is a separate artifact and has not been regenerated by this patch.
