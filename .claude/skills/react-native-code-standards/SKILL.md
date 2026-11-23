---
name: "react-native-code-standards"
description: "TIKITAKA 앱(app/, React Native·Expo)의 코드 구조와 작성 규칙집: 네이밍, 컴포넌트 구조, Clean Architecture·DDD·포트/어댑터, 상태와 데이터, 에러 처리, 백엔드 연동, 테스트. app/의 .ts/.tsx 코드를 새로 만들거나 수정·리팩터링·리뷰할 때 사용. pstack의 architect, 구현, 리뷰 단계에서 app/ 코드를 다룰 때도 설계 입력으로 읽는다. 디자인·스타일은 제외."
---

# React Native Code Standards

React Native 앱을 확장 가능하고 테스트하기 쉽게 만드는 코드 표준이다. RN 앱 전반에 쓰는 범용 규칙을 바탕으로, 맨 앞의 "TIKITAKA에서 정한 것"과 "백엔드 연동"에 이 프로젝트의 결정을 더했다.

원본은 alexandrebenkendorf/agents-playbooks의 `code-standards`와 `react-component-structure`(MIT, [UPSTREAM_LICENSE](UPSTREAM_LICENSE))이다. 원본의 규칙 체계는 유지하고, 웹(DOM·브라우저) 전용 내용을 RN 기준으로 바꿨다.

## TIKITAKA에서 정한 것

범용 규칙이 여러 선택지를 열어 둔 곳은 아래로 고정한다. 바꿀 때는 type:decision Issue와 ADR을 남긴다.

| 주제 | 결정 | 근거 |
|---|---|---|
| 앱 기반 | Expo, EAS Build | README 기술 스택 |
| 라우팅 | Expo Router(`src/app/`). React Navigation 규칙은 적용하지 않는다 | Expo 기본 |
| 서버 상태 | TanStack Query. 캐시 키 팩토리, `focusManager`·`onlineManager` 연결(9장)을 처음부터 넣는다 | README 기술 스택 |
| 스타일 | NativeWind. 스타일 값 규칙은 이 문서 범위 밖이다 | README 기술 스택 |
| 보안 저장소 | `expo-secure-store` | Expo 기본, 9장 |
| E2E | Maestro, `testID` 기반 | 마스터 플랜 테스트 스택 |
| 기능 폴더 이름 | 백엔드 컨텍스트와 같게: `auth`, `catalog`, `order`, `payment`, `point` | 같은 개념에 같은 이름(1-5) |
| 자동 검사 | `app/`을 만들 때 `tsc` strict와 ESLint 레이어 규칙([references/automation.md](references/automation.md))을 처음부터 넣는다 | 규칙을 사람보다 도구가 먼저 잡게(13장) |

**아직 정하지 않은 것** (정할 때까지 괄호 안을 기본값으로 쓴다)

- 단위 테스트 도구(Jest, `jest-expo` 프리셋, React Native Testing Library)
- 런타임 검증 라이브러리(zod)
- 엔티티·값 객체 표현(7-6의 두 방식 중 `type` + 순수 함수. pstack `typescript-best-practices`의 판별 유니온과 잘 맞는다)
- 전역 클라이언트 상태(`useState`와 Context. 전역 스토어 라이브러리는 필요해질 때 정한다)

## 백엔드 연동

백엔드 규칙은 `backend-architecture` 스킬에 있다. 앱은 아래를 맞춘다.

- **용어:** 백엔드 용어 사전(`.claude/skills/backend-architecture/references/contexts.md`)과 같은 단어를 쓴다. 예: 주문번호는 `orderNo`, 결제 키는 `paymentKey`, 회차는 `Schedule`.
- **에러:** 백엔드 에러 응답은 `{ code, message }`이고 HTTP 상태로 종류가 나뉜다. `core/http` 어댑터에서 아래처럼 `AppError`로 바꾸고, 서버의 `code`(예: `AMOUNT_MISMATCH`)는 `serverCode`로 함께 넘긴다. 화면은 HTTP 상태를 직접 보지 않는다(11장).

  | HTTP | AppErrorCode |
  |---|---|
  | 400 | `INVALID` |
  | 401 | `UNAUTHORIZED` (본문이 없을 수도 있다. Spring Security가 토큰 오류에 빈 본문으로 응답한다) |
  | 404 | `NOT_FOUND` |
  | 409 | `CONFLICT` |
  | 5xx, 502 | `UNKNOWN` |
  | 응답 없음, 타임아웃 | `NETWORK` |

- **인증 토큰:** 액세스 토큰(30분 JWT)은 메모리에, 리프레시 토큰은 `expo-secure-store`에 둔다. 401을 받으면 `/api/v1/auth/refresh`로 한 번 재발급하고 원래 요청을 한 번 다시 보낸다. 재발급도 실패하면 로그아웃한다.
- **재발급은 한 번에 하나만:** 백엔드 리프레시 토큰은 한 번 쓰면 사라진다. 요청 여러 개가 동시에 401을 받아도 재발급 요청은 하나만 보내고, 나머지는 그 결과를 기다린다. 동시에 보내면 첫 요청만 성공하고 나머지는 로그아웃된다.
- **결제:** 토스 결제 화면은 결제 SDK 포트(7-5) 뒤에 둔다. RN 결제위젯 SDK와 웹뷰 결제 페이지(ADR-002 대체안)는 같은 포트의 두 어댑터다. 시크릿 키는 앱에 두지 않고, 앱은 `api.tosspayments.com`을 직접 부르지 않는다. 결제 승인은 백엔드 `/api/v1/payments/confirm`이 한다.

## pstack과 함께 쓰기

작업 흐름은 pstack(`poteto-mode`, architect, tdd, 리뷰 등)을 따른다. 이 스킬은 그 흐름 안에서 앱 코드를 어디에 어떤 모양으로 둘지 정할 때 참고하는 규칙집이다. architect가 "변경이 닿는 시스템"을 추적할 때 이 문서를 함께 읽고, 두 가지 모양을 그릴 때도 둘 다 이 규칙 안에서 그린다.

pstack에 맡기는 것:

- **TypeScript 세부 규칙:** pstack `typescript-best-practices`를 먼저 따른다. 5장은 거기에 없는 보충 규칙만 담는다.
- **주석:** pstack `no-comments` 기준을 따른다(외부 플랫폼·라이브러리 제약, 공개 API 계약, 라이선스만 남긴다).
- **나머지 원칙:** 최소 diff, 경계 검증, 판별 유니온, 결과로 증명하기 등은 pstack 그대로다.

pstack 원칙을 덮어쓰는 예외는 두 가지뿐이다.

1. **의도한 경계는 합치지 않는다.** 7-5의 포트(원격 API, 저장소, 네이티브 기능, 결제 SDK, 시간)와 그 어댑터, `core/di`의 composition root는 실제 구현이 하나뿐이어도 Minimize Reader Load나 Laziness Protocol의 인라인 대상이 아니다. 테스트의 페이크가 두 번째 구현이고, 네이티브 모듈을 직접 모킹하지 않으려고 둔 경계다. 그 밖의 전달만 하는 래퍼에는 pstack 원칙을 적용한다.
2. **컨벤션을 바꾸는 재설계는 제안만 한다.** architect나 Redesign from First Principles가 7-3 폴더 구조나 7-2 레이어 자체를 바꾸는 모양을 고르면 구현하지 않는다. 이유와 두 모양을 정리해 type:decision Issue로 넘기고, 이번 작업은 현재 구조 안에서 진행한다.

domain과 use case를 바꾸면 단위 테스트를 같이 작성하는 규칙([references/testing.md](references/testing.md))은 pstack `tdd`(테스트를 먼저 쓸지)와 별개로 유지한다.

## 0. 적용 원칙

- **프로젝트에 이미 정한 규칙이 있으면 그것을 우선한다.** 이 문서는 정해지지 않은 부분의 기본값이다. 충돌하면 프로젝트 규칙을 따르고 차이를 알린다.
- Expo(Expo Router)와 bare RN(React Navigation) 모두에 적용된다. 둘이 다른 곳은 따로 적었다.
- **범위 밖:** 색상, 타이포, 간격, 애니메이션 같은 디자인·스타일 규칙.
- 리팩터링으로 파일을 옮기거나 지우면 결과 보고에 목록으로 적는다. git에 커밋되지 않은 파일을 지울 때는 되돌릴 수 없다는 점을 먼저 알린다.

### 작업별로 볼 섹션

| 작업 | 볼 섹션 |
|---|---|
| 이름 정하기 | 1. 네이밍 |
| 새 컴포넌트·화면 | 1, 2 |
| 유틸·헬퍼 함수 | 4. 헬퍼 함수 |
| 타입 정의 | 5. TypeScript |
| 폴더 구조·레이어 결정 | 7. 아키텍처 |
| 백엔드 API 호출, 에러, 토큰, 결제 | 백엔드 연동 |
| pstack 워크플로 안에서 쓸 때 | pstack과 함께 쓰기 |
| iOS/Android 분기 | 8. 플랫폼별 코드 |
| 목록이 느림, 버벅임 | 10. 성능 ([references/performance.md](references/performance.md)) |
| 코드 리뷰 | 3, 6, 13 체크리스트 |

---

## 1. 네이밍

### 1-1. 요약표

| 대상 | 규칙 | 예시 |
|---|---|---|
| 컴포넌트 | PascalCase | `UserProfile` |
| 컴포넌트 파일 | PascalCase, 컴포넌트명과 동일 | `UserProfile.tsx` |
| 화면 컴포넌트 | `~Screen` 접미사 | `ProfileScreen` |
| 내비게이터 컴포넌트 | `~Navigator` 접미사 | `MainTabNavigator` |
| 훅 | camelCase, `use` 접두사 | `useUser.ts` |
| 기능·도메인 폴더 | kebab-case | `user-profile/`, `order-history/` |
| 복합 컴포넌트 폴더 | PascalCase (공개 컴포넌트 1개 + 비공개 하위) | `UserProfile/` |
| 함수형 유틸 파일 | kebab-case | `format-date.ts` |
| 유틸 클래스·서비스 | PascalCase | `DateFormatter.ts` |
| 타입·인터페이스 | PascalCase | `User`, `UserRole` |
| 도메인 엔티티·값 객체 | PascalCase, 파일명 = 타입명 | `domain/entities/Order.ts` |
| 포트(인터페이스) | `~Port` 또는 `~Repository` | `LocationPort`, `UserRepository` |
| 어댑터 | `<구현방식><포트명>` | `ExpoLocationAdapter`, `HttpUserRepository` |
| use case | PascalCase + `UseCase`, 또는 동사형 함수 | `PlaceOrderUseCase`, `placeOrder` |
| 상수 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| 플랫폼별 파일 | `.ios.tsx` / `.android.tsx` | `DatePicker.ios.tsx` |
| testID | kebab-case, `<화면>-<요소>` | `login-submit-button` |

### 1-2. 라우트 파일 (Expo Router)

- Expo Router의 `app/` 아래 파일명은 URL 경로이므로 **kebab-case**로 쓴다: `order-history.tsx`.
- 동적 세그먼트는 `[camelCase]`: `[userId].tsx`.
- 라우트 그룹은 괄호: `(auth)/`, `(tabs)/`.
- 라우트 파일은 default export가 필수다. 이것만 named export 규칙의 예외다.

### 1-3. 복합 컴포넌트 폴더

```txt
user-profile/
  UserProfile/
    UserProfile.tsx      # 공개 컴포넌트
    UserAvatar.tsx       # 비공개 하위 컴포넌트
    index.ts             # 공개 컴포넌트만 export
```

- PascalCase 폴더는 **공개 컴포넌트 하나**를 나타낸다.
- `index.ts`는 공개 컴포넌트만 명시적으로 export한다. 하위 컴포넌트는 내부 구현이다.

### 1-4. 접두사 규칙

| 접두사 | 용도 | 예시 |
|---|---|---|
| `use` | 훅 | `useAuth` |
| `is` / `has` / `can` / `should` | 불리언 | `isLoading`, `canSubmit` |
| `get` | 동기 조회 | `getUserById` |
| `fetch` | 비동기 원격 조회 | `fetchUsers` |
| `handle` | 컴포넌트 안의 이벤트 처리 함수 | `handlePress` |
| `on` | 이벤트 콜백 props | `onPress`, `onSubmit` |
| `render` | JSX 반환 함수 (`renderItem` 등) | `renderUserItem` |
| `create` | 팩토리 | `createOrder` |
| `validate` / `format` / `parse` | 검증·포맷·파싱 | `validateEmail`, `formatPrice` |

### 1-5. 원칙

- 이름은 **의도**를 드러낸다. 구현 방식이 아니다.
- 도메인 용어는 **유비쿼터스 언어**로 통일한다. 백엔드·기획과 같은 단어를 쓰고, 한 개념에 이름을 여러 개 붙이지 않는다.
- 파일명, 폴더명, export 심볼이 **같은 이야기**를 해야 한다.
- 의미 없는 이름 금지: `data`, `info`, `temp`, `utils.ts`, `helpers.ts`, `common.ts`.

---

## 2. 컴포넌트 구조

### 2-1. function 선언을 쓴다

```tsx
// ❌ Don't
const UserProfile: React.FC<Props> = ({ name }) => <Text>{name}</Text>;

// ✅ Do
interface UserProfileProps {
  name: string;
  email: string;
}

export function UserProfile({ name, email }: UserProfileProps) {
  return (
    <View>
      <Text>{name}</Text>
      <Text>{email}</Text>
    </View>
  );
}
```

이유: 에러 스택에 이름이 잘 보이고, 호이스팅되며, `React.FC`의 암묵적 `children`과 제네릭 문제를 피한다.

- props 타입은 `<컴포넌트명>Props`로 짓는다.
- 파일 하나에 export하는 컴포넌트는 하나다.
- named export를 쓴다 (라우트 파일 예외).

### 2-2. 단일 책임

- 컴포넌트는 한 가지 일만 한다. 설명하는 데 "그리고"가 들어가면 나눈다.
- **화면(Screen)은 조립만** 한다: 데이터 훅 호출, 하위 컴포넌트 배치, 내비게이션 연결.
- 표시 컴포넌트는 props만 받아 그린다. 데이터 패칭, 네이티브 API 호출을 하지 않는다.
- 로딩·에러·빈 상태를 항상 처리한다.

```tsx
// ❌ Don't: 패칭, 가공, 표시, 내비게이션이 한 컴포넌트에
export function OrderListScreen() {
  const [orders, setOrders] = useState<Order[]>([]);
  useEffect(() => {
    fetch('/orders').then((r) => r.json()).then(setOrders);
  }, []);
  // ...200줄
}

// ✅ Do: 화면은 조립, 데이터는 훅, 표시는 하위 컴포넌트
export function OrderListScreen() {
  const { orders, isLoading, error } = useOrders();
  if (isLoading) {
    return <LoadingView />;
  }
  if (error) {
    return <ErrorView error={error} />;
  }
  return <OrderList orders={orders} onSelect={handleSelect} />;
}
```

### 2-3. 라우트·내비게이션 파일은 얇게

```tsx
// app/users/[userId].tsx (Expo Router)
export default function UserDetailRoute() {
  const { userId } = useLocalSearchParams<{ userId: string }>();
  return <UserDetailScreen userId={userId} />;
}
```

- 라우트 파일에는 파라미터 읽기, 화면 렌더링, 라우트 가드만 둔다.
- React Navigation이면 내비게이터 정의 파일에 화면 등록만 두고, 로직은 화면 컴포넌트로.
- 내비게이션 파라미터는 타입으로 정의한다 (`RootStackParamList` 등).

### 2-4. 헬퍼 함수 위치

**컴포넌트 파일에 둔다 (컴포넌트 아래쪽에):**
- 이 컴포넌트에서만 쓰고, 1~5줄이며, 단순 포맷·변환이다.

**별도 파일로 뺀다:**
- 2개 이상 컴포넌트에서 쓴다.
- 10줄이 넘는다.
- 비즈니스 규칙이다 → `domain/`
- 따로 테스트해야 한다.

컴포넌트 위에 헬퍼를 여러 개 쌓지 않는다. 파일을 열면 컴포넌트가 먼저 보여야 한다.

### 2-5. 파일 내부 순서

1. import
2. props 타입
3. export 컴포넌트
4. 비공개 하위 컴포넌트
5. 짧은 헬퍼 함수
6. `StyleSheet.create` (스타일 값 규칙은 이 문서 범위 밖)

### 2-6. RN 컴포넌트 규칙

- 누를 수 있는 요소는 `Pressable`을 기본으로 쓴다.
- 텍스트는 반드시 `<Text>` 안에 둔다. `View` 안에 문자열을 직접 넣지 않는다.
- 조건부 렌더링에 숫자를 `&&`로 쓰지 않는다. `0`이 그대로 렌더링되어 크래시가 난다.

```tsx
// ❌ count가 0이면 "0"이 View에 그려져 에러
{count && <Badge count={count} />}

// ✅
{count > 0 && <Badge count={count} />}
```

- 렌더 중에 무거운 계산이나 부수 효과를 넣지 않는다.
- E2E 테스트 대상 요소에는 `testID`를 붙인다.
- 동작이 정해지지 않은 요소는 누를 수 있게 만들지 않는다. 핸들러(`onPress`)를 선택 prop으로 두고, 없으면 `Pressable` 대신 일반 `View`로 렌더링한다. 버튼처럼 보이는데 아무 일도 안 하면 사용자와 스크린리더 모두 혼란스럽다.

---

## 3. 일반 코드 규칙

### 3-1. 함수 설계

- 화살표 함수보다 **이름 있는 function 선언**을 선호한다 (콜백 인라인은 예외).
- 함수 이름은 **동작(동사)** 으로: `calculateTotal`, `sendInvite`.
- 파라미터는 3개 이하. 넘으면 객체 하나로 받는다.
- **플래그 파라미터 금지.** 분기마다 함수를 나눈다. 여기서 플래그는 함수의 동작을 바꾸는 boolean 인자를 말한다. pstack Laziness Protocol의 "결정을 한 곳에서 내리고 결과를 단순한 값으로 넘긴다"는 계산된 결과 값을 넘기는 것이라 이 규칙과 부딪히지 않는다.

```ts
// ❌ Don't
function saveUser(user: User, isDraft: boolean) {}

// ✅ Do
function saveUser(user: User) {}
function saveUserDraft(user: User) {}
```

### 3-2. 명령-조회 분리 (CQS)

- 값을 돌려주는 함수는 상태를 바꾸지 않는다. 상태를 바꾸는 함수는 값을 돌려주지 않는다.

### 3-3. 제어 흐름

- **early return**으로 중첩을 없앤다. 중첩은 2단계까지.
- return 뒤의 `else`는 쓰지 않는다.
- 제어문은 한 줄이어도 **항상 중괄호**를 쓴다.

```ts
// ❌ Don't
if (!user) return null;

// ✅ Do
if (!user) {
  return null;
}
```

### 3-4. 크기와 범위

- 함수는 5~20줄을 목표로 한다.
- 변수는 쓰는 곳 가까이, 가장 좁은 범위에 선언한다.
- 한 줄에 변수 하나만 선언한다.
- 함수 안에 빈 줄을 넣지 않는다. 빈 줄이 필요할 만큼 길면 함수를 나눈다.

### 3-5. 매직 넘버와 주석

- 매직 넘버는 이름 있는 상수로 뺀다: `const MAX_UPLOAD_MB = 10;`
- 주석은 pstack `no-comments` 기준을 따른다. 무엇을 하는지는 이름으로 드러내고, 주석은 우리가 바꿀 수 없는 외부 제약(플랫폼, 라이브러리, 프로토콜)이나 공개 API 계약에만 쓴다.
- `console.log`를 커밋하지 않는다. 디버깅용 로그는 지우고, 남겨야 할 로그는 로거를 거친다. 운영 빌드에 그대로 남는다.

```ts
// ❌ 사용자의 전체 이름을 만든다
const fullName = `${user.firstName} ${user.lastName}`;

// ✅ Android 12 이하에서 이 API가 null을 반환하는 경우가 있다
const items = response.items ?? [];
```

### 3-6. Clean Code

- **의미 있는 이름:** 이름만 보고 역할을 알 수 있어야 한다.
- **한 가지 일:** 함수·컴포넌트·훅 모두.
- **에러 코드보다 예외:** 실패는 `throw`하거나 타입이 있는 결과(`Result`)로 돌려준다. `-1`, `null`로 실패를 숨기지 않는다.
- **DRY:** 같은 로직이 세 번 나오면 뺀다. 두 번은 지켜본다.
- **부수 효과 피하기:** 이름에 드러나지 않는 상태 변경을 하지 않는다.
- 여러 OR 조건은 배열로 모아 읽기 쉽게:

```ts
const hasAnyError = [emailError, passwordError, nameError].some(Boolean);
```

---

## 4. 헬퍼 함수

### 4-1. 종류

| 종류 | 역할 | 예시 | 위치 |
|---|---|---|---|
| Formatter | 표시용 변환 | `formatPrice`, `formatDate` | `shared/lib/` |
| Validator | 입력 검증 | `isValidEmail` | 비즈니스 규칙이면 `domain/` |
| Parser | 형식 변환 | `parseISODate` | `shared/lib/` |
| Calculator | 비즈니스 계산 | `calculateDiscount` | `domain/` |
| Guard | 타입 좁히기 | `isDefined`, `isAppError` | `shared/lib/` |

### 4-2. 규칙

- **순수 함수**로 만든다. 같은 입력에 같은 출력, 외부 상태 변경 없음.
- 이름은 동작으로, 시그니처는 단순하게.
- 헬퍼는 React·RN을 import하지 않는다. 그래야 어디서나 쓰고 쉽게 테스트한다.
- 날짜·숫자·통화 포맷은 **한 함수로만** 한다. 화면마다 따로 포맷하지 않는다.

### 4-3. 구성

- 작은 앱: `shared/lib/` 아래 평평하게.
- 중간 이상: 종류별 폴더(`formatters/`, `validators/`)에 각각 `index.ts` 배럴.
- 새 유틸을 만들면 배럴 `index.ts`에 export를 추가한다. 깊은 경로로 import하지 않는다.

### 4-4. 안티패턴

- ❌ `utils.ts` 하나에 수백 줄 몰아넣기
- ❌ 감싸는 의미가 없는 한 줄짜리 헬퍼 (`const isEmpty = (a) => a.length === 0` 를 굳이)
- ❌ 포맷과 비즈니스 계산을 한 함수에 섞기

---

## 5. TypeScript

TypeScript 규칙은 pstack `typescript-best-practices`(판별 유니온, 브랜드 타입, `unknown`, `as` 금지, `satisfies`, 경계에서 파싱, 스키마에서 타입 추론, 객체 인자 등)를 먼저 따른다. 아래는 거기에 없는 보충 규칙이다.

- `tsconfig`는 `strict: true`로 둔다.
- RN에서 신뢰하지 않는 입력: 서버 응답, `JSON.parse`, **딥링크·라우트 파라미터**, **저장소(SecureStore·AsyncStorage)에서 읽은 값**. 모두 경계에서 검증한다.
- export하는 함수, 포트(인터페이스), 공개 훅은 반환 타입을 명시한다. 내부 함수는 추론에 맡긴다.
- 객체 모양은 `interface`, 유니온·튜플·원시 타입 별칭·매핑 타입은 `type`으로 쓴다.
- `enum` 대신 문자열 리터럴 유니온을 쓴다: `type OrderStatus = 'pending' | 'paid' | 'cancelled'`.
- `null | undefined`는 `Nullable<T>`로 통일한다.

```ts
type Nullable<T> = T | null | undefined;
```

- 서버 DTO와 도메인 타입을 분리하고, 변환은 어댑터(infrastructure)에서 한다.
- API 스펙(OpenAPI 등)이 있으면 타입을 생성해서 쓴다. 손으로 쓰지 않는다.

---

## 6. SOLID (RN 관점)

| 원칙 | RN에서 이렇게 적용 |
|---|---|
| **S** 단일 책임 | 화면은 조립, 훅은 데이터·상태, 표시 컴포넌트는 그리기, 어댑터는 외부 연동 |
| **O** 개방-폐쇄 | 변형은 props·컴포지션으로 확장한다. 컴포넌트 안에 `if (type === ...)` 분기를 계속 추가하지 않는다 |
| **L** 리스코프 치환 | 같은 포트의 어댑터는 서로 바꿔 끼워도 동작해야 한다 (실제 ↔ 페이크, iOS ↔ Android) |
| **I** 인터페이스 분리 | 거대한 `NativeService` 대신 `LocationPort`, `CameraPort`, `PushPort`로 나눈다. 컴포넌트 props도 필요한 것만 받는다 |
| **D** 의존성 역전 | 도메인·use case는 네이티브 모듈이 아니라 포트에 의존한다. 구현은 composition root에서 주입한다 |

```ts
// ❌ use case가 네이티브 모듈에 직접 의존
import * as Location from 'expo-location';

export async function findNearbyStores() {
  const pos = await Location.getCurrentPositionAsync();
  // ...
}

// ✅ 포트에 의존
export interface LocationPort {
  getCurrentPosition(): Promise<Coordinates>;
}

export async function findNearbyStores(deps: { location: LocationPort; stores: StoreRepository }) {
  const position = await deps.location.getCurrentPosition();
  return deps.stores.findNear(position);
}
```

SOLID는 복잡도가 생긴 곳에 적용한다. 단순한 화면에 추상화를 미리 만들지 않는다.

---

## 7. 아키텍처: Clean Architecture + DDD + 포트/어댑터

### 7-1. 핵심 규칙

**의존성은 항상 안쪽(domain)으로.** 안쪽 레이어는 바깥 레이어를 모른다.

```
presentation(화면·컴포넌트·훅) ──▶ application(use case, 포트 정의) ──▶ domain(엔티티·규칙)
                                              ▲
infrastructure(API·저장소·네이티브 모듈 어댑터) ─┘ (포트를 구현)
```

### 7-2. 레이어

| 레이어 | 역할 | 의존 가능 | 금지 |
|---|---|---|---|
| **domain** | 엔티티, 값 객체, 비즈니스 규칙, 도메인 에러 | 없음 | React, RN, Expo, 네이티브 모듈, HTTP, 저장소 |
| **application** | use case, 포트(인터페이스) 정의 | domain | React, RN, 구체 구현 |
| **infrastructure** | 포트 구현(어댑터), DTO ↔ 도메인 변환 | application, domain | 화면 상태, 비즈니스 판단 |
| **presentation** | 화면, 컴포넌트, 훅, 내비게이션 | application, domain | 네이티브 모듈·HTTP 직접 호출 |

### 7-3. 폴더 구조: 기능 우선 + 기능 안의 레이어

```
src/
├── app/                      # Expo Router 라우트 (bare RN이면 navigation/)
├── features/
│   └── <feature-name>/
│       ├── presentation/
│       │   ├── screens/
│       │   ├── components/
│       │   └── hooks/
│       ├── application/
│       │   ├── ports/
│       │   └── use-cases/
│       ├── domain/
│       │   ├── entities/
│       │   └── value-objects/
│       ├── infrastructure/
│       │   ├── adapters/
│       │   └── mappers/
│       └── index.ts          # 기능의 공개 API
├── core/                     # 앱 전역 기반 (비즈니스 규칙 없음)
│   ├── di/                   # composition root
│   ├── http/                 # HTTP 클라이언트, 인증, 에러 변환
│   ├── storage/              # 저장소 포트·어댑터
│   └── errors/
└── shared/                   # 기능 공통 순수 UI·유틸
    ├── ui/
    └── lib/
```

- 기능 밖에서는 `features/<name>/index.ts`로만 가져온다. 다른 기능의 내부 파일을 직접 import하지 않는다.
- 쓰지 않는 레이어 폴더는 만들지 않는다. 조회 위주 기능은 presentation + infrastructure + domain만으로 충분하다.
- `shared/`에는 비즈니스 의미가 없는 것만 둔다. 의미가 생기면 해당 기능의 domain으로 옮긴다.

### 7-4. use case를 만드는 기준

다음 중 하나에 해당할 때만 만든다. 아니면 훅에서 어댑터를 바로 쓴다.

- 포트 두 개 이상을 순서대로 조합한다.
- 구현을 바꿔 끼울 수 있어야 한다.
- 성공·실패·취소·재시도 분기가 있어 테스트로 고정해야 한다.

### 7-5. 포트/어댑터를 쓰는 곳

**바뀔 수 있거나, 테스트에서 가짜로 바꿔야 하는 외부 의존성**에 쓴다.

- 원격 API (`UserRepository` ← `HttpUserRepository`)
- 저장소 (`TokenStoragePort` ← `SecureStoreTokenAdapter`)
- 네이티브 기능: 위치, 카메라, 푸시, 생체 인증, 결제 SDK, 분석 SDK
- 시간·ID 생성 (`ClockPort`): 시간에 따라 동작이 바뀌는 로직을 테스트할 때

### 7-6. DDD 전술 패턴 (앱에서는 가볍게)

- **엔티티·값 객체:** 클래스 또는 `type` + 순수 함수 둘 다 허용한다. 프로젝트에서 하나로 통일한다.
- **값 객체**는 생성 시 검증하고 불변으로 둔다.

```ts
export class EmailAddress {
  private constructor(private readonly value: string) {}

  static create(raw: string): EmailAddress {
    if (!EMAIL_PATTERN.test(raw)) {
      throw new InvalidEmailError(raw);
    }
    return new EmailAddress(raw.toLowerCase());
  }

  toString() {
    return this.value;
  }
}
```

- **애그리거트·도메인 서비스**는 앱이 그 규칙의 원본일 때만 만든다 (오프라인 우선 앱, 로컬 계산이 핵심인 앱). 서버가 규칙의 원본이면 앱에서 다시 구현하지 않는다. 앱은 입력 검증과 표시용 계산만 한다.

### 7-7. Composition Root

- 어댑터 생성과 주입은 **한 곳**(`core/di/`)에서만 한다.
- 앱 루트(`App.tsx` 또는 `app/_layout.tsx`)에서 Provider나 Context로 화면에 전달한다.
- 환경(개발·테스트·운영)에 따라 어댑터를 바꾸는 것도 여기서만 한다.

```ts
// core/di/container.ts
export function createContainer(env: AppEnv) {
  const http = createHttpClient(env.apiBaseUrl);
  return {
    userRepository: new HttpUserRepository(http),
    location: new ExpoLocationAdapter(),
    tokenStorage: new SecureStoreTokenAdapter(),
  };
}
```

---

## 8. 플랫폼별 코드

- 플랫폼 분기는 **presentation 또는 infrastructure에만** 둔다. domain과 application은 플랫폼을 모른다.
- 차이가 작으면 `Platform.select` / `Platform.OS`.
- 컴포넌트·어댑터 전체가 다르면 플랫폼별 파일로 나누고, 두 파일의 export 시그니처를 같게 맞춘다.

```txt
DatePicker.ios.tsx
DatePicker.android.tsx
```

- 같은 기능이 플랫폼마다 다른 네이티브 API를 쓰면, 포트 하나에 플랫폼별 어댑터를 둔다.
- 플랫폼 분기가 여러 파일에 흩어지면 한 어댑터로 모은다.

---

## 9. 상태와 데이터

- **서버 상태와 클라이언트 상태를 분리한다.**
  - 서버 상태(원격 데이터): 서버 상태 라이브러리(TanStack Query, SWR, RTK Query 등)에 둔다. 전역 스토어에 복사하지 않는다.
  - 클라이언트 상태: `useState`를 기본으로, 정말 전역인 것(인증 세션, 설정)만 전역 스토어에.
- 서버 상태 캐시 키는 기능마다 팩토리 하나로 관리한다.

```ts
export const userKeys = {
  all: ['user'] as const,
  detail: (id: string) => [...userKeys.all, 'detail', id] as const,
};
```

- 데이터를 바꾸는 작업 뒤에는 관련 캐시를 무효화한다.
- 서버 상태 라이브러리가 지원하면 **앱이 다시 포그라운드로 올 때와 네트워크가 다시 연결될 때 재조회**되도록 연결한다. RN에서는 웹처럼 자동으로 되지 않는다. TanStack Query는 `focusManager`를 `AppState`에, `onlineManager`를 NetInfo(`@react-native-community/netinfo`)에 앱 루트에서 연결한다.
- 긴 목록 화면에는 당겨서 새로고침(`refreshControl`)을 둔다.
- **민감 정보(토큰, 비밀번호)는 보안 저장소**(Keychain/Keystore 기반: `expo-secure-store`, `react-native-keychain`)에만 둔다. AsyncStorage에 두지 않는다.
- 비밀 키를 앱 번들에 넣지 않는다. 번들은 추출될 수 있다.

---

## 10. 성능

목록 가상화, 렌더링과 JS 스레드, JS 일반 규칙, 이미지·구독 리소스 관리는 [references/performance.md](references/performance.md)를 봅니다.

---

## 11. 에러 처리

- HTTP·네이티브 에러는 어댑터에서 **앱 에러 타입**으로 바꾼다. 화면은 HTTP 상태 코드나 네이티브 에러 코드를 직접 보지 않는다.

```ts
export type AppErrorCode = 'INVALID' | 'UNAUTHORIZED' | 'NOT_FOUND' | 'CONFLICT' | 'NETWORK' | 'PERMISSION_DENIED' | 'UNKNOWN';

export class AppError extends Error {
  constructor(
    public readonly code: AppErrorCode,
    message: string,
    public readonly serverCode?: string, // 백엔드 ErrorResponse.code (예: AMOUNT_MISMATCH)
    public readonly cause?: unknown,
  ) {
    super(message);
  }
}
```

- 사용자 메시지는 에러 코드별로 한 곳에서 정한다.
- 네트워크 없음, 권한 거부(위치·카메라·알림)는 **정상 흐름의 일부**로 화면에서 처리한다.
- 화면 단위로 Error Boundary를 둔다. 한 화면의 렌더 에러가 앱 전체를 멈추지 않게 한다.
- **이미 받은 데이터가 있으면 백그라운드 재조회 에러로 화면을 에러 화면으로 바꾸지 않는다.** 데이터는 그대로 보여 주고, 에러는 배너나 토스트로 알린다. 전체 에러 화면은 보여 줄 데이터가 없을 때만 쓴다.
- 재시도 중에는 로딩을 표시한다. 라이브러리마다 "처음 로딩"과 "재조회 중" 상태가 다르다(TanStack Query v5는 재시도 중 `isPending`이 아니라 `isFetching`이 `true`). 재시도 버튼을 눌러도 화면이 그대로면 사용자는 고장으로 안다.
- 빈 `catch {}` 금지. 에러를 삼키지 않는다.

---

## 12. 테스트

테스트 도구, 언제 테스트를 작성하는지, 작성 방법은 [references/testing.md](references/testing.md)를 봅니다.

---

## 13. 자동 검사

`tsc`, ESLint 규칙, 레이어 경계 검사 설정은 [references/automation.md](references/automation.md)를 봅니다.

---

## 14. 체크리스트

**코드를 쓰기 전**
- [ ] 어느 기능에 속하는지 정했다
- [ ] 어느 레이어에 둘지 7-2 표로 확인했다
- [ ] use case·포트가 필요한지 7-4, 7-5 기준으로 판단했다
- [ ] 도메인 용어를 팀·백엔드와 같게 썼다

**리뷰할 때**
- [ ] 네이밍이 1장 규칙을 따른다
- [ ] 컴포넌트가 function 선언이고 `React.FC`를 쓰지 않는다
- [ ] 화면은 조립만 하고, 표시 컴포넌트는 패칭·네이티브 호출을 하지 않는다
- [ ] 라우트·내비게이션 파일에 로직이 없다
- [ ] domain에 외부 import가 없다
- [ ] 다른 기능은 `index.ts`로만 가져왔다
- [ ] 플랫폼 분기가 domain·application에 없다
- [ ] 서버 데이터를 전역 스토어에 복사하지 않았다
- [ ] 민감 정보를 AsyncStorage나 번들에 두지 않았다
- [ ] 로딩·에러·빈 상태, 권한 거부, 오프라인을 처리했다
- [ ] 긴 목록이 가상화 목록이고 key가 안정적이다
- [ ] 구독·타이머를 cleanup에서 해제했다
- [ ] `any`, 빈 `catch`, 매직 넘버, 중괄호 없는 if가 없다
- [ ] domain·use case를 바꿨다면 단위 테스트를 같이 작성했다 (테스트 환경이 없으면 그 사실과 대상을 보고했다)
- [ ] 동작 없는 버튼과 `console.log`가 없다
- [ ] 데이터가 있을 때 재조회 에러로 화면을 지우지 않고, 재시도 중 로딩을 표시한다
- [ ] domain·use case를 바꿨다면 단위 테스트를 같이 작성했다 (테스트 환경이 없으면 그 사실과 대상을 보고했다)
- [ ] 파일을 옮기거나 지웠다면 보고에 목록으로 적었다
- [ ] `tsc`, ESLint, 테스트가 통과한다

---

## 원본에서 바꾼 것

| 원본 | 이 스킬 |
|---|---|
| DOM·브라우저 성능 (layout thrashing) | RN 목록 가상화, JS/UI 스레드, 애니메이션 |
| localStorage·쿠키 캐싱 | AsyncStorage·MMKV 읽기 캐싱, 보안 저장소 규칙 |
| `<div>`, `<form>`, `<input>` 예제 | `View`, `Text`, `Pressable` 예제 |
| 브라우저 지원 fallback | 삭제 |
| 일반 Clean Architecture 예제 | 네이티브 모듈·SDK를 포트로 감싸는 예제 |
| — | 추가: 라우트·내비게이션 규칙, 플랫폼별 코드, 서버/클라이언트 상태 분리, 에러·권한·오프라인 처리, 테스트, ESLint 레이어 검사, 체크리스트 |
| 엔티티는 클래스 | 클래스 또는 `type` + 순수 함수 중 프로젝트에서 통일 |