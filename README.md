# MineGuard AI — Team 026

**AI-powered Mining Truck Safety Monitoring System**

MineGuard AI — интеллектуальная система мониторинга карьерных самосвалов, разработанная на платформе OpenEgiz v1.0.4.

Система анализирует телеметрию в реальном времени, обнаруживает аномалии с помощью машинного обучения, рассчитывает Risk Score и отображает результаты в Grafana.

## Running

### Requirements

- Docker Desktop с Docker Compose
- GNU Make
- Git
- Linux или Windows с WSL2

Инструкции по установке OpenEgiz: [OPENEGIZ.md](OPENEGIZ.md) / [OPENEGIZ.ru.md](OPENEGIZ.ru.md).

### Installation and launch

```bash
git clone https://github.com/openegiz-contest/team-026.git
cd team-026
make mineguard
```

Команда `make mineguard` предназначена для запуска платформы OpenEgiz, симулятора шахты и сервиса MineGuard AI.

Обученная ML-модель включена в репозиторий. Отдельная установка Python и ручное обучение модели не требуются.

## What to open

После запуска открой Grafana:

**http://localhost:3000**

Логин и пароль Grafana выводятся при запуске OpenEgiz.

Панель MineGuard AI:

**http://localhost:3000/d/team026-mineguard**

На панели отображаются данные самосвалов, результаты ML-анализа и Risk Score.

## System Architecture

Поток обработки данных:

**OpenEgiz Simulator → MQTT Mosquitto → MineGuard AI → InfluxDB → Grafana**

MineGuard AI использует три параметра самосвалов:

- Payload — масса груза, тонн
- Fuel — уровень топлива, %
- Speed — скорость, км/ч

Для обнаружения статистических аномалий используется алгоритм **IsolationForest** из библиотеки scikit-learn.

## Risk Score

Система рассчитывает оценку риска от 0 до 100 на основе загрузки, уровня топлива и обнаруженных ML-аномалий.

| Risk Score | Level | Description |
|---|---|---|
| 0–34 | LOW | Низкий риск |
| 35–69 | MEDIUM | Повышенное внимание |
| 70–100 | HIGH | Требуется проверка |

При достижении уровня HIGH система формирует предупреждение `HIGH_RISK`.

Risk Score — демонстрационная эввристическая оценка, а не подтверждённая вероятность аварии.

Verification

Проверить работу AI-монитора:

docker logs --tail 40 openegiz-mineguard-ai-1

В логах должны отображаться телеметрия самосвалов, результаты ML-анализа и отправка Risk Score в InfluxDB.

Repository Contents

Path

Description

mineguard/

ML-модель, Python-мониторинг, Dockerfile

mineguard/compose.yml

Конфигурация контейнера MineGuard AI

deploy/compose/

Docker-инфраструктура OpenEgiz

examples/mine/

Симулятор шахты OpenEgiz

SUBMISSION.md

Описание конкурсного проекта

presentation.pdf

Презентация для жюри

OPENEGIZ.md

Документация платформы

Limitations

Система протестирована на двух виртуальных самосвалах. ML-модель обнаруживает статистические отклонения, но не прогнозирует реальные аварии. Для промышленного применения необходима дополнительная проверка на реальных данных.

Полный запуск с нуля в окружении жюри пока не проверен.

License

MIT License. See LICENSE.

Team 026 — Digital Mine on OpenEgiz, 2026