FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
# 폐쇄망: 포트 발행 안 함(내부 호출만). GPU 사용 시 base 이미지를 CUDA 계열로 교체.
# (v3) 비루트 실행
RUN useradd -u 10001 -r -s /usr/sbin/nologin appuser
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
