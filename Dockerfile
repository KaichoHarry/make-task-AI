FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# python -u を使うことで、ログをリアルタイムで出力させます
CMD ["python", "-u", "app/main.py"]