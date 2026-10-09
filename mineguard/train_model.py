import pandas as pd
from pathlib import Path
from sklearn.ensemble import IsolationForest
from joblib import dump

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "telemetry.csv"
MODEL_FILE = BASE_DIR / "risk_model.joblib"

columns = ["payload", "fuel", "speed"]

data = pd.read_csv(DATA_FILE)
data[columns] = data[columns].apply(pd.to_numeric, errors="coerce")
data = data.dropna(subset=columns)

if len(data) < 100:
    raise ValueError("Недостаточно данных для обучения")

print("=== MineGuard AI — обучение ML ===")
print(f"Записей для обучения: {len(data)}")

model = IsolationForest(
    n_estimators=100,
    contamination=0.05,
    random_state=42
)

model.fit(data[columns])

predictions = model.predict(data[columns])
anomalies = (predictions == -1).sum()

dump(model, MODEL_FILE)

print(f"Обнаружено аномальных записей: {anomalies}")
print(f"Модель сохранена: {MODEL_FILE}")
print("Обучение завершено!")
