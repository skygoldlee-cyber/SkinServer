# 외주개발사 인도 문서 패키지 (HANDOFF)

> 목적: 외부 전문 개발사에 인도할 문서를 **목적별 패키지**로 묶고, 각 문서의 전달 이유와 권장 전달 방식을 명시한다.
>
> 중심 계약 문서는 [`skinlens_outsourcing_srs.md`](./skinlens_outsourcing_srs.md)(SRS — "무엇을(요구)")이고,
> 이 패키지는 그 SRS를 뒷받침하는 **"어디에·어떤 상태로·어떻게 검증할지"** 자료다.
> 모든 문서는 [`MANIFEST.md`](../MANIFEST.md)에 등록된 정본이다.

> [!IMPORTANT]
> **읽기 전 과도기(transition) 메모 — nginx → Caddy 이주 중.**
> 현재 3-Tier 이전이 진행 중이라, 설계·작업계획·운영 문서 일부에 **`deploy/nginx/`(레거시)와 Caddy/gateway(신규) 참조가 공존**한다.
> 최신 방향은 **Caddy + gateway**(엣지·보안 헤더·rate-limit 책임이 nginx에서 이주 중)이며, `deploy/nginx/`는 제거 예정 자산이다([`MANIFEST.md`](../MANIFEST.md) `deploy/nginx/` 항목 참조).
> 문서마다 이주 상태 표기가 다를 수 있으니, 상충해 보이면 **작업계획 [`architecture/05_3Tier_이전_작업계획.md`](../architecture/05_3Tier_이전_작업계획.md)의 책임 이주 표**를 기준으로 판단한다.

---

## ① 필수 — 설계 정본·작업 범위 (계약서 부속)

| 문서 | 전달 이유 |
|---|---|
| [`architecture/04_3Tier_Vercel_Supabase_AIServer_설계.md`](../architecture/04_3Tier_Vercel_Supabase_AIServer_설계.md) | **3-Tier 재편 설계 정본.** Vercel·Supabase·AI Server 3분할의 "왜/무엇" — 아키텍처 규칙의 근거 |
| [`architecture/05_3Tier_이전_작업계획.md`](../architecture/05_3Tier_이전_작업계획.md) | Phase 1~6별 "무엇을·어느 파일을·어떤 순서로" + 상태 스냅샷 — 작업 범위(SoW)의 뼈대 |
| [`roadmap/00_PHASE_ROADMAP.md`](../roadmap/00_PHASE_ROADMAP.md) | **Phase 라벨 ↔ 구현 우선순위 ↔ 현재 반영 상태** 매핑 — 다른 문서의 "Phase N" 참조 해소 |
| [`roadmap/05_보완항목_정리.md`](../roadmap/05_보완항목_정리.md) | **남은 보완항목 도메인별 정리** — 미완 범위(D4 믹스표·P1-3·DR 리허설 등)를 계약 경계로 명시 |

## ② 필수 — API·데이터 계약

| 문서 | 전달 이유 |
|---|---|
| [`integration/flutter_app_contract.md`](../integration/flutter_app_contract.md) | **Flutter 앱 ↔ 서버 계약.** `POST /analyze`·설문 shape·폴리·오류 코드·Dart 예시 — SRS §4 API 명세의 실무 상세 |
| [`architecture/03_DB_MIGRATION_ROLLBACK.md`](../architecture/03_DB_MIGRATION_ROLLBACK.md) | "코드 롤백 ≠ 스키마 롤백" 런북(expand-contract) — SRS §3.4 DB 이관의 안전 규칙 |

## ③ 필수 — 엔진 도메인 (SRS §3.3 고도화의 실무 지도)

| 문서 | 전달 이유 |
|---|---|
| [`roadmap/engine_advancement_roadmap.md`](../roadmap/engine_advancement_roadmap.md) | **엔진 고도화 로드맵.** Heuristic 튜닝·딥러닝 통합·피드백 루프의 단계별 전략 + 구체적 코드 교체 지점 |
| [`architecture/엔진_baseline_교체_가이드.md`](../architecture/엔진_baseline_교체_가이드.md) | 엔진 baseline(OpenCV/규칙) → ML/GAN 교체 지점 가이드 |

## ④ 실행·검증 환경 (로컬/스테이징에서 돌릴 때)

| 문서 | 전달 이유 |
|---|---|
| [`operations/서버_실행_운영_가이드.md`](../operations/서버_실행_운영_가이드.md) | 실제 실행/운영 절차(기동·상태 확인·일상 운영, `sl` 기준) |
| [`operations/환경별_빌드_기동_절차.md`](../operations/환경별_빌드_기동_절차.md) | **환경별 빌드·기동 절차 정본.** dev/staging/prod 비교 + `sl init`/`doctor` |
| [`operations/09_Phase1_Supabase_실행런북.md`](../operations/09_Phase1_Supabase_실행런북.md) | **Phase 1 실행 런북.** Supabase 생성·스키마·RLS/Storage 정책 적용·`.env` 채우기 |
| [`operations/파이프라인_체크포인트_트러블슈팅.md`](../operations/파이프라인_체크포인트_트러블슈팅.md) | 업로드→분석→처방 단계별 체크포인트·장애 진단 |
| [`operations/11_원격_모니터링_제어.md`](../operations/11_원격_모니터링_제어.md) | Windows→Linux 원격 운영(`remote.ps1`) — 원격 협업·상태 확인용 |

## ⑤ 코드 품질 기준선 (인수인계 시점의 상태)

| 문서 | 전달 이유 |
|---|---|
| [`review/REVIEW_FINDINGS_2026-08-19.md`](../review/REVIEW_FINDINGS_2026-08-19.md) | **2차 검수.** 해결/미해결 지적 + 강점(유지할 것) — "손대지 말아야 할 보장" 목록 |
| [`review/RESOLUTIONS_2026-08-19.md`](../review/RESOLUTIONS_2026-08-19.md) | **해결 기록.** 이미 반영된 P1/P2/N 항목 — 중복 작업 방지 |
| [`roadmap/04_후속보완_로드맵.md`](../roadmap/04_후속보완_로드맵.md) | 주제별 백로그 + 우선 3개 반영 위치 |

## ⑥ 선택 — 비기술 배경 (이해 돕기, 필수 아님)

| 문서 | 전달 이유 |
|---|---|
| [`stories/README.md`](../stories/README.md) + [`stories/01_SkinLens_서버_이야기.md`](../stories/01_SkinLens_서버_이야기.md) | 전체 여정을 "작은 식당"으로 푼 overview — 비기술 stakeholder·온보딩 초기 큰그림 파악용 |
| [`operations/06_운영·배포_체크리스트.md`](../operations/06_운영·배포_체크리스트.md) | 배포·운영·하드닝·백업 체크리스트 — 인수 검증 시 나침반 |

---

## 권장 전달 방식

- **계약 부속(법적 구속력)** — ①②③: 설계 정본·API 계약·작업 범위·미완 경계를 확정.
  특히 [`roadmap/05_보완항목_정리.md`](../roadmap/05_보완항목_정리.md)로 "미완 범위"를 명시하면 범위 분쟁을 예방할 수 있다.
- **기술 인도 패키지** — ④⑤: 개발사가 환경을 띄우고 기준선 품질을 파악하는 실무 자료.
- **참고 자료** — ⑥: 큰그림 이해용(필수 아님).

## 인도 체크리스트

- [ ] SRS([`skinlens_outsourcing_srs.md`](./skinlens_outsourcing_srs.md)) 최신본 공유
- [ ] ①②③ 계약 부속 패키지 전달·합의
- [ ] ④⑤ 기술 인도 패키지 전달(레포 접근 권한 포함)
- [ ] 미완 범위(05_보완항목_정리) 양측 서명으로 경계 확정
- [ ] Supabase 프로젝트·`.env` 실값은 별도 보안 채널로 전달(본 문서에 포함 금지)
