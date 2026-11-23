# 테스트

| 대상 | 도구 | 방법 |
|---|---|---|
| domain, 헬퍼 | Jest | 순수 함수 단위 테스트, 모든 분기 |
| use case | Jest | 페이크 어댑터 주입, 성공·실패·취소 |
| 훅 | React Native Testing Library `renderHook` | 페이크 포트를 Provider로 주입 |
| 컴포넌트·화면 | React Native Testing Library | 로딩·에러·빈 상태, 주요 상호작용 |
| 사용자 주요 흐름 | E2E (Maestro, Detox 등) | `testID` 기반 |

## 언제 테스트를 작성하나

- `domain/` 함수나 use case를 새로 만들거나 바꾸면, **같은 작업 안에서 단위 테스트를 함께 작성한다.** 요청에 테스트가 없어도 작성한다.
- 화면·컴포넌트 테스트는 요청이 있을 때만 작성한다.
- 테스트 실행 환경(Jest 등)이 설정돼 있지 않으면 **직접 설치하지 않는다.** 테스트 파일 작성도 미루고, 작업 결과 보고에 "테스트 환경이 없어 단위 테스트를 작성하지 못했다"와 작성해야 할 대상을 적는다.

## 작성 방법

## 언제 테스트를 작성하나

- `domain/` 함수나 use case를 새로 만들거나 바꾸면, **같은 작업 안에서 단위 테스트를 함께 작성한다.** 요청에 테스트가 없어도 작성한다.
- 화면·컴포넌트 테스트는 요청이 있을 때만 작성한다.
- 테스트 실행 환경(Jest 등)이 설정돼 있지 않으면 **직접 설치하지 않는다.** 테스트 파일 작성도 미루고, 작업 결과 보고에 "테스트 환경이 없어 단위 테스트를 작성하지 못했다"와 작성해야 할 대상을 적는다.

## 작성 방법

- 테스트 파일은 대상 옆에 `<파일명>.test.ts(x)`.
- 네이티브 모듈은 직접 모킹하지 말고 **포트의 페이크**를 쓴다. 포트 덕분에 모킹이 단순해진다.

```ts
class FakeLocationAdapter implements LocationPort {
  constructor(private readonly position: Coordinates) {}
  async getCurrentPosition() {
    return this.position;
  }
}
```

- RNTL에서는 구현 세부(state, 내부 함수)가 아니라 **사용자에게 보이는 것**(텍스트, 역할, 라벨)으로 찾는다.
- `testID`를 바꾸면 E2E 시나리오도 같은 변경에서 고친다.
