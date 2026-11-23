# 테스트

| 계층 | 도구 | 원칙 |
|---|---|---|
| domain | Kotest | 목을 쓰지 않습니다. 업무 규칙은 여기서 검증합니다 |
| application | Kotest, MockK | 리포지토리, 포트, 다른 컨텍스트 공개 서비스만 목으로 바꿉니다 |
| adapter.persistence | `@DataJpaTest`, Testcontainers MySQL | H2 대신 실제 MySQL을 씁니다(락, 네이티브 쿼리) |
| adapter.toss, kopis | WireMock | 4xx, 5xx, 타임아웃 응답을 재현합니다 |
| 구조 | ArchUnit | 구조 규칙 5개. 모든 PR에서 실행합니다 |
| 파일 | SourceRulesTest | 파일당 최상위 타입 하나, 200줄 이하 |

테스트 위치는 main과 같은 패키지(`src/test/kotlin/com/tikitaka/<context>/<계층>/`)입니다.

## 의존성

```kotlin
testImplementation("org.springframework.boot:spring-boot-starter-data-jpa-test")
testImplementation("org.springframework.boot:spring-boot-testcontainers")
testImplementation("org.testcontainers:testcontainers-mysql")
testImplementation("io.kotest:kotest-runner-junit5:6.2.7")
testImplementation("io.kotest:kotest-extensions-spring:6.2.7")
testImplementation("io.mockk:mockk:1.14.12")
testImplementation("com.tngtech.archunit:archunit:1.5.1") // 스택 표에 추가하려면 type:decision Issue
```


## 아키텍처 테스트

새 컨텍스트를 만들면 `contexts` 목록에 추가합니다. 다른 컨텍스트의 domain을 일부러 import했을 때 세 번째 테스트가 실패하는 것을 확인했습니다.

`ArchitectureTest.kt`

```kotlin
package com.tikitaka

class ArchitectureTest : FunSpec({
    val imported = ClassFileImporter()
        .withImportOption(ImportOption.DoNotIncludeTests())
        .importPackages("com.tikitaka")
    val contexts = listOf("auth", "catalog", "order", "payment", "point", "settlement")

    test("domain은 application, adapter, config, Spring을 모른다") {
        noClasses().that().resideInAPackage("..domain..")
            .should().dependOnClassesThat()
            .resideInAnyPackage("..application..", "..adapter..", "..config..", "org.springframework..")
            .check(imported)
    }

    test("application은 adapter를 모른다") {
        noClasses().that().resideInAPackage("..application..")
            .should().dependOnClassesThat().resideInAPackage("..adapter..")
            .check(imported)
    }

    test("다른 컨텍스트의 domain, adapter, config를 import하지 않는다 (application만 호출)") {
        contexts.forEach { context ->
            noClasses().that().resideOutsideOfPackage("com.tikitaka.$context..")
                .should().dependOnClassesThat()
                .resideInAnyPackage("com.tikitaka.$context.domain..", "com.tikitaka.$context.adapter..", "com.tikitaka.$context.config..")
                .check(imported)
        }
    }

    test("application(하위 도메인 패키지 포함) 바로 아래에는 UseCase만 둔다") {
        classes().that().resideInAPackage("com.tikitaka.*.application..")
            .and().resideOutsideOfPackages("..dto..", "..service..", "..util..", "..port..")
            .and().areTopLevelClasses()
            .should().haveSimpleNameEndingWith("UseCase")
            .allowEmptyShould(true)
            .check(imported)
    }

    test("common은 업무 컨텍스트를 모른다") {
        noClasses().that().resideInAPackage("com.tikitaka.common..")
            .should().dependOnClassesThat()
            .resideInAnyPackage(*contexts.map { "com.tikitaka.$it.." }.toTypedArray())
            .check(imported)
    }
})
```

## 파일 규칙 테스트

한 파일에 클래스를 둘 넣었을 때 첫 번째 테스트가 실패하는 것을 확인했습니다. 줄 수 기준을 바꾸려면 `maxLines`를 고치고 SKILL.md도 함께 고칩니다.

`SourceRulesTest.kt`

```kotlin
package com.tikitaka

class SourceRulesTest : FunSpec({
    val maxLines = 200
    val sources = File("src/main/kotlin").walkTopDown().filter { it.extension == "kt" }.toList()
    val topLevelType = Regex(
        """^(?:(?:public|internal|private|data|enum|sealed|abstract|open|annotation|value)\s+)*(?:class|interface|object)\s+(\w+)""",
        RegexOption.MULTILINE,
    )

    test("파일 하나에 최상위 타입 하나, 파일 이름은 타입 이름과 같다") {
        assertSoftly {
            sources.forEach { file ->
                val types = topLevelType.findAll(file.readText()).map { it.groupValues[1] }.toList()
                withClue(file.path) {
                    types shouldHaveAtMostSize 1
                    types.firstOrNull()?.let { it shouldBe file.nameWithoutExtension }
                }
            }
        }
    }

    test("파일은 ${maxLines}줄 이하") {
        assertSoftly {
            sources.forEach { file ->
                withClue(file.path) { file.readLines().size shouldBeLessThanOrEqual maxLines }
            }
        }
    }
})
```

## 도메인 테스트

`order/domain/OrderTest.kt`

```kotlin
package com.tikitaka.order.domain

class OrderTest : FunSpec({
    fun order() = Order.place(memberId = 1, scheduleId = 1, amount = Money(10_000))

    test("결제 금액이 주문 금액과 다르면 거절한다") {
        shouldThrow<BusinessException> { order().verifyPayable(Money(9_000)) }
            .error shouldBe OrderError.AMOUNT_MISMATCH
    }

    test("결제 완료는 한 번만 할 수 있다") {
        val order = order()
        order.markPaid()
        order.status shouldBe OrderStatus.PAID
        shouldThrow<BusinessException> { order.markPaid() }.error shouldBe OrderError.NOT_PAYABLE
    }
})
```

## 유스케이스 테스트

`TransactionTemplate`은 콜백을 바로 실행하도록 목으로 바꿉니다.

`payment/application/ConfirmPaymentUseCaseTest.kt`

```kotlin
package com.tikitaka.payment.application

class ConfirmPaymentUseCaseTest : FunSpec({
    val command = ConfirmPaymentCommand(paymentKey = "pk", orderNo = "order-1", amount = 10_000)

    class Fixture(result: ConfirmResult) {
        val saved = slot<Payment>()
        val payments = mockk<PaymentRepository> {
            every { save(capture(saved)) } answers { saved.captured }
            every { findByPaymentKey("pk") } answers { saved.captured }
        }
        val orderPayments = mockk<OrderPaymentService> {
            every { getPayable("order-1", Money(10_000)) } returns PayableOrder("order-1", 7, Money(10_000))
            every { markPaid("order-1") } just runs
        }
        val gateway = mockk<PaymentGateway> { every { confirm(any(), any(), any()) } returns result }
        val outbox = mockk<OutboxAppender>(relaxed = true)
        val tx = mockk<TransactionTemplate> {
            every { execute(any<TransactionCallback<Any?>>()) } answers {
                firstArg<TransactionCallback<Any?>>().doInTransaction(mockk(relaxed = true))
            }
        }
        val useCase = ConfirmPaymentUseCase(payments, orderPayments, gateway, outbox, tx)
    }

    test("승인되면 주문을 결제 완료로 바꾸고 이벤트를 남긴다") {
        val f = Fixture(ConfirmResult.Approved(Instant.parse("2026-12-14T00:00:00Z")))
        f.useCase.execute(command) shouldBe PaymentStatus.APPROVED
        verify { f.orderPayments.markPaid("order-1") }
        verify { f.outbox.append(match { it.shouldBeInstanceOf<PaymentApproved>().memberId == 7L }) }
    }

    test("결과를 모르면 UNKNOWN으로 남기고 주문은 건드리지 않는다") {
        val f = Fixture(ConfirmResult.Unknown)
        f.useCase.execute(command) shouldBe PaymentStatus.UNKNOWN
        verify(exactly = 0) { f.orderPayments.markPaid(any()) }
    }
})
```

## Persistence 테스트

마이그레이션 도구를 정하기 전까지는 `ddl-auto=create-drop`을 씁니다. 정하면 이 속성을 지우고 마이그레이션으로 스키마를 만듭니다.

`order/adapter/persistence/OrderPersistenceAdapterTest.kt`

```kotlin
package com.tikitaka.order.adapter.persistence

@DataJpaTest(properties = ["spring.jpa.hibernate.ddl-auto=create-drop"])
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Import(OrderPersistenceAdapter::class)
class OrderPersistenceAdapterTest : FunSpec() {
    @Autowired lateinit var orders: OrderRepository

    override val extensions: List<Extension> = listOf(SpringExtension())

    init {
        test("저장한 주문을 주문번호로 다시 읽는다") {
            val saved = orders.save(Order.place(memberId = 1, scheduleId = 2, amount = Money(15_000)))
            val found = orders.findByOrderNo(saved.orderNo)!!
            found.amount shouldBe Money(15_000)
            found.memberId shouldBe 1
        }
    }

    companion object {
        @JvmField
        @ServiceConnection
        val mysql = MySQLContainer("mysql:8.4")
    }
}
```

## 인증이 필요한 통합 테스트

`@SpringBootTest` + `@AutoConfigureMockMvc`로 띄우고, MySQL과 함께 Redis 컨테이너를 붙입니다. 시크릿은 테스트 속성으로 넣습니다. 인증 흐름 전체(가입 → 로그인 → 재발급 → 로그아웃)는 auth 컨텍스트의 `adapter/web` 테스트에서 한 번 검증합니다.

```kotlin
@SpringBootTest(properties = ["spring.jpa.hibernate.ddl-auto=create-drop", "auth.jwt-secret=test-secret-test-secret-test-secret-0123"])
@AutoConfigureMockMvc
class XxxFlowTest : FunSpec() {
    // ...
    companion object {
        @JvmField @ServiceConnection
        val mysql = MySQLContainer("mysql:8.4")

        @JvmField @ServiceConnection(name = "redis")
        val redis: GenericContainer<*> = GenericContainer("redis:7.4").withExposedPorts(6379)
    }
}
```

로그인이 필요한 API는 `/api/v1/auth/login`으로 받은 토큰을 `Authorization: Bearer <accessToken>` 헤더에 넣어 부릅니다.
