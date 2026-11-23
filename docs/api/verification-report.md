# 외부 API 검증 보고서

두 사람이 같은 체크리스트 항목을 각자 직접 호출해 보고, 그 결과를 자기 이름 섹션에 남기는 문서입니다.
설계를 정하기 전에 문서에 적힌 동작과 실제 동작이 같은지 확인하고, 다른 점이 있으면 근거 로그와 함께 기록합니다.

> 표기 규칙: paymentKey·transactionKey·secret은 앞 8자리만 적습니다. 오늘 결제는 paymentKey 앞 8자리가 모두 `tviva261`이라 구분을 위해 끝 4자리를 `tviva261…0KFs`처럼 함께 적습니다. API 키 값은 적지 않습니다.

---

## 토스페이먼츠 — justziseok (2026-11-23)

**근거:** `toss-practice\logs\` 로그 파일(API 호출 21개, 웹훅 7개), `toss-reconcile\` 조회 결과 파일. 시각은 모두 KST이고, 로그 파일 이름의 시각은 UTC(KST −9시간)입니다.

### 체크리스트

| 항목 | 결과 | 근거 로그 파일 |
|---|---|---|
| 테스트 키 확인 | ✅ 시크릿 키 접두어 `test_sk_`(테스트 키), 응답 mId `tvivarepublica`(테스트 상점) | `toss-reconcile\fetch.py`(실행 시 키 종류 판별), `…01-24-39-803Z_confirm_…0KFs` |
| 승인·조회·취소 | ✅ …1LwI: 승인 200 DONE → 조회 DONE → 취소 200 CANCELED → 조회 CANCELED. …0KFs도 승인 → 17분 뒤 취소 성공 | `…01-25-46-180Z_confirm_…1LwI`, `…01-25-52-083Z_lookup_…1LwI`, `…01-26-00-219Z_cancel_…1LwI`, `…01-26-07-338Z_lookup_…1LwI`, `…01-42-06-174Z_cancel_…0KFs` |
| 같은 Idempotency-Key 재승인 | ✅ …wEBc: 키 A로 승인 200 DONE → 같은 키 A로 재요청 200, 응답 본문이 첫 응답과 **완전히 같음**(1351 bytes) → 다른 키 B로 재요청 400 `ALREADY_PROCESSED_PAYMENT` | `…01-30-55-799Z_confirm-A_…wEBc`, `…01-30-57-434Z_confirm-A-repeat_…wEBc`, `…01-30-58-606Z_confirm-B_…wEBc` |
| 웹훅 수신·재전송 | ✅ 7건 수신, 서명 있는 건은 모두 검증 성공. 500으로 응답하자 1분 21초 뒤 1차, 4분 뒤 2차 재전송(본문 같음, transmission-id는 다름) | `webhook_*_0001` ~ `_0007` (아래 표) |
| 에러 재현(카드 거절) | ✅ 테스트 헤더 `INVALID_REJECT_CARD`로 승인 → 400 `INVALID_REJECT_CARD`. 이후 조회하면 **IN_PROGRESS 그대로**, 30분 뒤 EXPIRED | `…01-30-13-602Z_confirm-error-repro_…ss4N`, `…01-58-39-981Z_lookup_…ss4N`, `…02-02-35-351Z_lookup_…ss4N` |
| 승인 가능 시간 | ✅ 인증 후 9분 26초에 승인 성공, 14분 50초에 승인하면 400 `EXPIRED_PAYMENT` + ABORTED 웹훅 → 기한 약 10분 | `…01-57-10-728Z_confirm-A_…98vE`, `…01-46-58-519Z_confirm-A_…kfwK`, `webhook_*_0002` |
| 일일 대사용 내역 조회 | ✅ `GET /v1/transactions` 오늘 범위 200·5행(1페이지). `GET /v1/settlements` 오늘 날짜 soldDate·paidOutDate 둘 다 200·0행 | `toss-reconcile\transactions_2026-11-23.json`, `settlements_soldDate_2026-11-23.json`, `settlements_paidOutDate_2026-11-23.json`, `payments_lookup_2026-11-23.json` |

### 웹훅 수신

모두 `PAYMENT_STATUS_CHANGED`입니다. 응답 코드는 우리 웹훅 서버(3001)가 돌려준 값이고, 0002~0004는 재전송을 확인하려고 일부러 500으로 응답했습니다.

| # | 수신 시각 (KST) | 결제 | status | retried | 서명 | 응답 코드 |
|---|---|---|---|---|---|---|
| 0001 | 10:42:09.887 | tviva261…0KFs | CANCELED | 0 | 있음(검증 OK) | 200 |
| 0002 | 10:47:02.268 | tviva261…kfwK | ABORTED | 0 | 있음(검증 OK) | 500 |
| 0003 | 10:48:23.697 | tviva261…kfwK | ABORTED | 1 | **없음** | 500 |
| 0004 | 10:52:23.199 | tviva261…kfwK | ABORTED | 2 | **없음** | 500 |
| 0005 | 10:57:14.555 | tviva261…98vE | DONE | 0 | 있음(검증 OK) | 200 |
| 0006 | 11:01:19.256 | tviva261…ss4N | EXPIRED | 0 | 있음(검증 OK) | 200 |
| 0007 | 11:04:39.523 | tviva261…cdBo | EXPIRED | 0 | 있음(검증 OK) | 200 |

### 설계에 영향을 주는 발견

- **승인 기한은 약 10분.** …98vE는 결제 요청(requestedAt 10:47:45) 후 9분 26초에 승인 성공했습니다. …kfwK는 requestedAt 10:32:08 후 14분 50초(10:46:58)에 승인 요청해 400 `EXPIRED_PAYMENT`를 받았고, 결제 상태는 ABORTED가 되며 ABORTED 웹훅이 왔습니다. → successUrl을 받은 즉시 승인을 호출하고, `EXPIRED_PAYMENT`를 받으면 주문을 실패로 처리해야 합니다.
- **승인되지 않은 결제는 30분 동안 IN_PROGRESS로 남았다가 EXPIRED가 됩니다.** …cdBo(승인 시도 없음)는 30분 43초까지 IN_PROGRESS였고, 32분 6초에 EXPIRED 웹훅을 받았습니다. …ss4N(카드 거절 테스트 1회만 시도)은 31분 40초에 EXPIRED 웹훅을 받았습니다. 두 웹훅 모두 서명이 있습니다. → 결제창 이탈 건은 30분 넘게 "진행 중"으로 보이므로, 좌석 홀드 해제 시점을 이 웹훅이나 자체 타이머로 정해야 합니다.
- **재전송 웹훅(retried ≥ 1)에는 서명 헤더가 없습니다.** 0003·0004에는 `tosspayments-webhook-signature`가 없습니다. → 서명이 없다고 무조건 거부하면 재전송을 전부 놓칩니다. 서명이 없는 웹훅은 본문을 믿지 말고 `GET /v1/payments/{paymentKey}`로 다시 조회해서 처리해야 합니다.
- **같은 Idempotency-Key로 다시 보내면 첫 응답이 그대로 돌아오고, 다른 키로 보내면 `ALREADY_PROCESSED_PAYMENT`입니다.** → 승인 재시도에는 반드시 같은 키를 써야 합니다. `ALREADY_PROCESSED_PAYMENT`가 오면 실패로 보지 말고 조회 API로 실제 상태를 확인해야 합니다.
- **카드 거절 테스트 헤더(`INVALID_REJECT_CARD`)는 결제 상태를 바꾸지 않습니다.** 승인 응답은 400인데 결제는 IN_PROGRESS로 남았습니다(이후 시간 만료로 EXPIRED). → 승인 에러 응답만 보고 결제 상태를 ABORTED라고 단정하면 안 됩니다.
- **거래 내역에는 승인·취소만 나옵니다.** 취소는 금액이 양수인 `CANCELED`(부분취소는 `PARTIAL_CANCELED`) 행으로 따로 나오고, 거절·만료(ABORTED/EXPIRED) 결제는 나오지 않습니다. 행마다 transactionKey가 다르므로(모두 `txrd_a01`로 시작) 대사 키는 **transactionKey**로 잡아야 합니다. 금액은 status를 보고 직접 부호를 붙여야 합니다.
- **정산 내역은 D+1부터 조회됩니다.** 당일 조회는 soldDate·paidOutDate 기준 모두 0행이었고, 문서에도 "결제 다음 날부터 조회"라고 되어 있습니다. → 수수료·지급액 대사는 다음 날 별도 배치로 돌려야 합니다.

---

## KOPIS — justziseok (2026-11-23)

**근거:** `kopring-practice\src\test\resources\kopis\` 응답 파일 5개(`pblprfr-list.xml`, `pblprfr-list-empty.xml`, `pblprfr-detail-PF307123.xml`, `error-02-invalid-key.xml`, `error-06-rows-over-100.xml`), `KopisXmlParserTest`, 그리고 다른 세션에서 실제로 호출한 결과값.

### 체크리스트

| 항목 | 결과 | 근거 |
|---|---|---|
| 서비스키 발급 | ✅ 발급 완료. 1인 1개, 양도 불가, 유효기간 1년, 3개월 동안 쓰지 않으면 승인 취소 | 활용신청 페이지, 개발가이드 |
| 목록·상세 호출과 Kotlin 파싱 | ✅ 목록 `/pblprfr`(stdate 20261123, eddate 20261129, cpage 1, rows 10) → HTTP 200·10건, 첫 공연 PF307123. 상세 `/pblprfr/PF307123` → HTTP 200. **http만 지원.** 파싱은 jackson-dataformat-xml(Jackson 3, `tools.jackson`)로 하고 Kotest 테스트 7개 통과. 공백 한 칸 값은 null로 바꾸고, `styurls`·`relates`는 홀더 클래스로 받음 | `pblprfr-list.xml`, `pblprfr-detail-PF307123.xml`, `KopisXmlParserTest` |
| 31일·100건 제약 | ⚠️ 100건 제약은 문서대로 returncode 06이 나옴. **31일 제약(05)은 실제로 나오지 않음**(아래 표) | `error-06-rows-over-100.xml`, 실제 호출 결과 |
| 호출 한도·출처 표기 | ⚠️ 일일 호출 한도는 수치 명시 없음("제한이 있을 수 있으며 초과 시 서비스 중지"). 출처 표기는 필수: 예시 "출처: (재)예술경영지원센터 공연예술통합전산망(http://www.kopis.or.kr)", 표기하지 않으면 서비스가 중단될 수 있음 | 이용안내, 개발가이드 |
| 포스터 이용 조건 | ❓ 가이드에 명시 없음, 문의 필요 (kopis@gokams.or.kr) | 개발가이드 |

### 제약 테스트 결과

| 시나리오 | HTTP | returncode | errmsg |
|---|---|---|---|
| 기간 32·33·60·365일, 시작일 > 종료일 | 200 | 없음 | 없음. 정상 데이터 반환(가이드의 31일 제한 에러 05가 실제로는 나오지 않음) |
| rows=101 | 200 | 06 | 최대 조회수는 100건까지 가능합니다. |
| rows=100 | 200 | 없음 | 없음. 정상 100건 |
| 키 없음 | 200 | 02 | SERVICE KEY IS NOT REGISTERED ERROR |
| 잘못된 키 | 200 | 02 | SERVICE KEY IS NOT REGISTERED ERROR (키 없음과 같음) |

- **에러는 HTTP 상태가 아니라 본문의 `returncode`로 판단해야 합니다.** 에러 응답도 HTTP 200으로 옵니다. 파서는 `<returncode>`가 있으면 `KopisApiException`을 던집니다.
- 기간 제한이 서버에서 강제되지 않으므로, 우리 쪽에서 조회 기간을 31일 이내로 직접 잘라서 호출해야 합니다(가이드 기준을 지키기 위해).

### 미정 항목

- 48시간 호출 성공률 측정: 담당자 미정

### 출처

- https://www.kopis.or.kr/por/cs/openapi/openApiInfo.do?menuId=MNU_00074
- https://kopis.or.kr/por/cs/openapi/openApiList.do?menuId=MNU_00074
- https://www.kopis.or.kr/por/cs/openapi/openApiUseSend.do?menuId=MNU_00074
- https://www.kopis.or.kr/upload/openApi/공연예술통합전산망OpenAPI개발가이드.pdf
