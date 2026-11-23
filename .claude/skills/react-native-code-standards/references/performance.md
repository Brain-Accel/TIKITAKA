# 성능

## 10-1. 목록

- 긴 목록은 `FlatList`, `SectionList`, 또는 `FlashList`를 쓴다. `ScrollView` + `map`은 짧고 고정된 목록에만.
- `keyExtractor`는 안정적인 고유 ID를 쓴다. 인덱스를 key로 쓰지 않는다.
- `renderItem`의 항목 컴포넌트는 가볍게 두고, 목록이 버벅일 때 `memo`로 감싼다.

## 10-2. 렌더링과 JS 스레드

- 렌더 중에 무거운 계산을 하지 않는다. 필요하면 `useMemo`나 데이터 변환 단계(어댑터·셀렉터)로 옮긴다.
- `useMemo`, `useCallback`, `memo`는 **측정해서 문제가 보일 때** 쓴다. 습관적으로 감싸지 않는다.
- 화면 전환 직후의 무거운 작업은 전환이 끝난 뒤로 미룬다.
- 애니메이션은 JS 스레드가 아니라 UI 스레드에서 돌게 한다 (Reanimated, `useNativeDriver`).

## 10-3. JS 일반 (원본 규칙 유지)

- **반복 조회는 Map/Set으로:** 루프 안의 `array.find` / `includes` 대신 인덱스 Map, Set.
- **배열 순회 합치기:** `filter().map().filter()`가 큰 배열에서 반복되면 한 번의 순회로.
- **최솟값·최댓값은 정렬하지 않고** 한 번 순회로.
- **불변 배열 메서드:** `sort()` 대신 `toSorted()`, `reverse()` 대신 `toReversed()`. 상태 배열을 직접 바꾸면 리렌더가 안 된다.
- **정규식은 모듈 범위로 끌어올린다.** 함수 안에서 매번 만들지 않는다. 전역 플래그(`g`) 정규식은 상태가 있으니 공유하지 않는다.
- **저장소 읽기 캐시:** AsyncStorage·MMKV를 같은 값으로 반복 읽지 않는다. 메모리에 캐시하고, 쓸 때 무효화한다.

## 10-4. 리소스

- 이미지는 표시 크기에 맞는 해상도로 받고, 캐시를 지원하는 컴포넌트를 쓴다 (`expo-image`, `react-native-fast-image`).
- 구독·타이머·리스너는 `useEffect` cleanup에서 반드시 해제한다.
