FROM python:3.13-slim

WORKDIR /app
COPY . /app

# Sim is stdlib-only for now. If we add deps later:
#   COPY requirements.txt .
#   RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "episode_1.py"]
