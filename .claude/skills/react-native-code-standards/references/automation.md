# 자동 검사

규칙은 사람이 아니라 도구가 먼저 잡게 한다.

- `tsc --noEmit` (strict)
- ESLint: `@typescript-eslint/no-explicit-any`, `curly`, `no-console`, `import/order`, `react-hooks/rules-of-hooks`, `react-hooks/exhaustive-deps`
- 레이어 경계: `eslint-plugin-boundaries` 또는 `import/no-restricted-paths`

```js
'import/no-restricted-paths': ['error', {
  zones: [
    // domain은 다른 레이어를 모른다
    { target: './src/features/*/domain', from: './src/features/*/(presentation|application|infrastructure)' },
    // application은 presentation·infrastructure를 모른다
    { target: './src/features/*/application', from: './src/features/*/(presentation|infrastructure)' },
    // presentation은 infrastructure를 직접 쓰지 않는다
    { target: './src/features/*/presentation', from: './src/features/*/infrastructure' },
  ],
}],
```

- domain에서 `react`, `react-native`, `expo-*` import를 금지하는 규칙(`no-restricted-imports`)도 함께 둔다.
