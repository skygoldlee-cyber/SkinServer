FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY worker.py logging_setup.py ./
# (v3) 비루트 실행
RUN useradd -u 10001 -r -s /usr/sbin/nologin appuser
USER appuser
CMD ["python", "-u", "worker.py"]
