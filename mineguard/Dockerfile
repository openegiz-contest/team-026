FROM python:3.11-slim

WORKDIR /app

COPY mineguard/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY mineguard/ /app/

CMD ["python", "-u", "monitor.py"]
