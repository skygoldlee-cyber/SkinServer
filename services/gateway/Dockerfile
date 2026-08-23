FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
# (v3) 비루트 실행 — 컨테이너 탈출 시에도 host root 로 이어지지 않도록
RUN useradd -u 10001 -r -s /usr/sbin/nologin appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
