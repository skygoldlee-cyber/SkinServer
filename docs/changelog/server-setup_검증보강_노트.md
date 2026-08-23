# 검증 보강 노트 — 하드닝·운영 검증 자동화

기존 검증(설치·구축·네트워크·이관·배포·백업)은 잘 갖춰져 있었으나, **하드닝을 "적용했는지
즉시 확인"하는 게이트가 없고**, 게이트 루프가 구축 10장에서 끊기며, 운영 점검이 수동 목록이었습니다.
아래 3가지로 보강해, "설치→구축→**하드닝**→네트워크→구현→**운영·백업**→이관→배포" 전 구간을
동일한 게이트 방식으로 검증합니다.

## 1. `verify_server.sh` 에 `hardening` 모듈 추가

서버측에서 검증 가능한 하드닝을 PASS/FAIL/WARN 로 확인합니다.

- `sshd -T` 실제 적용값 — `passwordauthentication no`·`permitrootlogin no`·`MaxAuthTries<=4`
  (편집만 하고 reload 안 한 "껐다고 착각" 케이스를 잡음, 5-3·6-4)
- 민감 포트(5432/8000/8080/3001)가 `0.0.0.0` 으로 발행됐는지 — ufw 우회 함정의 **서버측 탐지**(9-3-1·20-2)
- 컨테이너 하드닝 — `no-new-privileges`·mem 상한·비루트(9-4). 적용 0건이면 FAIL
- fail2ban 동작(WSL NAT면 의도적 미사용일 수 있어 WARN)

> 외부 실차단(다른 PC→서버)은 `verify_client.ps1 -Check ports`(또는 `nc -vz`)가 담당.
> `hardening` 은 `all` 에 포함하지 않습니다(구축 중 실행 시 하드닝 전이라 오탐 방지 → **별도 게이트**).

## 2. §11 검증 게이트 루프 연장

기존엔 3~10장만 "PASS→다음/FAIL→복귀" 게이트였고 이후는 체크리스트뿐이었습니다.
Mermaid와 §15 순서표에 **하드닝·백업·운영 게이트**를 이어 붙였습니다.

- 20장(하드닝) 후 → `./verify_server.sh hardening` (+ 다른 PC `verify_client -Check ports`)
- 18장(백업) 후 → 복구 리허설(18-3 임시 DB 복원 성공)
- 16장(부팅·운영) 후 → 재부팅 자동복구(`verify_server all` + `verify_client`)

## 3. `verify_ops.sh` 신설 — 운영 점검 자동화

§21의 재부팅 후/정기 점검 13항목을 실행 가능한 스크립트로 묶었습니다.

- **recovery** 컨테이너 Up·재시작 정책 · **backup** 백업 신선도(≤N일)·오프사이트·암호화·WSL 스냅샷·리허설 리마인더
- **resource** 디스크 임계·portproxy(NAT) · **update** 보안 업데이트·fail2ban·인증서
- `--with-hardening` 로 끝에 `verify_server.sh hardening` 위임 실행
- 종료 코드(FAIL=0→0) 로 cron/스케줄러 연동 가능

> 보안 항목은 1의 hardening 모듈이 단일 출처이고, `verify_ops.sh` 는 운영 건강도에 집중해 중복을 피합니다.
