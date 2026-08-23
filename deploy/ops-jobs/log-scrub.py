#!/usr/bin/env python3
# =============================================================
# log-scrub.py — 앱 로그 개인정보/토큰 스크러빙 필터 (①)
#
#  대상: 3-Tier 이후 AI Server 의 Caddy / gateway / worker 로그.
#        (nginx 는 제거되어 더 이상 대상이 아님 — 계획 §2 제거 대상 참조)
#  로그에 흔히 새는 것: Authorization/Bearer, JWT, presigned URL 쿼리(?token=…),
#  이메일, 스토리지 객체 키({uid}/{job}/…). 이 필터가 메시지·인자를 마스킹.
#
#  설치(예: gateway/worker 부팅 시):
#     from followup_P1.log_scrub import install_scrubber
#     install_scrubber()            # 루트 로거에 필터 부착
#
#  주의:
#   - 필터는 최선의 방어일 뿐, "애초에 민감정보를 로깅하지 않는 것"이 우선.
#     요청 바디(이미지)·헤더 전체를 로깅하지 말 것.
#   - 구조적 로깅과 함께 쓰면(observability/logging_config.py) 값 필드에도 적용됨.
# =============================================================
import logging
import re

_PATTERNS = [
    # Authorization: Bearer xxx  /  "token": "xxx"
    (re.compile(r'(?i)(authorization\s*[:=]\s*)(bearer\s+)?[A-Za-z0-9._\-]+'), r'\1\2<redacted>'),
    (re.compile(r'(?i)("?(?:token|access_token|refresh_token|apikey|api_key|secret|password)"?\s*[:=]\s*"?)[^"\s,&}]+'),
     r'\1<redacted>'),
    # JWT (xxx.yyy.zzz)
    (re.compile(r'\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+'), '<jwt>'),
    # presigned/URL 쿼리스트링 제거 (경로는 남기고 ? 이후 삭제)
    (re.compile(r'(https?://[^\s?]+)\?[^\s]*'), r'\1?<redacted>'),
    # 이메일
    (re.compile(r'\b[\w.+\-]+@[\w\-]+\.[\w.\-]+\b'), '<email>'),
    # 스토리지 객체 키 {uuid}/{uuid}/... → 소유자/잡 마스킹
    (re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(/[^\s"]*)'),
     r'<uid><path>'),
]


def scrub(text: str) -> str:
    if not text:
        return text
    for pat, repl in _PATTERNS:
        text = pat.sub(repl, text)
    return text


class ScrubFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = scrub(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: scrub(str(v)) for k, v in record.args.items()}
                else:
                    record.args = tuple(scrub(str(a)) for a in record.args)
        except Exception:
            # 로깅이 앱을 죽이면 안 됨 — 실패 시 원문 통과보다 안전하게 통째 마스킹
            record.msg = "<scrub-error>"
            record.args = ()
        return True


def install_scrubber(logger: logging.Logger | None = None) -> None:
    (logger or logging.getLogger()).addFilter(ScrubFilter())


if __name__ == "__main__":
    # 간단 자체 테스트
    for s in [
        'Authorization: Bearer abc.def.ghi',
        'GET https://x.supabase.co/storage/v1/object/sign/skin-images/a?token=eyJhbGci.a.b',
        'user contact john.doe@example.com',
        'key 12345678-1234-1234-1234-123456789abc/job/original.jpg',
    ]:
        print(scrub(s))
