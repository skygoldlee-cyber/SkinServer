# 이야기(stories) — 변경 요약 (v2 + v3 + v4 + v4.1)

`이야기_보완개선_정리.md`의 12개 항목을 세 편 + 신설 허브에 반영했습니다. 문체는 그대로 두고
**정확성·일관성·완결성**만 손봤습니다. 항목별 적용 위치는 아래와 같습니다.

## 신설 파일

- **`README.md`** (허브) — 읽는 순서 · **공용 비유 사전** · 심화편 로드맵. (항목 3·8)
- **`변경요약.md`** — 이 문서(현 `docs/changelog/stories_변경요약.md`).

## 항목별 반영

| # | 심각도 | 항목 | 반영 위치 |
|---|---|---|---|
| 1 | 높음 | 비동기 Job 생애주기(주문 처리 순서) 추가 | 서버 이야기 **막 0-B 신설**(순서 다이어그램 + redis 역할(Phase 3 예정)) · 부록 C 링크 |
| 2 | 높음 | "창고" 용어 통일 | 세 편 전체 — **이미지 창고**(GHCR) / **데이터 창고=납품처**(Supabase) / **임시 냉장고**(로컬 db)로 고정 |
| 3 | 중간 | 흩어진 비유 사전 통합 | `README.md` 공용 비유 사전(우편함·화이트보드·중앙공장 포함), 각 편은 참조 |
| 4 | 중간 | 엔진 2개 관계(처방=독립 진입점) | 서버 이야기 등장인물표 + 막 0 + 막 0-B(분석/설문/PCR ≥1) |
| 5 | 중간 | 균일한 교차링크 + 심화편 로드맵 | 서버 이야기 서두 로드맵 note + 막 2·3·4·5 끝 "더 자세히 → 01" |
| 6 | 중간 | 이관/DB 정확성 정렬 | 서버 이야기 막 4·5, 배포 이야기 승격 — "임시 냉장고=스테이징 전용, 실장부=Supabase" 명시 |
| 7 | 낮음 | overview 막 6 다이어그램에 정적 경로 | 서버 이야기 막 6 그림 — 정적(rsync) 경로 + 이미지 창고 노드 추가 |
| 8 | 낮음 | `docs/stories/` 허브 신설 | `README.md` |
| 9 | 낮음 | 하드닝 막에 daemon.json 교차 | 서버 이야기 막 2 note |
| 10 | 낮음 | 손님 접점(앱=배달, 캐싱=단골 장부) | 서버 이야기 막 0 |
| 11 | 낮음 | 미러 모드 트레이드오프 · NAT IP 변동 | 구축 이야기 §6 갈림길 note |
| 12 | 낮음 | "비유(부품)" 첫 등장 병기 규칙 | 허브 사전에 규칙 명시 + 세 편 v2 노트에서 안내 |

## 용어 통일 결과(빠른 참조)

| 통일 용어 | 실제 부품 | 이전에 쓰이던 말 |
|---|---|---|
| 이미지 창고 | GHCR | 냉장창고 |
| 데이터 창고 = 납품처 | Supabase | 바깥 보관창고 · 바깥 창고 · 관리형 창고 · 전문 납품처 |
| 임시 냉장고 | 로컬 db(postgres, staging 전용) | 임시 창고 · 로컬 냉장고 · (연습 주방의) 냉장고 |

## 검증

- 세 편 + 허브에서 **옛 창고 용어 잔존 0건**.
- Mermaid 블록 14개 전부 **펜스 짝·괄호/따옴표 균형 OK**.
- 사실 정합성: 막 0-B는 `../architecture/SkinLens_서버구성_적합성_검토.md` 부록 C 시퀀스, 처방 독립 진입점은 `../../services/engine-prescription/`,
  임시 냉장고=staging 프로파일은 `../../deploy/compose/compose.staging.yml`과 대조 확인.

---

## v3 — 폴더구조 반영 (경로 갱신)

문서세트가 단일 **monorepo** 로 재구성되면서, 세 편 + 허브의 **문서·코드 경로 참조**를 현행 구조로 맞췄습니다.
문체·비유·다이어그램은 그대로 두고 **가리키는 위치만** 갱신했습니다(옛 번호 폴더 → 현재 위치).

| 옛 표기 | 현재 위치 |
|---|---|
| `04_이야기/` | `docs/stories/` |
| `01/windows11_ubuntu_server_setup.md`, `01/server_migration_runbook.md` | `../server-setup/` |
| `01`의 `verify_*`·`pg_backup.sh`·`wsl-backup-task.ps1`·`migrate_*`·`deploy.sh` | `../../deploy/scripts/` |
| `test_environment.py` | `../../tests/test_environment.py` |
| `02_적합성검토` (부록 B·C) | `../architecture/SkinLens_서버구성_적합성_검토.md` |
| `03_webstack_스캐폴드` | `../../deploy/compose/`·`../../deploy/nginx/`·`../../services/`·`../../apps/` |
| `05_CD_배포` | `../../deploy/`(scripts·compose·env·supabase·ops-jobs)·`../../.github/workflows/` |
| `08_최종리뷰` | `../architecture/`·`../roadmap/04_후속보완_로드맵.md` |

> 전체 옛→새 매핑 표는 허브 `README.md`의 **"세부 문서 위치(현행 monorepo 구조)"** 절에 있습니다.

### v3.1 — 비유 정합성 마무리 · 심화편 확장

- **다중 레포 표현 정리:** 사전만이 아니라 **본문·다이어그램까지** "공방=레포"·"서비스별 레포" → **"공방=서비스 경로"·"경로 필터(`on.push.paths`)"** 로 맞췄습니다(배포·서버 이야기 본문, 구축 §4 우편함 서사). `deploy.sh`·`.env.images`·`verify_server.sh` 같은 **부품 이름**은 비유 매핑이라 경로로 바꾸지 않고 그대로 둡니다.
- **사실 정합성:** 엔진 GPU는 상시가 아니라 **CPU baseline + `compose.gpu.yml` 옵트인**임을 서버 이야기 막 0에 caveat으로 명시(감사 `../architecture/01_SkinLens_운영아키텍처_최종리뷰.md §①-A`와 정렬). 막 0-B에 **등급→비율 구간(예)** 한 줄 추가.
- **심화편 확장:** overview에만 요약돼 있던 **막 2(하드닝)·막 5(이관)** 를 심화편으로 신설 — `SkinLens_하드닝_이야기.md`·`SkinLens_이관_이야기.md`. 이제 네 막(구축·하드닝·이관·배포)에 심화편이 있고, 운영·백업은 overview 한 막씩으로 남습니다.

---

## v4 — 통합 기동 CLI(`sl`) 도입 · 기동 이야기 신설

환경(dev/staging/prod)마다 다른 compose 조합을 외워야 한다는 복잡성 진단(`../../plans/improve-startup-ux.md`)에 따라 **"어느 환경이든 같은 동사"** 를 주는 통합 CLI를 도입하고, 그 흐름을 이야기 한 편으로 엮었습니다.

**신설 파일:**

| 파일 | 내용 |
|---|---|
| `../../deploy/scripts/sl` · `sl.ps1` | 통합 기동 CLI(bash/PowerShell) — `up/down/logs/ps/doctor/init/deploy` 동사 통일, 환경 생략 시 실행 중 컨테이너로 추론, `up prod` 전 doctor 자동 게이트 |
| `SkinLens_기동_이야기.md` | 연습 주방(dev)·리허설 주방(staging)·영업점(prod) 3막 — `sl`=총지배인, `doctor`=개업 전 점검 비유 |
| `../operations/환경별_빌드_기동_절차.md` | 환경 비교 표 + `sl` 사용법 + 부록 A(긴 compose one-liner) |
| `../../plans/improve-startup-ux.md` | 복잡성 진단 5가지 → 개선안 → 수용 기준(전부 ✅) |

**갱신된 기존 문서:**

- 루트 `Makefile` — sl 호출 **얇은 래퍼**로 슬림화(`dev-up`·`staging-up`·`prod-up`·`up ENV=`·`doctor`).
- 루트 `README.md` — 빠른 시작(`sl init dev` → `sl up dev`)·배포(`sl deploy`) 절을 sl 기준으로.
- `../operations/서버_실행_운영_가이드.md` — §4·§5 실행/로그/정지/승격 절을 `sl up/logs/down/deploy` 기준으로.
- 허브 `README.md` — 읽는 순서에 기동 이야기 추가, 심화편 로드맵에 "기동" 행 추가, 배포 캐스트 사전에 **총지배인 | `deploy/scripts/sl`** 추가.
- `../MANIFEST.md` — Makefile 설명을 "sl의 얇은 래퍼"로, stories·operations·deploy/scripts 표에 신설 파일 행 추가.
- `../README.md` — ③ 구현의 실행 절과 상황별 라우터("실제로 띄워 보기")를 sl 기준으로.

---

## v4.1 — 정합성 정리

허브 README와 01 서버 이야기 간 심화편 개수 불일치를 정리했습니다.

| 항목 | 내용 |
|---|---|
| 문제 | 허브는 "6막 전체 심화편 완비"로 안내하나, 01은 "네 편"으로 구버전 표기 잔존 |
| 조치 | 01 서버 이야기 서두를 **"구축·하드닝·운영·백업·이관·배포" 여섯 편**으로 갱신 |
| 확인 | stories 폴터 01~10 전편 존재, 허브 로드맵과 01 링크 일치 확인 |
