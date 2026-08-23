# Vercel + Render 기반 웹서비스 도메인 및 IP 구성 가이드

## 1. 결론 요약

프론트엔드를 **Vercel**, 백엔드를 **Render**에서 운영하는 경우:

- 도메인 업체(가비아 등)에 가입하는 목적은 **IP 확보가 아니라 도메인 등록**이다.
- 별도의 **고정 IP를 직접 구매하거나 서버 IP를 확보할 필요가 없다.**
- Linux 서버, Nginx, 방화벽 등을 직접 구축·관리할 필요도 없다.
- 다만 특정 외부 시스템의 IP Allowlist 등 특별한 요구사항이 있다면 별도의 네트워크 구성이 필요할 수 있다.

> **핵심: 가비아 가입 = 도메인 확보, IP 확보 아님**

---

## 2. 전체 아키텍처

CoteLeaf를 예시로 한 권장 구성은 다음과 같다.

```text
                         Internet
                            │
                            ▼
                     Cloudflare DNS
                       │         │
                       │         │
                       ▼         ▼
                    Vercel     Render
                   Frontend   Backend API
                       │         │
                       └────┬────┘
                            │
                            ▼
                         Supabase
                     DB / Auth / Storage
```

### 서비스별 주소 및 역할

| 구성요소 | 주소 예시 | 역할 |
|---|---|---|
| Frontend | `https://www.coteleaf.com` | Vercel에서 호스팅 |
| Backend API | `https://api.coteleaf.com` | Render에서 호스팅 |
| Database | Supabase | PostgreSQL / Auth / Storage |
| Domain | `coteleaf.com` | 도메인 등록기관에서 등록 |
| DNS | Cloudflare | 도메인 연결 및 DNS 관리 |

---

## 3. IP 주소를 직접 확보할 필요가 없는 이유

### 3.1 Vercel (Frontend)

Vercel은 글로벌 인프라와 CDN을 사용하므로 일반적인 웹서비스 운영에서는 서버의 고정 IP를 직접 관리할 필요가 없다.

```text
사용자 → www.coteleaf.com → Vercel → Frontend
```

### 3.2 Render (Backend)

Render 역시 클라우드에서 백엔드 서비스를 운영하며 기본 제공 주소를 사용할 수 있다.

```text
https://your-backend.onrender.com
```

커스텀 도메인 연결 후:

```text
https://api.coteleaf.com
```

따라서 일반적인 Vercel + Render 구성에서는 서버의 고정 공인 IP를 직접 확보할 필요가 없다.

---

## 4. 도메인 등록기관(Registrar)의 역할

가비아, 후이즈, 카페24, Cloudflare Registrar 등은 **도메인 등록기관**이다.

다음과 같은 주소를 사용하려면 해당 도메인을 등록해야 한다.

```text
coteleaf.com
coteleaf.co.kr
```

도메인 등록 후 DNS 설정을 통해 Vercel과 Render로 연결한다.

> **도메인 등록 = 인터넷에서 사용할 주소를 확보하는 것**
>
> **고정 IP 확보 = 서버의 네트워크 주소를 직접 확보하는 것**
>
> 두 가지는 서로 다른 개념이다.

---

## 5. DNS 연결 구성

`coteleaf.com`을 등록했다고 가정할 때:

### 연결 구조

```text
www.coteleaf.com    → Vercel  (Frontend)
api.coteleaf.com    → Render  (Backend)
```

### DNS 레코드 설정

실제 DNS 레코드의 종류와 대상 값은 **Vercel 및 Render의 도메인 설정 화면에서 현재 안내하는 값을 그대로 사용한다.**

개념적으로는 다음과 같이 구성한다.

| 호스트 | 연결 대상 | 용도 |
|---|---|---|
| `@` | Vercel이 안내하는 값 | 루트 도메인 |
| `www` | Vercel이 안내하는 값 | Frontend |
| `api` | Render가 안내하는 값 | Backend API |

> DNS 레코드의 구체적인 A/CNAME 값은 서비스 제공자가 변경할 수 있으므로, 오래된 문서에 있는 고정값을 복사하지 말고 **Vercel/Render 대시보드의 현재 안내값을 기준으로 설정하는 것**을 권장한다.

---

## 6. Cloudflare DNS 사용 권장

### 6.1 권장 구성

도메인은 가비아 등에서 등록하고, DNS 관리는 Cloudflare에서 하는 방식을 권장한다.

도메인 등록부터 DNS까지 Cloudflare에서 관리하는 구성도 가능하다.

```text
                  ┌──────────────┐
                  │  Cloudflare  │
                  │     DNS      │
                  └──────┬───────┘
                         │
                ┌────────┴────────┐
                ▼                 ▼
             Vercel            Render
            Frontend         Backend API
                │                 │
                └────────┬────────┘
                         ▼
                      Supabase
```

### 6.2 Cloudflare의 장점

- DNS 관리 편의성
- DNS 보안 기능
- CDN 및 보안 기능 활용 가능
- DDoS 방어 기능 활용 가능
- 향후 서버 구조 변경 시 DNS만 수정하면 되므로 유연함
- 여러 클라우드 서비스를 하나의 도메인으로 관리하기 편리

> **주의:** Cloudflare가 반드시 있어야 HTTPS가 가능한 것은 아니다. Vercel과 Render도 각각 HTTPS를 제공한다. Cloudflare는 DNS 및 추가적인 보안/네트워크 기능을 관리하기 위한 선택지로 보는 것이 좋다.

---

## 7. 기존 서버 구축 방식과의 비교

### 기존 방식 — 직접 서버 관리

```text
Linux Server
    │
    ├─ Nginx
    ├─ SSL 인증서
    ├─ 고정 IP
    ├─ 방화벽
    ├─ 포트포워딩
    ├─ 서버 업데이트
    └─ 서버 장애관리
```

### 현재 권장 방식 — 관리형 서비스 조합

```text
Vercel + Render + Supabase + Cloudflare
```

서버를 직접 구축하지 않고 각 서비스의 역할을 명확하게 분리하여 운영할 수 있다.

---

## 8. 실제 구축 순서

실제 서비스를 구축할 때는 다음 순서로 진행하는 것을 권장한다.

```text
① 도메인 등록
       ↓
② Cloudflare DNS 구성
       ↓
③ Vercel Frontend 배포
       ↓
④ Render Backend 배포
       ↓
⑤ Vercel에 www.coteleaf.com 연결
       ↓
⑥ Render에 api.coteleaf.com 연결
       ↓
⑦ DNS 레코드 설정
       ↓
⑧ Backend CORS 설정
       ↓
⑨ Frontend의 Backend API 주소 설정
       ↓
⑩ HTTPS / API 통신 테스트
       ↓
⑪ Supabase DB / Auth / Storage 연결 확인
```

### 8.1 Frontend API 주소

Frontend에서 Backend를 호출할 때는 개발환경과 운영환경의 API 주소를 분리하는 것이 좋다.

```text
개발환경
http://localhost:xxxx

운영환경
https://api.coteleaf.com
```

환경변수를 사용하는 방식을 권장한다.

```text
NEXT_PUBLIC_API_URL=https://api.coteleaf.com
```

실제 환경변수 이름은 프로젝트의 프레임워크와 코드 구조에 맞게 정한다.

### 8.2 CORS

Frontend와 Backend가 서로 다른 도메인/서브도메인을 사용하는 경우 Backend에서 허용할 Origin을 설정해야 한다.

예:

```text
Frontend
https://www.coteleaf.com

        │
        │ HTTPS API 요청
        ▼

Backend
https://api.coteleaf.com
```

Backend에서는 신뢰할 수 있는 Frontend Origin만 허용하는 것이 좋다.

```text
Allowed Origin:
https://www.coteleaf.com
```

개발환경에서는 별도로 로컬 개발 주소를 허용할 수 있다.

```text
http://localhost:3000
```

---

## 9. 비용 구분

도메인 비용과 서버/플랫폼 비용은 별개다.

| 항목 | 서비스 | 비용 |
|---|---|---|
| 도메인 | 가비아 / Cloudflare Registrar | 등록 및 갱신 비용 발생 |
| Frontend | Vercel | 무료/유료 플랜 |
| Backend | Render | 무료/유료 플랜 |
| Database | Supabase | 무료/유료 플랜 |
| DNS | Cloudflare | 무료 플랜 및 유료 기능 |

> 무료 플랜의 사용량 및 기능에는 제한이 있을 수 있으므로 실제 상용서비스에서는 트래픽, 저장공간, 실행시간, 데이터베이스 사용량 등을 기준으로 비용을 검토해야 한다.

---

## 10. 고정 IP가 필요한 경우

일반적인 Vercel + Render 웹서비스에는 고정 IP가 필요하지 않지만 다음과 같은 상황에서는 별도의 검토가 필요하다.

- 외부 금융/기업 시스템에서 특정 IP만 허용하는 경우
- 외부 API가 IP Allowlist를 요구하는 경우
- 기관의 방화벽 정책상 특정 공인 IP가 필요한 경우
- 자체 서버 또는 특정 네트워크 인프라와 직접 연결해야 하는 경우

따라서 정확한 표현은:

> **일반적인 Vercel + Render 웹서비스에서는 고정 IP가 필요하지 않다.**

이다.

---

## 11. 최종 권장 구성

| 영역 | 추천 |
|---|---|
| 도메인 | 가비아 또는 Cloudflare Registrar |
| DNS | Cloudflare |
| Frontend | Vercel |
| Backend | Render |
| Database | Supabase |
| 파일/이미지 저장 | Supabase Storage 또는 별도 Object Storage |
| SSL/HTTPS | Vercel / Render / 필요 시 Cloudflare 활용 |
| 고정 IP | 일반적으로 불필요 |
| Linux 서버 직접 구축 | 불필요 |
| Nginx 직접 관리 | 일반적으로 불필요 |

### 최종 구조도

```text
                         coteleaf.com
                              │
                              ▼
                       Cloudflare DNS
                         │         │
                         │         │
                         ▼         ▼
                      Vercel     Render
                         │         │
                         │         │
                    Frontend   Backend API
                         │         │
                         └────┬────┘
                              │
                              ▼
                           Supabase
                         ┌────┼────┐
                         ▼    ▼    ▼
                    PostgreSQL Auth Storage
```

---

## 12. 기존 서버와 비교한 핵심 장점

기존에 직접 서버를 운영하는 방식에서는 서버의 하드웨어, OS, Nginx, SSL, 방화벽, 업데이트, 장애 대응 등을 직접 관리해야 한다.

반면 관리형 서비스 조합에서는 다음과 같이 역할을 분리할 수 있다.

```text
Vercel
  → Frontend 배포 및 CDN

Render
  → Backend API 실행

Supabase
  → Database / Auth / Storage

Cloudflare
  → DNS / 보안 / 네트워크 관리

도메인 등록기관
  → 도메인 등록 및 갱신
```

따라서 웹서비스 개발자는 **애플리케이션 개발에 집중하고 서버 인프라 관리 부담을 줄일 수 있다.**

---

## 13. 핵심 정리

1. **가비아 가입은 IP 확보가 아니라 도메인 확보를 위한 것이다.**
2. **Vercel + Render 조합에서는 일반적으로 고정 IP를 직접 확보할 필요가 없다.**
3. `www.coteleaf.com → Vercel`, `api.coteleaf.com → Render` 형태로 구성하면 Frontend와 Backend를 명확하게 분리할 수 있다.
4. 도메인은 가비아 등에서 등록하고 DNS는 Cloudflare에서 관리할 수 있다.
5. **Vercel과 Render 자체도 HTTPS를 제공하므로 Cloudflare가 HTTPS를 위한 필수 조건은 아니다.**
6. 실제 DNS 레코드는 Vercel과 Render 대시보드에서 안내하는 현재 값을 기준으로 설정한다.
7. 운영환경에서는 **CORS와 Frontend의 Backend API 주소 설정**을 반드시 확인한다.
8. Linux 서버, Nginx, 방화벽 등을 직접 구축하지 않고도 관리형 서비스 기반으로 웹서비스를 운영할 수 있다.

---

## 14. CoteLeaf / SkinLens에 적용할 경우

현재와 같은 웹서비스를 구성한다면 다음과 같은 형태가 적합하다.

```text
                    사용자
                      │
                      ▼
              www.coteleaf.com
                      │
                      ▼
                   Vercel
                  Frontend
                      │
                      │ HTTPS API
                      ▼
               api.coteleaf.com
                      │
                      ▼
                    Render
                 Backend API
                      │
                      ▼
                  Supabase
             ┌────────┼────────┐
             ▼        ▼        ▼
          Database   Auth    Storage
```

이 구조에서는 **웹서비스의 Frontend, Backend, Database, Storage를 각각 적합한 관리형 서비스에 분리**할 수 있으며, 기존의 직접 서버 구축 방식보다 초기 인프라 관리 부담을 크게 줄일 수 있다.
