# SkinLens 운영 아키텍처 최종 리뷰

> 대상: `deploy/compose/compose.base.yml` · `deploy/scripts/deploy.sh` · `deploy/nginx/*` · `deploy/env/.env*` · `deploy/nginx/.htpasswd`
> + `.github/workflows/`(build-and-deploy-engine · deploy-built-service · deploy-static)
> + `SkinLens_서버구성_적합성_검토.md` · `docs/server-setup/` 대조.
>
> 이번 리뷰는 "이야기(설계 서사)"가 아니라 **실제로 배포되는 설정 파일**을 기준으로 한다.
> (이 monorepo에는 `../stories/` 서사 문서와 `services/`·`deploy/` 구동 코드가 모두 채워져 있다.
>  본 리뷰는 서사가 아니라 실제 배포 설정/코드 아티팩트를 기준으로 한다.)

---

## 0. 이전 총평과의 차이 — 먼저 정리

앞선 총평은 서사 문서 기준이라 지금 세트와 몇 군데 어긋난다. 실제 아티팩트로 확인한 결과:

- **포트 외부 노출은 이미 안전하다.** compose에서 `ports:`를 발행하는 서비스는 `nginx`(80)뿐이다. gateway/engine/redis(Phase 3 예정)/db는 포트 미발행(db는 `127.0.0.1:5432` 주석 처리). 총평이 우려한 `8000:8000` 무심코 노출은 이 세트엔 없다. → **표는 문서화 목적이면 좋되, 결함은 아님.**
- **GPU 완화 전략은 문서에 있다.** `SkinLens_서버구성_적합성_검토.md §7`이 로드/언로드·동시성=1 직렬화·워크로드 분리를 이미 제시한다. 다만 **compose에는 GPU 할당 자체가 없다**(아래 ①-A — 이게 진짜 문제).
- **DB 마이그레이션 가이드도 부분적으로 있다.** `deploy/db/README.md`가 build↔deploy 사이 `alembic upgrade head` + expand-contract를 권한다. 다만 **(리뷰 시점) 워크플로에 배선되지 않았고, 롤백 정책이 없다**(③-B).
- **PIPA/보존/presigned도 서사엔 있다.** `SkinLens_서버구성_적합성_검토.md §5/§8`, `../changelog/server-setup_보완개선_v3_노트.md`(피부 이미지 평문 우려·보존 하한). 다만 **실행 아티팩트(RLS SQL·보존 잡·presigned 구현)가 세트에 없다**(②-G).

요약하면, 이 세트의 남은 과제는 대부분 **"문서에는 있으나 설정/코드로 배선되지 않음"**이다. 개념 설계는 성숙했고, 지금은 **구현 정합성** 단계다.

---

## ① 구조상 문제

**A. GPU가 compose에 전혀 할당되지 않는다 — 이번 리뷰 최상위 발견.**
`engine-analysis`/`engine-prescription`에 `# ★ GPU 워크로드` 주석과 `mem_limit: 2g`만 있고, `deploy.resources.reservations.devices`(nvidia)·`gpus: all`·`runtime: nvidia` 어느 것도 없다. 지금 이 compose로 뜨면 **두 엔진은 CPU로 돈다.** 즉 §7의 VRAM 경합 논의는 현재 산출물에선 작동조차 하지 않는다. → GPU를 쓸 것인지 먼저 확정하고, 쓴다면 반드시 배선해야 한다. 안 쓸 거면 "GPU 엔진" 표기를 문서에서 내려야 한다(동작=문서 불일치 해소).

**B. gateway가 enginenet에 붙어 있다.**
`gateway.networks: [frontnet, appnet, enginenet]`. 설계상 엔진을 부르는 주체는 worker인데, gateway까지 폐쇄망에 들여놓으면 Case A의 "엔진 접점 최소화" 취지가 약해진다. gateway가 실제로 엔진을 직접 프록시하지 않는다면 `enginenet`에서 제외하는 편이 신뢰경계에 맞다. 직접 호출한다면 그 이유를 문서에 남길 것.

**C. worker 헬스체크가 "파일 존재"다.**
`test -f /tmp/worker_alive`(+ `read_only: true`/`tmpfs: /tmp`). 파일이 한 번 생기면 **워커가 멈춰도 healthy로 보인다**(신선도 없음). 하트비트 mtime(최근 N초 이내) 또는 큐 폴링 성공을 조건으로 바꿔야 "조용한 정지"를 잡는다.

**D. 정적 사이트가 별도 컨테이너 2개.**
homepage/devpage가 각자 `nginx:alpine`로 뜨고 엣지 nginx가 다시 프록시한다(홉 추가). 엣지 nginx에 bind-mount로 직접 서빙하면 컨테이너 2개를 줄일 수 있다. 선택 사항(성능/단순화).

**E. 마이그레이션 실행 지점이 불명확.**
워크플로에 마이그레이션 스텝이 없어, 실제로는 이미지 시작 시 암묵 실행될 가능성이 크다(순서·실패 처리 미정의). ③-B와 함께 다뤄야 한다.

---

## ② 보안 취약점

**A. TLS 부재 (실사용 전 최우선).**
compose는 `80`만, `443`·HSTS·dev basic-auth 전부 평문 경로다. SkinLens는 **피부 사진(민감 개인정보)**을 다루므로, 실사용자 오픈 전 **엔드투엔드 HTTPS는 협상 불가**다. Caddy(자동)/certbot이 "이후 적용"으로만 언급되어 있는데, 이를 **런치 게이트**로 승격할 것.

**B. dev basic-auth가 평문 + `.htpasswd` 커밋.**
`deploy/nginx/.htpasswd`(운영용 실제 파일)이 레포에 커밋되면 안 된다 — 현재 저장소엔 `deploy/nginx/.htpasswd.example`만 두고, apr1(MD5-crypt)은 오프라인 크랙이 쉬우므로 bcrypt로 발급한다. TLS 없이 basic-auth면 자격증명이 평문 전송이다. → 실제 `.htpasswd` 커밋 제외(.gitignore) + bcrypt 재발급 + `deploy/nginx/conf.d/dev.conf`의 `allow/deny` IP 화이트리스트 활성.

**C. compose 기본값에 약한 비밀.**
`DATABASE_URL` 기본 폴백 `...:app_pw@db:...`, `REDIS_URL` 기본값 등이 스테이징 편의로 박혀 있다(REDIS_URL은 현재 제거, Phase 3 예정). 운영에서 값 누락 시 이 폴백으로 조용히 뜨지 않도록, `DATABASE_URL` 미설정이면 **fail-fast** 처리를 권한다.

**D. 운영 VPS 위의 self-hosted 러너.**
러너가 레포 코드를 실행하고 `docker build .`까지 **운영 호스트에서** 수행한다. 잘한 점: 트리거가 `push`/`workflow_dispatch`뿐이라 **fork PR RCE 경로가 없다**. 보강: `environment: production` 승인 게이트를 "선택"→**필수**로, 러너는 전용 비루트 사용자·격리(가능하면 ephemeral), main push 권한 최소화.

**E. 이관 번들에 `.env` 평문 포함.**
`migrate_export.sh` 산출 tgz에 `.env`+DB덤프가 들어간다(MANIFEST가 "암호화 전송" 경고). 경고를 정책으로: 전송 암호화 + 사용 후 안전 삭제 + 비밀 포함 tgz를 디스크에 방치 금지.

**F. CSP 없음 / 업로드 경로 전용 제한 없음.**
`security-headers.conf`에 nosniff·X-Frame-Options·Referrer-Policy는 있으나 **CSP 없음**(HTML 표면 XSS 완화 약화), HSTS는 TLS 후 개방. 업로드는 일반 존(10r/s)만 적용 — 스토리지 채우기 남용 방지를 위해 업로드 엔드포인트에 **더 강한 limit + 인증**을 권한다.

**G. Supabase Storage RLS/정책 아티팩트 부재.**
"사용자 A가 B의 사진 접근 불가"는 산문으로만 존재한다. 실제로는 **RLS 정책 + Storage 정책 + object-key 스코핑** SQL이 세트에 있어야 강제된다. 지금은 코드로 담보되지 않는다.

---

## ③ 실제 장애 가능성

**A. `.env.images` 쓰기 경쟁(레이스).**
engine-analysis/engine-prescription 워크플로는 monorepo 안에서 경로 필터(`on.push.paths`)로 **독립 트리거**되므로 두 엔진 배포가 **동시에 실행될 수 있다**. 두 배포가 동시에 같은 `deploy/env/.env.images`를 read-modify-write하면 태그가 유실되거나 롤백 기준값이 깨진다. 리뷰 시점 `deploy.sh`엔 파일 락이 없었다. → **`flock` 한 줄**로 큰 위험을 막을 수 있다(④에 스니펫; 현재 `deploy/scripts/deploy.sh`에 반영됨).

**B. 마이그레이션 ↔ 이미지 롤백 불일치.**
`v1→(migrate)→v2`에서 v2 실패 시 이미지만 v1로 돌려도 **스키마는 v2**다. v1 코드가 없는 컬럼/제약을 만나 크래시 루프 → 헬스체크 실패 → "이미지 롤백 성공"인데 서비스는 계속 다운. → **하위호환 마이그레이션(expand-contract)만 허용** + "코드 롤백 ≠ 스키마 롤백"을 런북에 명문화.

**C. GPU 활성화 시 OOM.**
①-A를 배선하되 동시성 제어 없이 두 엔진+모델을 한 카드에 올리면 부하 시 VRAM OOM(§7 예측)이 난다. **동시성=1·직렬화(analysis→prescription)**를 먼저 넣고 GPU를 켤 것.

**D. 워커 거짓 healthy(①-C).**
멈춘 워커가 healthy로 남으면 **잡이 조용히 적체**되어 사용자 분석이 영영 끝나지 않는다. 신선도 기반 헬스체크로 교정.

**E. WSL2를 운영으로 쓰는 순간의 함정(문서화됨).**
sleep 후 시계 드리프트, NAT에서 fail2ban 원본 IP 상실, idle 타임아웃 — 모두 setup 가이드가 이미 경고. **"WSL=스테이징 전용, 운영=VPS"를 불변 규칙으로** 문서 앞단에 선언.

**F. 배포 후 `docker image prune -f` — 안전 확인됨.**
sha 태그 이미지는 dangling이 아니라 prune(dangling 전용)에 안 지워진다 → 롤백 대상 보존. **조치 불필요(정상 설계).**

**G. 최초 부팅이 `:latest`.**
`.env.images.example`의 엔진 기본값이 `:latest`(가변) → 최초 운영 부팅이 재현 불가 상태. **첫 운영 부팅은 sha 고정** 권장.

---

## ④ 개선안 (핵심 스니펫)

**GPU 배선 + 동시성 제한(엔진 각각):**
```yaml
  engine-analysis:
    # ...
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: ["gpu"]
    environment:
      ENGINE_MAX_CONCURRENCY: "1"   # 직렬화로 VRAM 경합 회피
```
(Compose v2 `deploy.resources`가 안 먹으면 `gpus: all` 또는 `runtime: nvidia`로. WSL은 `docs/server-setup/windows11_ubuntu_server_setup.md §26` NVIDIA Container Toolkit 선행.)

**`deploy.sh`에 파일 락 추가(레이스 방지):**
```bash
exec 9>"$ENV_DIR/.env.images.lock"
flock 9            # 동시 배포 직렬화 — 크리티컬 섹션 진입
```

**워크플로에 마이그레이션 스텝(build↔deploy 사이, gateway/worker):**
```bash
docker compose --env-file .env --env-file .env.images run --rm gateway alembic upgrade head
# 실패 시 배포 중단. 마이그레이션은 하위호환(추가→백필→전환→정리)만 허용.
```

**워커 헬스체크(신선도):**
```yaml
    healthcheck:
      test: ["CMD-SHELL", "find /tmp/worker_alive -mmin -1 | grep -q ."]
```

그 외: TLS(Caddy 자동 or certbot)→HSTS 개방→basic-auth를 TLS 뒤로, `.htpasswd` 커밋 중단·bcrypt·dev IP 화이트리스트; Supabase RLS+Storage 정책 SQL·presigned 업로드(TTL 5~10분)·보존 잡(MIN_KEEP + 리포트 생성 후 원본 자동 삭제)·로그 스크러빙(URL/토큰/PII 미기록); 운영 승인 게이트 필수화·전용 러너 사용자; gateway를 enginenet에서 제외(정당화 없으면).

---

## ⑤ 우선순위 (P0 / P1 / P2)

| 우선 | 항목 | 근거 |
|---|---|---|
| **P0** | 엔드투엔드 TLS(443·HSTS·basic-auth를 TLS 뒤로) | 민감 개인정보(피부 사진) 평문 전송 차단 — 실사용 오픈 게이트 |
| **P0** | Supabase RLS + Storage 접근 정책(SQL) | 교차 사용자 접근 차단이 코드로 담보돼야 함(②-G) |
| **P0** | GPU 정책 확정 + 배선(또는 CPU-only로 명시) | 현재 동작(CPU) ≠ 문서(GPU). ①-A |
| **P0** | 마이그레이션 vs 롤백 정책(expand-contract + "코드≠스키마" 런북) | 롤백해도 서비스 다운되는 실장애(③-B) |
| **P1** | `deploy.sh`에 `flock`(.env.images 레이스) | 동시 엔진 배포 시 태그 유실/롤백 기준 파손(③-A) |
| **P1** | 이미지/PII 보존·자동삭제 + presigned TTL + 로그 스크러빙 | PIPA 운영 담보(②-G 실행편) |
| **P1** | 운영 승인 게이트 필수화 + 러너 하드닝 | 운영 호스트 위 코드 실행 리스크(②-D) |
| **P1** | 워커 신선도 헬스체크 | 잡 조용한 적체 방지(①-C·③-D) |
| **P1** | `.htpasswd` 커밋 중단·bcrypt·dev IP 화이트리스트 | 자격증명 노출·평문 basic-auth(②-B) |
| **P2** | CSP 헤더 + 업로드 경로 전용 rate limit | XSS 완화·스토리지 남용 방지(②-F) |
| **P2** | gateway를 enginenet에서 제외(또는 문서화) | 엔진 신뢰경계 최소화(①-B) |
| **P2** | 최초 운영 부팅 이미지 sha 고정(`:latest` 금지) | 재현성(③-G) |
| **P2** | 이미지 서명/프로버넌스(cosign)·SBOM | 공급망 보강 |
| **P2** | `DATABASE_URL` 미설정 fail-fast·약한 기본값 제거 | 운영 오폴백 방지(②-C) |
| **P2** | 정적 사이트를 엣지 nginx로 통합 | 컨테이너/홉 축소(①-D, 선택) |

---

## 총괄

전체 그림(WSL 스테이징 → VPS 운영 → GHCR → self-hosted 러너 → 헬스 게이트 → 태그 롤백, enginenet 폐쇄망, Postgres 원장(Redis 신호 분리는 Phase 3 예정), 비동기 Job)은 **일관되고 성숙**하다. read_only·cap_drop·no-new-privileges가 전 서비스에 적용됐고, self-hosted 러너에 `pull_request` 트리거가 없는 것도 옳은 판단이다.

남은 건 **"산문 → 배선"**이다. 특히 **①-A(GPU 미배선)**, **③-B(마이그레이션 롤백)**, **②-A(TLS)**, **②-G(RLS/보존 아티팩트)** 네 가지가 개념과 실제 산출물 사이의 가장 큰 간극이며, 실사용자 오픈 전에 닫아야 한다.
