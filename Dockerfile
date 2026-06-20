# Python 3.13 ကို သုံးမယ်
FROM python:3.13-slim

# Working Directory သတ်မှတ်မယ်
WORKDIR /app

# Requirements တွေ Install လုပ်မယ်
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Project Files အကုန်ကူးမယ်
COPY . .

# Bot ကို Run မယ်
CMD ["python", "main.py"]
