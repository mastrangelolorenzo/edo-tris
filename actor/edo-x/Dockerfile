# build context: ./actor (serve anche edo-common)
FROM python:3.12-slim
# pynput (usato da pyedo per la tastiera) senza display: backend dummy, niente evdev da compilare
ENV PYNPUT_BACKEND=dummy
WORKDIR /app
COPY edo-common/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir --no-deps pynput==1.8.1
COPY edo-common/edo.py edo-x/edo_x.py ./
CMD ["python", "-u", "edo_x.py"]
