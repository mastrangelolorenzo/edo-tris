FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY frame.py frame_service.py field.json ./
CMD ["python", "-u", "frame_service.py"]
