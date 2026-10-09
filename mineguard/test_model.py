from pathlib import Path
import pandas as pd
from joblib import load

BASE_DIR = Path(__file__).parent
model = load(BASE_DIR / "risk_model.joblib")

examples = pd.DataFrame([
    {"payload": 50, "fuel": 75, "speed": 20},
    {"payload": 90, "fuel": 15, "speed": 35},
    {"payload": 0, "fuel": 90, "speed": 0},
    {"payload": 90, "fuel": 30, "speed": 20}
])

predictions = model.predict(examples)
scores = model.decision_function(examples)

print("=== MineGuard AI — проверка ML ===")

for i, row in examples.iterrows():
    status = "АНОМАЛИЯ" if predictions[i] == -1 else "ОБЫЧНОЕ ПОВЕДЕНИЕ"

    print(f"\nПример {i + 1}:")
    print(f"Груз: {row['payload']} т")
    print(f"Топливо: {row['fuel']}%")
    print(f"Скорость: {row['speed']} км/ч")
    print(f"ML результат: {status}")
    print(f"Оценка аномальности: {scores[i]:.4f}")
