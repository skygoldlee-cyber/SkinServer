# followup-P1 — 후속 P1 배치 (①·②·③)

`08_최종리뷰/04_후속보완_로드맵.md`의 우선 3개를 실제 파일로 반영. 근거/우선순위는 그 로드맵 참고.

## 구성

| 파일 | # | 역할 | 배선 |
|---|---|---|---|
| `retention.py` | ① | 완료 원본 삭제 + 미완료 정리(Supabase service_role) | cron 에서 `docker compose run --rm worker python …` |
| `log-scrub.py` | ① | 앱 로그 토큰/URL/PII 마스킹 필터 (Caddy/gateway/worker) | 부팅 시 `install_scrubber()` |
| ~~`nginx-log-privacy.conf`~~ | ① | (사문화) nginx 제거로 대상 소멸 — 계획 §2 제거 대상 | — |
| `observability/logging_config.py` | ② | 구조적 JSON 로깅 + `job_id` 상관ID | 부팅 시 `setup_logging()` + `set_job_id()` |
| `observability/alert.sh` | ② | 디스크/VRAM/큐 임계 알림(webhook) | cron 5분 + deploy 실패 훅 |
| `observability/crontab.example` | ①② | 스케줄 예시 | `crontab -e` |
| `restore-rehearsal.sh` | ③ | 최신 백업 복구 + RPO/RTO 측정(스테이징) | 월 1회 수동 |
| `restore-rehearsal.md` | ③ | 복구 리허설 체크리스트·기록표 | 리허설 시 |

## 배선 요령

**① 개인정보**
- `retention.py`: 스키마 매핑 기본값은 실제 스키마(`deploy/db/migrations/0001_init.sql`의 `jobs.image_key`,
  status `queued/processing/done`)에 맞춰져 있다. 처음엔 `DRY_RUN=1`로 대상만 며칠 관찰 → 확인되면 `DRY_RUN=0`.
  presigned 발급 TTL 은 앱에서 15분(PRESIGN_EXPIRES_SEC).
- `log-scrub.py` + `logging_config.py`는 함께: JSON 로깅 핸들러에 스크럽 필터가 자동 부착됨.
- ~~`nginx-log-privacy.conf`~~ — nginx 스택 제거로 더 이상 배치하지 않는다(사문화).

**② 관측성**
- `setup_logging()`을 gateway/worker 진입점에서 1회 호출, 요청/잡 시작 시 `set_job_id(...)`.
- `alert.sh`는 `ALERT_WEBHOOK` 필수, `DATABASE_URL` 있으면 큐 점검까지. `nvidia-smi` 있으면 VRAM 점검.
- 배포 실패 알림: `deploy.sh` 롤백 분기에서 `ALERT_WEBHOOK=… followup-P1/observability/alert.sh` 호출하거나
  워크플로 `if: failure()` 스텝에서 webhook 전송.

**③ 백업 복구**
- 월 1회 스테이징에서 `restore-rehearsal.sh` → RPO/RTO 를 `restore-rehearsal.md` 표에 기록.
- 운영(Supabase)은 콘솔 PITR 로 별도 검증.

> 이 배치는 스텁/스켈레톤 포함(스키마·백업 형식은 환경별 TODO). 값만 채우면 동작하도록 구성.
