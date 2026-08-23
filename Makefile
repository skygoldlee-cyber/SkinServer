# SkinLens monorepo — 개발/배포 단축 명령
#
# 모든 기동 명령의 진실원본은 deploy/scripts/sl (bash) 이다.
# 이 Makefile 은 기존 습관(make dev-up 등)을 위한 얇은 래퍼다.
# Windows 네이티브에서는 deploy/scripts/sl.ps1 을 사용.
#
#   예) make dev-up      →  deploy/scripts/sl up dev
#       make logs        →  deploy/scripts/sl logs dev
#       make doctor      →  deploy/scripts/sl doctor dev

SL := deploy/scripts/sl

.PHONY: help \
	dev-up dev-down dev-build dev-logs \
	staging-up staging-down staging-logs \
	prod-up prod-down prod-logs \
	up down logs ps doctor init \
	smoke test itest

help:
	@echo "== 기동 (sl 래퍼) =="
	@echo "  dev-up / dev-down / dev-build / dev-logs"
	@echo "  staging-up / staging-down / staging-logs"
	@echo "  prod-up / prod-down / prod-logs"
	@echo "  up down logs ps doctor init   (ENV=dev|staging|prod, SVC=서비스명)"
	@echo "== 검증 =="
	@echo "  smoke / test / itest"

# ---- 개발 ----
dev-up:      ; $(SL) up dev
dev-down:    ; $(SL) down dev
dev-build:   ; docker compose -f deploy/compose/compose.base.yml -f deploy/compose/compose.dev.yml --env-file deploy/env/.env build
dev-logs:    ; $(SL) logs dev

# ---- 스테이징 ----
staging-up:   ; $(SL) up staging
staging-down: ; $(SL) down staging
staging-logs: ; $(SL) logs staging

# ---- 운영 ----
prod-up:      ; $(SL) up prod
prod-down:    ; $(SL) down prod
prod-logs:    ; $(SL) logs prod

# ---- 환경 가변 단축 (make up ENV=staging) ----
ENV ?= dev
up:     ; $(SL) up $(ENV)
down:   ; $(SL) down $(ENV)
logs:   ; $(SL) logs $(ENV) $(SVC)
ps:     ; $(SL) ps $(ENV)
doctor: ; $(SL) doctor $(ENV)
init:   ; $(SL) init $(ENV)

# ---- 엔드투엔드 스모크: 업로드 → job_id → 단계 타임라인 ----
# api vhost 로 본내기 위해 Host 헤더를 붙인다. 샘플 이미지는 tests/fixtures/sample.jpg.
H := -H Host:api.localhost
smoke:
	@echo "· 업로드"; \
	JOB=$$(curl -s $(H) -F "image=@tests/fixtures/sample.jpg;type=image/jpeg" http://localhost/analyze | python3 -c "import sys,json;print(json.load(sys.stdin)['job_id'])"); \
	echo "· job_id=$$JOB"; \
	for i in $$(seq 1 30); do \
	  ST=$$(curl -s $(H) http://localhost/jobs/$$JOB | python3 -c "import sys,json;print(json.load(sys.stdin).get('status',''))"); \
	  echo "  · $$ST"; [ "$$ST" = "done" ] && break; sleep 1; \
	done; \
	echo "· 단계 타임라인:"; \
	curl -s $(H) http://localhost/jobs/$$JOB/events | python3 -c "import sys,json;[print('   ',e['stage']) for e in json.load(sys.stdin)['events']]"

# ---- 단위 테스트(파트별, 인프라 불필요) ----
test:		## 단위(파트별, 인프라 불필요)
	python3 -m pytest -m "not integration"
itest:		## 통합(임시 Postgres 필요: DATABASE_URL)
	python3 -m pytest -m integration
