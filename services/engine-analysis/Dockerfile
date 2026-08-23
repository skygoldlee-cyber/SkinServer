FROM python:3.12-slim
WORKDIR /app
# opencv-python-headless 런타임 의존(libglib). GPU 전환 시 base 를 CUDA 계열로 교체.
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
# 폐쇄망: 포트 발행 안 함(내부 호출만).
RUN useradd -u 10001 -r -s /usr/sbin/nologin appuser
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
