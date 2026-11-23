# 코드 템플릿

컴파일하고 테스트까지 통과한 예시입니다(Spring Boot 4.1.3, Kotlin 2.3.21, MySQL 8.4 Testcontainers). 파일 하나에 최상위 타입 하나씩 두었고, import는 생략했습니다. 새 코드는 이름만 바꿔 이 모양을 따릅니다.

## 공통: 금액과 에러

컨텍스트마다 `XxxError` enum을 만들고, HTTP 상태는 `GlobalExceptionHandler`에서만 정합니다.

`common/domain/Money.kt`

```kotlin
package com.tikitaka.common.domain

@Embeddable
data class Money(val amount: Long) {
    init {
        require(amount >= 0) { "금액은 0 이상이어야 합니다: $amount" }
    }

    operator fun plus(other: Money) = Money(amount + other.amount)

    companion object {
        val ZERO = Money(0)
    }
}
```

`common/error/ErrorKind.kt`

```kotlin
package com.tikitaka.common.error

enum class ErrorKind { INVALID, NOT_FOUND, CONFLICT, EXTERNAL }
```

`common/error/ErrorCode.kt`

```kotlin
package com.tikitaka.common.error

interface ErrorCode {
    val name: String
    val kind: ErrorKind
}
```

`common/error/BusinessException.kt`

```kotlin
package com.tikitaka.common.error

class BusinessException(val error: ErrorCode, message: String = error.name) : RuntimeException(message)
```

`common/web/dto/ErrorResponse.kt`

```kotlin
package com.tikitaka.common.web.dto

data class ErrorResponse(val code: String, val message: String?)
```

`common/web/GlobalExceptionHandler.kt`

```kotlin
package com.tikitaka.common.web

@RestControllerAdvice
class GlobalExceptionHandler {
    @ExceptionHandler(BusinessException::class)
    fun business(e: BusinessException) =
        ResponseEntity.status(e.error.kind.toStatus()).body(ErrorResponse(e.error.name, e.message))

    @ExceptionHandler(IllegalArgumentException::class)
    fun invalid(e: IllegalArgumentException) =
        ResponseEntity.badRequest().body(ErrorResponse(ErrorKind.INVALID.name, e.message))

    private fun ErrorKind.toStatus() = when (this) {
        ErrorKind.INVALID -> HttpStatus.BAD_REQUEST
        ErrorKind.NOT_FOUND -> HttpStatus.NOT_FOUND
        ErrorKind.CONFLICT -> HttpStatus.CONFLICT
        ErrorKind.EXTERNAL -> HttpStatus.BAD_GATEWAY
    }
}
```

## 애그리거트와 Repository

상태는 `protected set`, 생성은 팩토리, 규칙은 메서드에 둡니다. Repository 인터페이스와 `getBy` 확장 함수는 domain의 한 파일에 둡니다.

`order/domain/Order.kt`

```kotlin
package com.tikitaka.order.domain

@Entity
@Table(name = "orders")
class Order private constructor(
    @Column(unique = true) val orderNo: String,
    val memberId: Long,
    val scheduleId: Long,
    @Embedded val amount: Money,
) {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long = 0
        protected set

    @Enumerated(EnumType.STRING)
    var status: OrderStatus = OrderStatus.PENDING
        protected set

    fun verifyPayable(paidAmount: Money) {
        if (status != OrderStatus.PENDING) throw BusinessException(OrderError.NOT_PAYABLE)
        if (amount != paidAmount) throw BusinessException(OrderError.AMOUNT_MISMATCH)
    }

    fun markPaid() {
        if (status != OrderStatus.PENDING) throw BusinessException(OrderError.NOT_PAYABLE)
        status = OrderStatus.PAID
    }

    companion object {
        fun place(memberId: Long, scheduleId: Long, amount: Money) =
            Order(UUID.randomUUID().toString(), memberId, scheduleId, amount)
    }
}
```

`order/domain/OrderStatus.kt`

```kotlin
package com.tikitaka.order.domain

enum class OrderStatus { PENDING, PAID, CANCELED }
```

`order/domain/OrderError.kt`

```kotlin
package com.tikitaka.order.domain

enum class OrderError(override val kind: ErrorKind) : ErrorCode {
    ORDER_NOT_FOUND(ErrorKind.NOT_FOUND),
    NOT_PAYABLE(ErrorKind.CONFLICT),
    AMOUNT_MISMATCH(ErrorKind.INVALID),
}
```

`order/domain/OrderRepository.kt`

```kotlin
package com.tikitaka.order.domain

interface OrderRepository {
    fun save(order: Order): Order
    fun findByOrderNo(orderNo: String): Order?
}

fun OrderRepository.getByOrderNo(orderNo: String) =
    findByOrderNo(orderNo) ?: throw BusinessException(OrderError.ORDER_NOT_FOUND)
```

## Persistence 어댑터

Spring Data는 이 패키지 밖으로 나가지 않습니다.

`order/adapter/persistence/OrderJpaRepository.kt`

```kotlin
package com.tikitaka.order.adapter.persistence

interface OrderJpaRepository : JpaRepository<Order, Long> {
    fun findByOrderNo(orderNo: String): Order?
}
```

`order/adapter/persistence/OrderPersistenceAdapter.kt`

```kotlin
package com.tikitaka.order.adapter.persistence

@Repository
class OrderPersistenceAdapter(private val jpa: OrderJpaRepository) : OrderRepository {
    override fun save(order: Order): Order = jpa.save(order)
    override fun findByOrderNo(orderNo: String) = jpa.findByOrderNo(orderNo)
}
```

## 단순 명령 유스케이스와 컨트롤러

금액은 catalog의 공개 서비스에서 가져옵니다. 클라이언트 값을 쓰지 않습니다.

`order/application/dto/PlaceOrderCommand.kt`

```kotlin
package com.tikitaka.order.application.dto

data class PlaceOrderCommand(val memberId: Long, val scheduleId: Long)
```

`order/application/dto/PlaceOrderResult.kt`

```kotlin
package com.tikitaka.order.application.dto

data class PlaceOrderResult(val orderNo: String, val amount: Long)
```

`order/application/PlaceOrderUseCase.kt`

```kotlin
package com.tikitaka.order.application

@Service
class PlaceOrderUseCase(
    private val orders: OrderRepository,
    private val schedules: ScheduleQueryService,
) {
    @Transactional
    fun execute(command: PlaceOrderCommand): PlaceOrderResult {
        val price = schedules.getPrice(command.scheduleId) // 금액은 서버가 정함. 클라이언트 값을 믿지 않음
        val order = orders.save(Order.place(command.memberId, command.scheduleId, price))
        return PlaceOrderResult(order.orderNo, order.amount.amount)
    }
}
```

`order/adapter/web/dto/PlaceOrderRequest.kt`

```kotlin
package com.tikitaka.order.adapter.web.dto

data class PlaceOrderRequest(@Positive val scheduleId: Long)
```

`order/adapter/web/OrderController.kt`

```kotlin
package com.tikitaka.order.adapter.web

@RestController
@RequestMapping("/api/v1/orders")
class OrderController(private val placeOrder: PlaceOrderUseCase) {
    // memberId는 JWT subject에서 꺼냄. auth 컨텍스트 코드를 import하지 않음
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    fun place(
        @AuthenticationPrincipal jwt: Jwt,
        @Valid @RequestBody request: PlaceOrderRequest,
    ): PlaceOrderResult = placeOrder.execute(PlaceOrderCommand(jwt.subject!!.toLong(), request.scheduleId))
}
```

## 다른 컨텍스트가 부르는 공개 서비스

값만 돌려주고, 같은 트랜잭션에서만 불려야 하는 메서드에는 `MANDATORY`를 붙입니다.

`catalog/application/service/ScheduleQueryService.kt`

```kotlin
package com.tikitaka.catalog.application.service

/** 다른 컨텍스트가 부르는 catalog의 공개 API. 도메인 객체 대신 값만 돌려줍니다. */
@Service
class ScheduleQueryService(private val schedules: ScheduleRepository) {
    @Transactional(readOnly = true)
    fun getPrice(scheduleId: Long): Money = schedules.getById(scheduleId).price
}
```

`order/application/dto/PayableOrder.kt`

```kotlin
package com.tikitaka.order.application.dto

data class PayableOrder(val orderNo: String, val memberId: Long, val amount: Money)
```

`order/application/service/OrderPaymentService.kt`

```kotlin
package com.tikitaka.order.application.service

/** payment 컨텍스트가 부르는 order의 공개 API. */
@Service
class OrderPaymentService(private val orders: OrderRepository) {
    @Transactional(readOnly = true)
    fun getPayable(orderNo: String, paidAmount: Money): PayableOrder {
        val order = orders.getByOrderNo(orderNo)
        order.verifyPayable(paidAmount)
        return PayableOrder(order.orderNo, order.memberId, order.amount)
    }

    /** 결제 승인과 같은 트랜잭션에서만 호출합니다. */
    @Transactional(propagation = Propagation.MANDATORY)
    fun markPaid(orderNo: String) {
        orders.getByOrderNo(orderNo).markPaid()
    }
}
```

## 외부 API를 부르는 유스케이스

트랜잭션을 셋으로 나눕니다: 짧은 트랜잭션 → 트랜잭션 밖에서 외부 호출 → 결과 반영. 결과 불명(`UNKNOWN`)은 스케줄러가 토스 조회로 확정합니다.

`payment/domain/Payment.kt`

```kotlin
package com.tikitaka.payment.domain

@Entity
class Payment private constructor(
    val orderNo: String,
    @Column(unique = true) val paymentKey: String,
    @Embedded val amount: Money,
) {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long = 0
        protected set

    @Enumerated(EnumType.STRING)
    var status: PaymentStatus = PaymentStatus.REQUESTED
        protected set

    var approvedAt: Instant? = null
        protected set

    var failureCode: String? = null
        protected set

    fun approve(at: Instant) {
        requireUnsettled()
        status = PaymentStatus.APPROVED
        approvedAt = at
    }

    fun fail(code: String) {
        requireUnsettled()
        status = PaymentStatus.FAILED
        failureCode = code
    }

    /** 타임아웃 등으로 승인 여부를 모름. 복구 작업이 토스 조회로 확정합니다. */
    fun markUnknown() {
        requireUnsettled()
        status = PaymentStatus.UNKNOWN
    }

    private fun requireUnsettled() {
        if (status != PaymentStatus.REQUESTED && status != PaymentStatus.UNKNOWN) {
            throw BusinessException(PaymentError.ALREADY_SETTLED)
        }
    }

    companion object {
        fun request(orderNo: String, paymentKey: String, amount: Money) = Payment(orderNo, paymentKey, amount)
    }
}
```

`payment/domain/PaymentStatus.kt`

```kotlin
package com.tikitaka.payment.domain

enum class PaymentStatus { REQUESTED, APPROVED, FAILED, UNKNOWN }
```

`payment/domain/PaymentError.kt`

```kotlin
package com.tikitaka.payment.domain

enum class PaymentError(override val kind: ErrorKind) : ErrorCode {
    PAYMENT_NOT_FOUND(ErrorKind.NOT_FOUND),
    ALREADY_SETTLED(ErrorKind.CONFLICT),
}
```

`payment/domain/PaymentApproved.kt`

```kotlin
package com.tikitaka.payment.domain

data class PaymentApproved(
    val orderNo: String,
    val memberId: Long,
    val amount: Long,
    val approvedAt: Instant,
) : DomainEvent
```

`payment/domain/PaymentRepository.kt`

```kotlin
package com.tikitaka.payment.domain

interface PaymentRepository {
    fun save(payment: Payment): Payment
    fun findByPaymentKey(paymentKey: String): Payment?
}

fun PaymentRepository.getByPaymentKey(paymentKey: String) =
    findByPaymentKey(paymentKey) ?: throw BusinessException(PaymentError.PAYMENT_NOT_FOUND)
```

`payment/application/port/PaymentGateway.kt`

```kotlin
package com.tikitaka.payment.application.port

/** 결제 대행사 포트. 토스 응답 형식은 어댑터 밖으로 나오지 않습니다. */
interface PaymentGateway {
    fun confirm(paymentKey: String, orderNo: String, amount: Money): ConfirmResult
}
```

`payment/application/port/ConfirmResult.kt`

```kotlin
package com.tikitaka.payment.application.port

sealed interface ConfirmResult {
    data class Approved(val approvedAt: Instant) : ConfirmResult
    data class Rejected(val code: String, val message: String) : ConfirmResult
    data object Unknown : ConfirmResult
}
```

`payment/application/dto/ConfirmPaymentCommand.kt`

```kotlin
package com.tikitaka.payment.application.dto

data class ConfirmPaymentCommand(val paymentKey: String, val orderNo: String, val amount: Long)
```

`payment/application/ConfirmPaymentUseCase.kt`

```kotlin
package com.tikitaka.payment.application

@Service
class ConfirmPaymentUseCase(
    private val payments: PaymentRepository,
    private val orderPayments: OrderPaymentService,
    private val gateway: PaymentGateway,
    private val outbox: OutboxAppender,
    private val tx: TransactionTemplate,
) {
    fun execute(command: ConfirmPaymentCommand): PaymentStatus {
        val amount = Money(command.amount)

        // 1. 짧은 트랜잭션: 주문 검증과 결제 요청 기록
        val order = tx.execute {
            val payable = orderPayments.getPayable(command.orderNo, amount)
            payments.save(Payment.request(command.orderNo, command.paymentKey, amount))
            payable
        }!!

        // 2. 외부 호출은 트랜잭션 밖에서. DB 커넥션을 잡은 채로 토스를 기다리지 않음
        val result = gateway.confirm(command.paymentKey, command.orderNo, amount)

        // 3. 결과 반영. 결제 승인과 주문 결제 완료는 일부러 한 트랜잭션으로 묶음
        return tx.execute {
            val payment = payments.getByPaymentKey(command.paymentKey)
            when (result) {
                is ConfirmResult.Approved -> {
                    payment.approve(result.approvedAt)
                    orderPayments.markPaid(command.orderNo)
                    outbox.append(PaymentApproved(order.orderNo, order.memberId, amount.amount, result.approvedAt))
                }
                is ConfirmResult.Rejected -> payment.fail(result.code)
                ConfirmResult.Unknown -> payment.markUnknown()
            }
            payment.status
        }!!
    }
}
```

`payment/adapter/web/dto/ConfirmPaymentRequest.kt`

```kotlin
package com.tikitaka.payment.adapter.web.dto

data class ConfirmPaymentRequest(
    @NotBlank val paymentKey: String,
    @NotBlank val orderId: String,
    @Positive val amount: Long,
) {
    fun toCommand() = ConfirmPaymentCommand(paymentKey, orderId, amount)
}
```

`payment/adapter/web/dto/ConfirmPaymentResponse.kt`

```kotlin
package com.tikitaka.payment.adapter.web.dto

data class ConfirmPaymentResponse(val status: PaymentStatus)
```

`payment/adapter/web/PaymentController.kt`

```kotlin
package com.tikitaka.payment.adapter.web

@RestController
@RequestMapping("/api/v1/payments")
class PaymentController(private val confirmPayment: ConfirmPaymentUseCase) {
    @PostMapping("/confirm")
    fun confirm(@Valid @RequestBody request: ConfirmPaymentRequest) =
        ConfirmPaymentResponse(confirmPayment.execute(request.toCommand()))
}
```

## 외부 API 어댑터(ACL)

토스 응답 DTO는 `internal`로 두고 포트 결과 타입으로 번역합니다. Idempotency-Key는 `orderNo`입니다.

`payment/adapter/toss/TossPaymentResponse.kt`

```kotlin
package com.tikitaka.payment.adapter.toss

internal data class TossPaymentResponse(val status: String, val approvedAt: OffsetDateTime)
```

`payment/adapter/toss/TossErrorResponse.kt`

```kotlin
package com.tikitaka.payment.adapter.toss

internal data class TossErrorResponse(val code: String, val message: String)
```

`payment/adapter/toss/TossPaymentGateway.kt`

```kotlin
package com.tikitaka.payment.adapter.toss

@Component
class TossPaymentGateway(
    @Value("\${toss.secret-key}") secretKey: String,
    @Value("\${toss.base-url:https://api.tosspayments.com/v1}") baseUrl: String,
) : PaymentGateway {
    private val client = RestClient.builder()
        .baseUrl(baseUrl)
        .defaultHeaders { it.setBasicAuth(secretKey, "") }
        .requestFactory(SimpleClientHttpRequestFactory().apply {
            setConnectTimeout(Duration.ofSeconds(3))
            setReadTimeout(Duration.ofSeconds(30))
        })
        .build()

    override fun confirm(paymentKey: String, orderNo: String, amount: Money): ConfirmResult = try {
        val response = client.post().uri("/payments/confirm")
            .header("Idempotency-Key", orderNo)
            .contentType(MediaType.APPLICATION_JSON)
            .body(mapOf("paymentKey" to paymentKey, "orderId" to orderNo, "amount" to amount.amount))
            .retrieve()
            .body(TossPaymentResponse::class.java)!!
        ConfirmResult.Approved(response.approvedAt.toInstant())
    } catch (e: HttpClientErrorException) { // 4xx: 토스가 거절함
        val error = e.getResponseBodyAs(TossErrorResponse::class.java)
        ConfirmResult.Rejected(error?.code ?: "HTTP_${e.statusCode.value()}", error?.message.orEmpty())
    } catch (e: RestClientException) { // 타임아웃, 5xx: 승인됐는지 모름
        ConfirmResult.Unknown
    }
}
```

## Outbox

`append`는 트랜잭션 안에서만 부를 수 있습니다. 소비자는 `OutboxHandler`를 구현하고, 다른 컨텍스트 클래스 대신 자기 타입으로 읽습니다.

`common/domain/DomainEvent.kt`

```kotlin
package com.tikitaka.common.domain

/** Outbox로 내보내는 이벤트. 클래스 이름이 eventType이 되므로 이름을 바꾸면 소비자도 바꿔야 합니다. */
interface DomainEvent
```

`common/outbox/OutboxMessage.kt`

```kotlin
package com.tikitaka.common.outbox

@Entity
class OutboxMessage(
    val eventType: String,
    @Column(columnDefinition = "json") val payload: String,
) {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long = 0
        protected set

    val createdAt: Instant = Instant.now()

    var processedAt: Instant? = null
        protected set

    fun markProcessed() {
        processedAt = Instant.now()
    }
}
```

`common/outbox/OutboxMessageRepository.kt`

```kotlin
package com.tikitaka.common.outbox

interface OutboxMessageRepository : JpaRepository<OutboxMessage, Long> {
    @Query(
        value = "select * from outbox_message where processed_at is null order by id limit 1 for update skip locked",
        nativeQuery = true,
    )
    fun lockNextUnprocessed(): OutboxMessage?
}
```

`common/outbox/OutboxAppender.kt`

```kotlin
package com.tikitaka.common.outbox

@Component
class OutboxAppender(
    private val repository: OutboxMessageRepository,
    private val json: JsonMapper,
) {
    /** 상태 변경과 같은 트랜잭션에서만 호출합니다. 트랜잭션 밖에서 부르면 예외가 납니다. */
    @Transactional(propagation = Propagation.MANDATORY)
    fun append(event: DomainEvent) {
        repository.save(OutboxMessage(event::class.simpleName!!, json.writeValueAsString(event)))
    }
}
```

`common/outbox/OutboxHandler.kt`

```kotlin
package com.tikitaka.common.outbox

/** 같은 DB 안에서 이벤트를 처리하는 소비자. 처리와 처리 완료 표시가 한 트랜잭션이라 중복 처리되지 않습니다. */
interface OutboxHandler {
    val eventType: String
    fun handle(payload: String)
}
```

`common/outbox/OutboxRelay.kt`

```kotlin
package com.tikitaka.common.outbox

@Component
class OutboxRelay(
    private val repository: OutboxMessageRepository,
    handlers: List<OutboxHandler>,
    private val tx: TransactionTemplate,
) {
    private val handlers = handlers.associateBy { it.eventType }

    // TODO: 실패한 메시지가 큐 맨 앞을 막음. attempts 컬럼과 재시도 상한은 6주차 유실·중복 검증 때 추가
    @Scheduled(fixedDelayString = "\${outbox.relay.delay-ms:1000}")
    fun relay() {
        repeat(BATCH_SIZE) {
            if (tx.execute { processNext() } != true) return
        }
    }

    private fun processNext(): Boolean {
        val message = repository.lockNextUnprocessed() ?: return false
        val handler = handlers[message.eventType] ?: error("Outbox 핸들러 없음: ${message.eventType}")
        handler.handle(message.payload)
        message.markProcessed()
        return true
    }

    companion object {
        const val BATCH_SIZE = 100
    }
}
```

`point/adapter/event/PaymentApprovedMessage.kt`

```kotlin
package com.tikitaka.point.adapter.event

/** payment의 클래스를 import하지 않고, 필요한 필드만 자기 타입으로 읽습니다. */
@JsonIgnoreProperties(ignoreUnknown = true)
internal data class PaymentApprovedMessage(val memberId: Long, val amount: Long)
```

`point/adapter/event/PaymentApprovedPointHandler.kt`

```kotlin
package com.tikitaka.point.adapter.event

@Component
class PaymentApprovedPointHandler(
    private val earnPoint: EarnPointUseCase,
    private val json: JsonMapper,
) : OutboxHandler {
    override val eventType = "PaymentApproved"

    override fun handle(payload: String) {
        val message = json.readValue(payload, PaymentApprovedMessage::class.java)
        earnPoint.execute(message.memberId, Money(message.amount))
    }
}
```

## 인증과 설정(config)

인증 기능을 만들 때 아래 위치와 역할을 따릅니다. 코드가 생기면 그 파일을 기준으로 삼습니다.

| 파일 | 내용 |
|---|---|
| `auth/config/SecurityConfig.kt` | 필터 체인(`/api/v1/auth/**`만 공개), JWT 인코더·디코더, `PasswordEncoder`, `role` 클레임 → `ROLE_` 권한 |
| `auth/config/AuthProperties.kt` | `@ConfigurationProperties("auth")`. 시크릿 길이를 `init`에서 검사합니다 |
| `auth/application/util/TokenIssuer.kt` | 여러 유스케이스(로그인, 재발급)가 함께 쓰는 도우미라 `util/`에 둡니다 |
| `auth/application/service/MemberQueryService.kt` | 조회 서비스라 `service/`에 둡니다 |
| `auth/adapter/redis/RedisRefreshTokenStore.kt` | `application/port/RefreshTokenStore` 구현. GETDEL로 읽으면서 지웁니다 |

다른 컨텍스트 컨트롤러는 auth를 import하지 않고 위 `OrderController`처럼 `jwt.subject`를 씁니다.
