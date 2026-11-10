FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY edo_x.py .
CMD ["python", "-u", "edo_x.py"]
