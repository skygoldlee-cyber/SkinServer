# Flutter 앱 ↔ 서버 연동 계약 (사진 + 고객 설문)

Flutter 앱은 **사진과 고객 설문을 한 번의 요청**으로 보낸다. 서버는 job 을 만들고
`job_id` 를 즉시 돌려주며(202), 앱은 그 id 로 상태·결과를 폴링한다.

공용 규격 원본: [`../../packages/common/skinlens_contract`](../../packages/common/skinlens_contract)
(`Survey`, `UPLOAD_FIELDS`, `AnalysisResult`, `PrescribeResult`).

---

## 1. 업로드 — `POST /analyze` (multipart/form-data)

| 필드 | 필수 | 형식 | 설명 |
|---|---|---|---|
| `image` | ✅ | file(jpeg/png/webp, ≤25MB) | 얼굴/피부 사진 |
| `survey` | 선택 | JSON 문자열(object) | 고객 설문(아래 shape) |
| `pcr` | 선택 | JSON 문자열(object) | PCR 결과(있을 때) |

헤더:
- `Authorization: Bearer <supabase-jwt>` — **운영(strict) 필수**. 서버가 서명을 검증해
  사용자(sub=uuid)를 도출한다. 클라이언트가 보낸 `X-User-Id` 는 엣지에서 제거되므로 신뢰되지 않는다.
- dev 모드에선 `X-User-Id: <uuid>`(없으면 고정 UUID 폴백)로 대체 가능.
- 조회 API(`GET /jobs/{id}` 등)도 **동일하게 본인 토큰**을 실어야 하며, 남의 job 은 404 로 응답한다.
- (Content-Type 은 multipart 로 자동 설정)

응답: `202 { "job_id": "...", "status": "queued" }`

> 처방 엔진은 **분석·설문·PCR 중 하나만 있어도** 동작한다(설문만 보내도 됨).
> 설문은 사진으로 얻기 어려운 지표(민감성/복합성 등)를 채운다.

### 설문(Survey) 권장 shape

앱은 **아는 필드만** 채워 보내면 되고, 엔진은 아는 필드만 사용한다(모르는 문항도 보관).

```json
{
  "skin_type": "sensitive",
  "sensitivity": { "stings_easily": true, "reacts_to_products": false, "redness_frequent": true },
  "concerns": ["redness", "dryness"],
  "age_band": "30s",
  "sun_exposure": "medium",
  "notes": "겨울에 각질"
}
```
- `skin_type`: `oily|dry|combination|normal|sensitive` (자가보고)
- `sensitivity`: 불리언 플래그들 — 민감성 지표 산출에 사용
- `concerns`: 관심 지표 목록 — 결과에 기록(후속 가중은 도메인 규칙)
- 나머지는 확장 필드(그대로 저장)

> ⚠ 실제 문항·척도는 도메인 결정이다. 위는 baseline 해석이 인식하는 최소 권장 필드이며,
> 문항이 늘면 `engine-prescription/app/survey.py` 의 매핑만 확장하면 된다(계약은 유지).

---

## 2. 상태·결과 조회

- `GET /jobs/{job_id}` — `status`(queued→processing→done|error) + `result`
- `GET /jobs/{job_id}/events` — 단계별 산출물(디버깅/진행 표시용)

`result` 예(요약):
```json
{
  "analysis":     { "score": 72.4, "metrics": { "redness": {"value":..,"source":"cv"}, ... } },
  "prescription": {
    "grade": "경미", "prescription_ratio_pct": 0.5,
    "per_metric": { "sensitivity": {"grade":"위험/심각","source":"survey"}, ... },
    "selected_mixes": [ {"mix":"M06","reason":"sensitivity=위험/심각"}, ... ],
    "concerns": ["redness","dryness"]
  }
}
```

---

## 3. 앱 폴링 규칙(권장)

1. `POST /analyze` → `job_id` 저장, 화면에 "분석 중".
2. 1~2초 간격으로 `GET /jobs/{id}` 폴링, `status==done` 이면 `result` 표시,
   `error` 면 `error` 메시지 표시.
3. 타임아웃(예: 60s) 넘으면 재시도/안내. (업로드는 비동기라 요청 자체는 즉시 끝남)

---

## 4. Dart 예시 (http 패키지)

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

Future<String> submit(String base, String userId, List<int> jpg, Map survey) async {
  final req = http.MultipartRequest('POST', Uri.parse('$base/analyze'))
    ..headers['X-User-Id'] = userId
    ..files.add(http.MultipartFile.fromBytes('image', jpg,
        filename: 'face.jpg', contentType: MediaType('image', 'jpeg')))
    ..fields['survey'] = jsonEncode(survey);
  final res = await http.Response.fromStream(await req.send());
  if (res.statusCode != 202) { throw Exception('업로드 실패: ${res.body}'); }
  return jsonDecode(res.body)['job_id'];
}

Future<Map> poll(String base, String jobId) async {
  for (var i = 0; i < 60; i++) {
    final r = await http.get(Uri.parse('$base/jobs/$jobId'));
    final j = jsonDecode(r.body);
    if (j['status'] == 'done')  return j['result'];
    if (j['status'] == 'error') throw Exception(j['error']);
    await Future.delayed(const Duration(seconds: 2));
  }
  throw Exception('시간 초과');
}
```
`base` 는 운영 API 도메인(예: `https://api.<도메인>`). `MediaType` 은 `http_parser` 패키지.

---

## 5. 오류 코드

| 코드 | 의미 | 앱 처리 |
|---|---|---|
| 202 | 접수됨 | `job_id` 로 폴링 시작 |
| 400 | 빈 파일 / survey·pcr 가 JSON object 아님 / X-User-Id 형식 오류 | 입력 점검 후 재시도 |
| 413 | 이미지 용량 초과(>25MB) | 리사이즈/재촬영 |
| 415 | 형식 불일치(jpeg/png/webp 아님, 매직바이트 위조) | 형식 확인 |
| 404 | 없는 job | id 확인 |
| 5xx | 서버 오류 | 잠시 후 재시도, 지속 시 서버 점검(체크포인트 가이드) |
