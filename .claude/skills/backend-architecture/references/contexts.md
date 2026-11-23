# 컨텍스트와 용어

## 컨텍스트

모든 컨텍스트의 소유자는 A입니다(07 역할 분담 문서 기준). 애그리거트는 후보이고, 실제 경계는 `/design-schema`에서 확정합니다.

| 컨텍스트 | 맡는 일 | 애그리거트 후보 | 바깥 시스템 |
|---|---|---|---|
| `auth` | 회원가입, 로그인, 권한 | Member | |
| `catalog` | 공연·회차 조회, KOPIS 수집 | Performance, Schedule | KOPIS(`adapter/kopis`) |
| `order` | 주문, 좌석·재고, 주문 상태 | Order | |
| `payment` | 결제 승인, 취소, 웹훅, 결과 불명 복구 | Payment | 토스(`adapter/toss`) |
| `point` | 포인트 적립·사용, 원장 | 원장 설계 후 확정 | |
| `settlement` | 정산 집계, 일일 대사 | 설계 후 확정 | |

## 컨텍스트 사이 관계

| 호출하는 쪽 → 불리는 쪽 | 방식 | 내용 |
|---|---|---|
| order → catalog | 동기, `ScheduleQueryService` | 주문 금액은 회차 가격으로 서버가 정합니다 |
| payment → order | 동기, `OrderPaymentService` | 결제할 수 있는지 확인하고 결제 완료로 바꿉니다. 결제 승인과 주문 결제 완료는 **일부러 한 트랜잭션**으로 묶습니다 |
| payment → point | 비동기, `PaymentApproved` 이벤트 | 포인트를 적립합니다 |
| payment·point → settlement | 비동기 이벤트 또는 일일 배치 | 정산을 집계하고 대사합니다(6~7주차) |
| KOPIS → catalog | ACL 어댑터 | KOPIS XML을 우리 타입으로 번역합니다 |
| 토스 → payment | ACL 어댑터, 웹훅 | 토스 응답과 상태를 `ConfirmResult`와 `PaymentStatus`로 번역합니다 |
| 모든 컨텍스트 → auth | 호출하지 않음, JWT | 로그인한 회원 id는 액세스 토큰의 `subject`에서 꺼냅니다(`@AuthenticationPrincipal jwt: Jwt`). 회원 정보가 더 필요해지면 auth `application/service`에 공개 서비스를 만듭니다 |

새 관계를 추가할 때는 이렇게 정합니다.

- 같은 트랜잭션에서 함께 성공하거나 함께 실패해야 하면 동기 호출(`MANDATORY`)을 쓰고, 이 표에 이유를 적습니다.
- 늦게 반영돼도 되면 Outbox 이벤트를 씁니다.
- 순환 호출(A→B→A)은 만들지 않습니다. 생기면 컨텍스트 경계를 다시 봅니다.

## 용어

코드, DB, API, Issue에서 같은 단어를 씁니다.

| 한국어 | 코드 | 뜻 |
|---|---|---|
| 회원 | Member | 가입한 사용자. 다른 컨텍스트는 `memberId`로만 참조합니다 |
| 액세스 토큰 | `accessToken` | 30분짜리 JWT. `subject`가 memberId입니다 |
| 리프레시 토큰 | `refreshToken` | 액세스 토큰을 다시 받는 불투명 값. Redis에 저장하고 한 번 쓰면 교체합니다 |
| 공연 | Performance | KOPIS의 공연 하나 |
| 회차 | Schedule | 공연의 특정 일시. 가격을 가집니다 |
| 주문 | Order | 회원이 회차를 예매한 단위 |
| 주문번호 | `orderNo` | 외부에 노출되는 주문 ID(UUID). 토스의 `orderId`이고 confirm의 Idempotency-Key입니다 |
| 결제 | Payment | 주문 하나에 대한 결제 시도 |
| 결제 키 | `paymentKey` | 토스가 발급하는 결제 ID |
| 승인 | approve / confirm | 토스 `/payments/confirm` 성공 |
| 결과 불명 | `UNKNOWN` | 타임아웃이나 5xx로 승인 여부를 모르는 상태. 토스 조회로 확정합니다 |
| 포인트 | Point | 결제 금액에 따라 쌓이는 포인트 |
| 원장 | Ledger | 포인트 변동을 차변·대변으로 기록한 장부 |
| 정산 | Settlement | 기간별 매출 집계 |
| 대사 | Reconciliation | 우리 기록과 토스 기록을 맞춰 보는 작업 |
