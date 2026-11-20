# 🎫 TIKITAKA — 공연 티켓 커머스

공연 예매·결제·포인트·정산을 다루는 2인 풀스택 프로젝트입니다.
Claude Code로 개발을 자동화하고, CI/CD·테스트를 자동화하며, 장애 대응 환경을 직접 구축하는 것이 목표입니다.

## 목표

- **AI 기반 개발 자동화**: Claude Code Skills·Hooks로 설계부터 구현, 리뷰, 이슈 기록까지
- **CI/CD·테스트 자동화**: GitHub Actions, Argo CD GitOps, Kotest, 계약 테스트, Maestro E2E, k6 스모크
- **장애 대응 환경**: Prometheus/Loki/Alertmanager → n8n → GitHub Incident Issue와 Discord → Claude Code 분석

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| Backend | Kotlin 2.3, Spring Boot 4.1, JDK 25, JPA, MySQL(RDS), Redis |
| 비동기·정합성 | Outbox + 폴링 워커, 복식부기 포인트 원장, 일일 대사 |
| 결제·데이터 | 토스페이먼츠(RN SDK, 실패 시 WebView 대체), KOPIS 공연 API |
| App | React Native(Expo), EAS Build, NativeWind, TanStack Query |
| Infra | k3s(EC2 단일 노드), Helm, Argo CD, Sealed Secrets, GHCR, Traefik |
| 관측·운영 | Prometheus, Grafana, Loki, Alertmanager, n8n |
| AI 협업 | Claude Code(Skills 7종, Hooks), claude-code-action, SwarmCode |

## 역할

- **A**: 서비스 백엔드(인증·카탈로그·주문·결제·포인트·정산)와 앱
- **B**: 플랫폼과 자동화(k3s·Helm·Argo CD, CI/CD, 관측, n8n, 장애 대응)

## 레포 구조

```
backend/        Kotlin Spring Boot API·정산 워커
app/            React Native(Expo) 앱
infra/          helm, argocd, values, sealed-secrets, observability, n8n
load-test/      k6 시나리오
docs/           ADR, 실험 기록, 장애 리포트
```

## 문서

| 문서 | 링크 |
| --- | --- |
| 마스터 플랜 | [열기](https://claude.ai/artifact/BeLz7eMMRjYvef8kAG3qtR) |
| 01 개발 환경과 연동 준비 | [열기](https://claude.ai/artifact/PPdfzW3TExScmWd8F7h1tA) |
| 02 프론트엔드와 오픈소스 활용 | [열기](https://claude.ai/artifact/A6f4oi14rG9U4xRAdXkTqw) |
| 03 기능 범위와 개발 명세 | [열기](https://claude.ai/artifact/JqZgFQ8t9RpCPhZAf6UfGk) |
| 04 주차별 실행 계획 | [열기](https://claude.ai/artifact/JnkALgifwKWdR3Njgb3eyf) |
| 05 GitHub 운영 규칙 | [열기](https://claude.ai/artifact/T8N2exV8dkvHcbtSvcBBKq) |
| 06 실험과 장애 훈련 명세 | [열기](https://claude.ai/artifact/FFTXxVFvdZuKEjw8JjN3dj) |
| 07 역할 분담 | [열기](https://claude.ai/artifact/9jVEhFWz2PT7FJP1a6Kd6f) |

## 일정

2026.11.09 ~ 2027.01.24 (10주). 자세한 내용은 [04 문서](https://claude.ai/artifact/JnkALgifwKWdR3Njgb3eyf)를 참고하세요.
