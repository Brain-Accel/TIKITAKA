---
name: backend-architecture
description: TIKITAKA 백엔드(backend/, Kotlin·Spring Boot·JPA)의 패키지 구조와 코드 작성 규칙집. backend/의 코드를 새로 만들 때뿐 아니라 기존 코드를 수정, 버그 수정, 리팩터링할 때도 사용합니다. pstack의 architect, 구현, 리뷰 단계에서 backend 코드를 다룰 때도 설계 입력으로 읽습니다. 유스케이스, 엔티티, 리포지토리, 외부 API 연동(토스, KOPIS), Outbox 이벤트를 다룰 때, 클래스를 어디에 둘지 정하거나 파일이 길어져 나눌 때, 백엔드 PR을 구조 관점에서 리뷰할 때 사용합니다. 앱(app/)과 인프라(infra/)에는 쓰지 않습니다.
---

# TIKITAKA 백엔드 아키텍처

컨텍스트별 패키지, 헥사고날(포트·어댑터), 실용적 DDD를 섞은 구조입니다. [clean-ddd-hexagonal](https://github.com/ccheney/robust-skills/tree/main/skills/clean-ddd-hexagonal)의 원칙을 우리 스택에 맞춰 확정했습니다. 사용자의 지시가 이 문서와 다르면 사용자 지시를 따르고, 규칙을 바꾸면 ADR을 남깁니다.

## 확정한 결정

| 주제 | 결정 | 이유 |
|---|---|---|
| 최상위 구조 | 업무 컨텍스트별 패키지(`auth`, `catalog`, `order`, `payment`, `point`, `settlement`)와 `common` | 소유 영역 단위로 코드가 모입니다 |
| 컨텍스트 안 | `domain` / `application` / `adapter` 3계층과 설정용 `config` | 원본의 presentation 계층은 `adapter.web`에 합칩니다. application 바로 아래에는 유스케이스만 두고, Command·Result는 `application.dto`, 서비스는 `application.service`, 도우미는 `application.util`, 설정 클래스는 `config`에 모읍니다 |
| 도메인 모델과 JPA | 도메인 엔티티에 JPA 어노테이션을 허용합니다. 별도 JPA 엔티티와 매퍼는 만들지 않습니다 | 2명이 10주 안에 만들고, N+1·인덱스 실험을 엔티티에 바로 합니다. 대신 domain은 Spring을 import하지 않습니다 |
| 리포지토리 | 애그리거트당 1개. 인터페이스는 domain, 구현은 `adapter.persistence`에 둡니다. Spring Data는 어댑터 안에서만 씁니다 | 원본의 DDD 중심 변형과 같습니다 |
| 들어오는 포트 | 인터페이스를 만들지 않고, 컨트롤러가 유스케이스 클래스를 바로 호출합니다 | 구현이 하나뿐인 인터페이스는 만들지 않습니다 |
| 나가는 포트 | DB를 뺀 바깥 시스템(토스, KOPIS, 알림)만 `application/port`에 인터페이스로 둡니다 | 테스트에서 가짜로 바꿔 끼웁니다 |
| 컨텍스트 간 호출 | 동기 호출은 상대 컨텍스트 `application`의 공개 서비스로만 하고, 반환값은 값(DTO, `Money`)입니다. 비동기는 Outbox 이벤트로 합니다 | ArchUnit으로 강제합니다 |
| 인증 | JWT 액세스 토큰(HS256, 30분, `subject` = memberId, `role` 클레임)과 리프레시 토큰(불투명 UUID, Redis 14일, 쓸 때마다 교체)을 씁니다. 검증은 Spring `oauth2-resource-server`에 맡깁니다 | 사용자 결정(RN 앱). 다른 컨텍스트는 auth를 호출하지 않고 `@AuthenticationPrincipal jwt: Jwt`의 `jwt.subject`로 memberId를 얻습니다 |
| 이벤트 | Outbox 테이블과 폴링 워커를 씁니다. 같은 DB의 소비자는 처리와 완료 표시를 한 트랜잭션에서 합니다 | 마스터 플랜대로 브로커를 두지 않습니다 |
| CQRS, 이벤트 소싱 | 쓰지 않습니다. 목록 조회만 `XxxReader`로 분리할 수 있습니다 | 원본도 필요하기 전에 CQRS를 도입하지 말라고 합니다 |
| 파일 크기 | 파일 하나에 최상위 타입 하나, 파일은 200줄 이하 | 파일만 보고 내용을 알 수 있고, 리뷰 범위가 작아집니다 |
| 강제 수단 | ArchUnit 테스트 5개와 파일 규칙 테스트 2개([references/testing.md](references/testing.md)) | 리팩터링 뒤에도 규칙이 지켜집니다 |

## 패키지 구조

```
backend/src/main/kotlin/com/tikitaka/
├── common/
│   ├── domain/        Money, DomainEvent
│   ├── error/         ErrorCode, ErrorKind, BusinessException
│   ├── outbox/        OutboxMessage, OutboxAppender, OutboxRelay, OutboxHandler
│   └── web/           GlobalExceptionHandler (ErrorResponse는 web/dto/)
└── <context>/                         예: payment
    ├── domain/        애그리거트(@Entity), 값 객체(@Embeddable), enum, 이벤트, Repository 인터페이스, XxxError
    ├── application/   XxxUseCase만 둡니다
    │   ├── dto/       Command, Result, 다른 컨텍스트에 돌려주는 값(PayableOrder)
    │   ├── service/   XxxQueryService(조회), 다른 컨텍스트용 공개 서비스(OrderPaymentService)
    │   ├── util/      여러 유스케이스가 함께 쓰는 도우미(TokenIssuer)
    │   └── port/      바깥 시스템 포트(PaymentGateway), 목록 조회 포트(XxxReader)
    ├── config/        @Configuration, @ConfigurationProperties(SecurityConfig, AuthProperties)
    └── adapter/
        ├── web/          Controller (Request/Response는 web/dto/)
        ├── persistence/  Spring Data 인터페이스, XxxPersistenceAdapter, 조회 쿼리
        ├── toss/ kopis/  외부 API 클라이언트(외부 형식을 우리 타입으로 번역)
        ├── event/        OutboxHandler 구현(다른 컨텍스트 이벤트 수신)
        └── scheduler/    @Scheduled 작업(KOPIS 수집, 결제 결과 복구)
```

`adapter.in`과 `adapter.out`은 쓰지 않습니다. `in`이 Kotlin 예약어라 백틱을 붙여야 하기 때문에, 기술 이름으로 나눕니다.

## 어디에 둘까

1. 업무 규칙과 상태 전이(예: "PENDING일 때만 결제 완료")는 domain 메서드에 둡니다.
2. 여러 애그리거트, 외부 호출, 트랜잭션 순서를 조율하는 코드는 application 유스케이스에 둡니다.
3. HTTP, DB 쿼리, 토스·KOPIS 형식, 스케줄은 adapter에 둡니다.
4. 클래스 종류로도 나눕니다. 계층 바로 아래에는 그 계층의 주인공(application은 UseCase, web은 Controller)만 두고, 주고받는 데이터는 `dto/`, 설정은 `config/`로 보냅니다.
5. 두 컨텍스트가 같은 개념을 쓰면 정말 같은 의미인지 먼저 확인합니다. 같으면 값만 `common.domain`에 두고(예: `Money`), 다르면 각자 정의합니다.

애그리거트 경계는 이렇게 정합니다. 함께 원자적으로 바뀌어야 하면 같은 애그리거트로 묶고, 따로 존재할 수 있으면 나눈 뒤 ID로 참조합니다. 애그리거트 사이에는 `@ManyToOne` 같은 객체 참조를 쓰지 않습니다.

## 코드 규칙

### 파일과 클래스 크기

- 파일 하나에 최상위 클래스·인터페이스·enum·object를 하나만 두고, 파일 이름을 타입 이름과 같게 합니다. Command, Result, Request, Response, 외부 API DTO, enum도 각자 파일에 둡니다.
- 같은 파일에 둬도 되는 것: 그 타입 안에 중첩된 타입(예: `ConfirmResult`의 sealed 하위 타입), 그 타입에 딸린 확장 함수(예: `OrderRepository.getByOrderNo`), private 함수.
- 파일은 200줄을 넘지 않습니다. `SourceRulesTest`가 강제합니다.
- 수정하거나 기능을 추가할 때 파일이 150줄을 넘을 것 같으면, 코드를 덧붙이기 전에 먼저 나눕니다. 함수가 30줄을 넘거나 생성자 의존성이 6개 이상이면 책임이 많다는 신호이니 같은 방법으로 나눕니다.

길어지면 아래 순서로 나눕니다. 앞 단계로 해결되면 거기서 멈춥니다.

1. **클래스에서 뽑기:** 함께 다니는 값과 검증은 값 객체(`@Embeddable`)로, 여러 애그리거트에 걸친 규칙은 도메인 서비스로, 바뀔 수 있는 계산 규칙(할인, 적립률)은 `XxxPolicy` 클래스로 뽑습니다.
2. **유스케이스 나누기:** 한 유스케이스가 두 가지 일을 하면 둘로 나눕니다(예: 결제 승인 요청과 결과 불명 복구). 컨트롤러와 어댑터는 리소스나 외부 API 기능 단위로 나눕니다(예: `TossConfirmClient`, `TossCancelClient`).
3. **하위 도메인 패키지:** 한 패키지에 파일이 10개를 넘거나 애그리거트가 둘 이상이 되면, 각 계층 아래에 하위 도메인 패키지를 둡니다(예: `order/domain/seat/`, `order/application/seat/`, `order/adapter/web/seat/`). 하위 도메인 패키지도 바로 아래에는 UseCase·Controller만 두고 `order/application/seat/dto/`, `order/adapter/web/seat/dto/`처럼 같은 하위 구조를 씁니다. 계층이 바깥에 있으니 ArchUnit 규칙은 그대로 적용됩니다.
4. **새 컨텍스트로 분리:** 하위 도메인이 자기 용어와 생명주기를 가지면 새 컨텍스트로 분리합니다. 이 단계는 사용자와 상의하고, [references/contexts.md](references/contexts.md)와 `ArchitectureTest`의 `contexts` 목록을 함께 고칩니다.

### domain

- import할 수 있는 것: Kotlin 표준 라이브러리, `jakarta.persistence`, `com.tikitaka.common.domain`, `com.tikitaka.common.error`. Spring은 import하지 않습니다.
- 상태는 `var x ... protected set`으로 두고, 의미 있는 메서드(`markPaid()`)로만 바꿉니다. kotlin-jpa allopen 플러그인 때문에 `private set`은 쓸 수 없어서 `protected`를 씁니다.
- 생성은 `private constructor`와 `companion object` 팩토리(`Order.place(...)`)로 합니다.
- 업무 규칙을 어기면 `BusinessException(XxxError.CODE)`를 던지고, 값 형식 오류는 `require`로 막습니다.
- 엔티티는 data class로 만들지 않고 `equals`도 재정의하지 않습니다. 값 객체는 `@Embeddable data class`로 만듭니다. 한 엔티티에 같은 값 객체가 두 개 이상이면 `@AttributeOverride`를 붙입니다.
- Repository 인터페이스에는 애그리거트 단위의 `save`와 `findByXxx(): T?`만 둡니다. 없으면 예외를 던지는 `getByXxx`는 같은 파일에 확장 함수로 만듭니다.
- 목록, 검색, 통계 쿼리는 Repository에 넣지 않습니다. `application/port`의 `XxxReader`를 만들고 persistence에서 구현해 DTO를 돌려줍니다.

### application

- `application` 바로 아래에는 `XxxUseCase`만 둡니다. 나머지는 하위 패키지로 보냅니다: Command·Result는 `dto/`, 조회 서비스와 다른 컨텍스트용 공개 서비스는 `service/`, 여러 유스케이스가 함께 쓰는 도우미(예: `TokenIssuer`)는 `util/`, 바깥 시스템 포트는 `port/`에 둡니다.
- 명령 유스케이스 하나가 클래스 하나입니다. 이름은 `XxxUseCase`이고, 공개 메서드는 `execute(command)` 하나입니다. Command와 Result data class는 `application/dto`에 각자 파일로 둡니다.
- 조회는 `application/service`의 `XxxQueryService`(`readOnly = true`)에 둡니다.
- `@Transactional`은 application에만 붙입니다. 외부 API 호출이 끼면 `TransactionTemplate`으로 나눕니다: 짧은 트랜잭션 → 트랜잭션 밖에서 외부 호출 → 결과를 반영하는 트랜잭션.
- 변경은 JPA 변경 감지로 저장하고, `save`는 새로 만들 때만 부릅니다.
- 다른 컨텍스트가 부를 메서드는 `application/service`의 `XxxService`(예: `OrderPaymentService`)에 모으고 값만 돌려줍니다. 호출하는 쪽 트랜잭션 안에서만 불려야 하면 `Propagation.MANDATORY`를 붙입니다.
- 여기에 if 분기로 상태를 판단하는 업무 규칙이 생기면 domain으로 옮깁니다.
- `ArchitectureTest`가 application(하위 도메인 패키지 포함) 바로 아래의 최상위 클래스 이름이 `UseCase`로 끝나는지 검사합니다.

### config

- `@Configuration`, `@ConfigurationProperties`는 컨텍스트의 `config/`에 둡니다(예: `auth/config/SecurityConfig`, `auth/config/AuthProperties`). 앱 전체에 걸린 설정이라도 주인 컨텍스트에 둡니다. 보안 설정은 auth가 주인입니다.
- application과 adapter는 config의 프로퍼티 클래스를 읽을 수 있습니다. domain은 config를 모르고, 다른 컨텍스트는 상대의 config를 import하지 않습니다(ArchUnit).
- 새 공개 경로(로그인 없이 부를 API, 예: 공연 목록)를 만들면 `SecurityConfig`의 `permitAll` 목록에 추가합니다. 나머지 경로는 모두 Bearer 토큰을 요구합니다.

### adapter

- **web:** Request·Response는 `adapter/web/dto`에 둡니다. 로그인한 회원 id는 `@AuthenticationPrincipal jwt: Jwt`의 `jwt.subject!!.toLong()`으로 꺼내고, 요청 본문이나 헤더로 받지 않습니다. Request DTO에 Bean Validation을 붙이고 `toCommand()`로 변환합니다. 도메인 엔티티를 응답으로 그대로 내보내지 않습니다. enum은 내보내도 됩니다. 금액과 가격은 클라이언트가 보낸 값을 믿지 않고 서버에서 정합니다.
- **persistence:** `XxxJpaRepository : JpaRepository`와 `@Repository class XxxPersistenceAdapter : XxxRepository`를 같은 패키지에 각자 파일로 둡니다. 락, 조건부 UPDATE, 키셋 페이징 쿼리도 여기에 둡니다.
- **외부 API(toss, kopis):** 응답 DTO는 `internal`로 두고 포트의 결과 타입으로 번역합니다(ACL). 타임아웃은 반드시 설정합니다. 4xx는 거절, 타임아웃과 5xx는 결과 불명으로 처리합니다.
- **event:** 다른 컨텍스트의 이벤트 클래스를 import하지 않습니다. 필요한 필드만 자기 `internal data class`로 읽습니다.

### 이벤트(Outbox)

- 상태 변경과 같은 트랜잭션에서 `outboxAppender.append(XxxHappened(...))`를 부릅니다. 이벤트 이름은 과거형이고, 클래스 이름이 eventType이 됩니다.
- 같은 DB의 소비자(`OutboxHandler`)는 중복을 걱정하지 않아도 됩니다. DB 밖으로 보내는 소비자(n8n, Discord)는 최소 한 번 이상 전달될 수 있으므로 받는 쪽이 멱등해야 합니다.
- 이벤트 필드를 지우거나 이름을 바꿀 때는 먼저 소비자를 확인하고, SwarmCode와 Issue로 상대에게 알립니다.

## pstack과 함께 쓰기

작업 흐름은 pstack(`poteto-mode`, architect, tdd, 리뷰 등)을 따릅니다. 이 스킬은 그 흐름 안에서 코드를 어디에 어떤 모양으로 둘지 정할 때 참고하는 규칙집입니다. architect가 "변경이 닿는 시스템"을 추적할 때 이 문서와 [references/patterns.md](references/patterns.md)를 함께 읽고, 두 가지 모양을 그릴 때도 둘 다 이 규칙 안에서 그립니다.

pstack 원칙을 덮어쓰는 예외는 두 가지뿐입니다. 나머지는 pstack을 그대로 따릅니다.

1. **의도한 경계는 합치지 않습니다.** domain의 Repository 인터페이스, `adapter.persistence`의 PersistenceAdapter, `application/port`의 포트는 구현이 하나뿐이어도 Minimize Reader Load나 Laziness Protocol의 인라인 대상이 아닙니다. domain이 Spring을 모르게 하려고 둔 경계이고, 합치면 `ArchitectureTest`가 실패합니다. 그 밖의 전달만 하는 래퍼에는 pstack 원칙을 적용합니다.
2. **컨벤션을 바꾸는 재설계는 제안만 합니다.** Redesign from First Principles나 architect가 패키지 구조, 계층, 파일 규칙 자체를 바꾸는 모양을 고르면 구현하지 않습니다. 이유와 두 모양을 정리해 type:decision Issue로 넘기고, 이번 작업은 현재 컨벤션 안의 모양으로 진행합니다.

파일 하나에 타입 하나, 200줄 규칙과 계층 의존 규칙은 테스트가 강제하므로 따로 확인할 필요 없이 `./gradlew test`로 검증합니다.

## 새 기능 만드는 순서

pstack 없이 작업할 때의 순서입니다. pstack을 쓸 때는 pstack 워크플로를 따르고, 아래 순서는 빠진 단계가 없는지 확인하는 용도로만 씁니다.

1. 어느 컨텍스트에 속하는지, 새 애그리거트가 필요한지 정합니다. 업무 규칙이 불명확하면 지어내지 말고, Issue에 질문을 남긴 뒤 그 규칙에 걸리지 않는 부분부터 만듭니다.
2. domain 코드와 도메인 테스트를 작성합니다. 도메인 테스트는 목을 쓰지 않습니다.
3. application 유스케이스와 MockK 테스트를 작성합니다. 목은 포트와 리포지토리에만 씁니다.
4. adapter(web, persistence, 외부)와 통합 테스트를 작성합니다. Testcontainers MySQL과 WireMock을 씁니다.
5. `./gradlew test`를 실행해 ArchitectureTest와 SourceRulesTest까지 통과하는지 확인합니다.

기존 코드를 고칠 때는 먼저 고칠 파일의 길이를 확인합니다. 고친 뒤 150줄을 넘을 것 같으면 "파일과 클래스 크기"의 순서대로 먼저 나누고, 나누는 커밋과 기능 커밋을 따로 만듭니다.

## 리뷰 체크리스트

- domain이 Spring을 import하거나, 다른 컨텍스트의 domain·adapter를 import하는가
- 컨트롤러가 리포지토리를 바로 부르는가
- 트랜잭션 안에서 외부 API를 호출하는가
- 클라이언트가 보낸 금액이나 가격을 그대로 믿는가
- 애그리거트 사이에 `@ManyToOne`이나 객체 참조가 있는가
- 업무 규칙이 유스케이스에 있고 엔티티에는 getter만 있는가(빈약한 도메인)
- 이벤트를 트랜잭션 밖에서 기록하는가, 외부로 보내는 소비자에 멱등 처리가 없는가
- 구현이 하나뿐인 인터페이스를 추가했는가
- 한 파일에 타입이 둘 이상이거나, 150줄을 넘겨서 나눌 때가 됐는가
- Command·Result·Request·Response가 `dto/` 밖에 있거나, 설정 클래스가 `config/` 밖에 있는가
- memberId를 JWT가 아니라 요청 값에서 받는가

## 아직 정하지 않은 것

- **마이그레이션 도구:** Flyway를 가정합니다. `/design-schema`를 쓸 때 정합니다.
- **좌석 선점, 결제 시간 제한, 대기열:** 요구사항이 확정되면 order 애그리거트를 설계합니다.
- **ArchUnit:** 마스터 플랜의 스택 표에 없습니다. `backend/`를 만들 때 함께 넣고, type:decision Issue로 확정해야 합니다.
- **패키지 세분화(dto, service, util, config):** 사용자 지시로 반영했습니다. type:decision Issue와 ADR로 확정해야 합니다.
- **포인트 원장(복식부기) 구조:** 6주차 `/design-schema`에서 정합니다. 예시의 `PointAccount`는 패턴을 보여주기 위한 것입니다.
- **패키지 루트:** `com.tikitaka`로 가정합니다.

## 참고

- [references/patterns.md](references/patterns.md): Kotlin 코드 템플릿입니다. 컴파일하고 테스트한 코드입니다.
- [references/testing.md](references/testing.md): 테스트 구성과 ArchUnit 규칙입니다.
- [references/contexts.md](references/contexts.md): 컨텍스트, 용어, 컨텍스트 사이 관계입니다.
- 더 깊은 개념은 원본 참고 문서를 봅니다. 예시가 TypeScript이니 개념만 가져옵니다.
  - 계층과 의존 방향: [LAYERS.md](https://github.com/ccheney/robust-skills/blob/main/skills/clean-ddd-hexagonal/references/LAYERS.md)
  - 애그리거트, 값 객체, 리포지토리: [DDD-TACTICAL.md](https://github.com/ccheney/robust-skills/blob/main/skills/clean-ddd-hexagonal/references/DDD-TACTICAL.md)
  - 포트와 어댑터: [HEXAGONAL.md](https://github.com/ccheney/robust-skills/blob/main/skills/clean-ddd-hexagonal/references/HEXAGONAL.md)
  - Outbox, 사가, 멱등 소비자: [CQRS-EVENTS.md](https://github.com/ccheney/robust-skills/blob/main/skills/clean-ddd-hexagonal/references/CQRS-EVENTS.md)
  - ACL, 컨텍스트 매핑: [DDD-STRATEGIC.md](https://github.com/ccheney/robust-skills/blob/main/skills/clean-ddd-hexagonal/references/DDD-STRATEGIC.md)
  - 테스트: [TESTING.md](https://github.com/ccheney/robust-skills/blob/main/skills/clean-ddd-hexagonal/references/TESTING.md)

원본: ccheney/robust-skills `clean-ddd-hexagonal` (MIT, [UPSTREAM_LICENSE](UPSTREAM_LICENSE))
