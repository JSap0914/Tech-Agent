# Tech Spec Agent - 시각적 요약

## 🎯 한눈에 보는 Tech Spec Agent

### 전체 플로우 (17개 노드)

```
🚀 시작 (디자인 완료)
    ↓
📥 1. 입력 로드 (PRD/디자인)
    ↓
🔍 2. 완전성 분석 (0-100점)
    ↓
   ❓ 점수 >= 80?
    ├─ No → 2-1. 사용자 질문 → 다시 분석
    └─ Yes ↓
    
🔎 3. 기술 Gap 탐지
    ↓
   ❓ Gap 있음?
    ├─ No → 8번으로 점프
    └─ Yes ↓
    
🌐 4. 오픈소스 웹 검색
    ↓
📊 5. 선택지 3개 제시
    ↓
⏳ 6. 사용자 선택 대기
    ↓
✅ 7. 선택 검증
    ↓
   ❓ 충돌 있음?
    ├─ Yes → 7-1. 경고 → 재선택 or 계속
    └─ No ↓
    
   ❓ 남은 결정 있음?
    ├─ Yes → 4번으로 (다음 Gap)
    └─ No ↓
    
💻 8. Google AI Studio 코드 파싱
    ↓
🔮 9. API 명세 추론
    ↓
📝 10. TRD 생성
    ↓
✔️ 11. TRD 검증 (품질 점수)
    ↓
   ❓ 유효? (점수 >= 90)
    ├─ No → 10번으로 (재생성, 최대 3회)
    └─ Yes ↓
    
📄 12. API 명세서 생성
    ↓
🗄️ 13. DB 스키마 생성
    ↓
🏗️ 14. 아키텍처 다이어그램 생성
    ↓
📚 15. 기술 스택 문서 생성
    ↓
💾 16. DB 저장
    ↓
🔔 17. 백로그 Agent 트리거
    ↓
✨ 완료 (백로그 단계로)
```

---

## 🎨 4단계 Phase 구조

```
┌──────────────────────────────────────────────────┐
│ Phase 1: 입력 및 분석 (완료율: 0% → 25%)        │
├──────────────────────────────────────────────────┤
│ 노드 1-3                                         │
│ • PRD/디자인 로드                                │
│ • 완전성 평가                                    │
│ • 기술 Gap 식별                                  │
└──────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────┐
│ Phase 2: 기술 조사 및 선택 (완료율: 25% → 50%) │
├──────────────────────────────────────────────────┤
│ 노드 4-7                                         │
│ • 웹 검색으로 오픈소스 조사                      │
│ • 3가지 옵션 제시                                │
│ • 사용자 선택 & 검증                             │
│ • 반복 (모든 Gap 해결까지)                      │
└──────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────┐
│ Phase 3: 코드 분석 (완료율: 50% → 65%)          │
├──────────────────────────────────────────────────┤
│ 노드 8-9                                         │
│ • Google AI Studio ZIP 파싱                     │
│ • 컴포넌트 구조 분석                             │
│ • API 엔드포인트 추론                            │
└──────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────┐
│ Phase 4: 문서 생성 (완료율: 65% → 100%)         │
├──────────────────────────────────────────────────┤
│ 노드 10-17                                       │
│ • TRD 생성 및 검증                               │
│ • API 명세, DB 스키마 생성                       │
│ • 아키텍처, 기술 스택 문서                       │
│ • DB 저장 및 백로그 Agent 트리거                 │
└──────────────────────────────────────────────────┘
```

---

## 🔀 조건부 분기 6곳

### 1️⃣ 완전성 점수 체크 (노드 2 이후)

```
분석 완료
    ↓
점수 >= 80?
    ├─ Yes → 기술 Gap 탐지로
    └─ No  → 사용자 질문으로
```

**목적**: 기획이 불완전하면 먼저 보완

---

### 2️⃣ 기술 Gap 존재 여부 (노드 3 이후)

```
Gap 탐지 완료
    ↓
Gap 있음?
    ├─ Yes → 웹 검색으로
    └─ No  → 코드 파싱으로 점프
```

**목적**: 기술 결정이 필요 없으면 스킵

---

### 3️⃣ 검증 충돌 (노드 7 이후)

```
선택 검증
    ↓
충돌 있음?
    ├─ Yes → 경고 표시
    └─ No  → 다음 Gap 체크로
```

**목적**: 잘못된 선택을 사용자에게 경고

---

### 4️⃣ 사용자 재선택 여부 (노드 7-1 이후)

```
경고 표시
    ↓
사용자 선택
    ├─ 재선택 → 옵션 제시로 돌아감
    └─ 계속  → 다음 Gap 체크로
```

**목적**: 사용자가 최종 결정

---

### 5️⃣ 남은 결정 체크 (Phase 2 반복)

```
한 Gap 처리 완료
    ↓
남은 Gap 있음?
    ├─ Yes → 웹 검색으로 (다음 Gap)
    └─ No  → 코드 파싱으로
```

**목적**: 모든 Gap 해결까지 반복

---

### 6️⃣ TRD 검증 (노드 11 이후)

```
TRD 생성 완료
    ↓
품질 >= 90?
    ├─ Yes → API 명세 생성으로
    └─ No  → TRD 재생성 (최대 3회)
```

**목적**: 고품질 TRD 보장

---

## 📊 상태 데이터 구조

```typescript
interface TechSpecState {
  // 🆔 세션 정보
  session_id: string
  project_id: string
  user_id: string
  
  // 📥 입력
  prd_content: string
  design_docs: Record<string, string>
  initial_trd: string
  google_ai_studio_code_path?: string
  
  // 🔍 분석 결과
  completeness_score: number        // 0-100
  missing_elements: string[]
  ambiguous_elements: string[]
  
  // 🔎 기술 Gap
  technical_gaps: TechGap[]
  tech_research_results: ResearchResult[]
  selected_technologies: Record<string, Technology>
  pending_decisions: string[]       // gap IDs
  
  // 💬 대화
  current_question?: string
  conversation_history: Message[]
  
  // 💻 코드 분석
  google_ai_studio_data?: AIStudioData
  inferred_api_spec?: APISpec
  
  // 📝 생성 문서
  final_trd?: string
  api_specification?: string
  database_schema?: string
  architecture_diagram?: string
  tech_stack_document?: string
  
  // 📈 진행 상태
  current_stage: Stage
  completion_percentage: number     // 0-100
  iteration_count: number           // TRD 재생성 횟수
  
  // ⚠️ 에러
  errors: Error[]
}
```

---

## 🎯 핵심 기능 3가지

### 1. 🌐 오픈소스 기술 조사

```
사용자 요구: "사용자 로그인 필요"
    ↓
웹 검색: "authentication library 2025"
    ↓
후보 추출: NextAuth, Firebase Auth, Auth0 등 5개
    ↓
각 후보 상세 조사:
  • GitHub stats (⭐ stars, downloads)
  • 장단점 (pros & cons)
  • 사용 사례 (use cases)
  • 학습 난이도
  • 비용
    ↓
상위 3개 선택 → 사용자에게 제시
```

**특징**:
- ✅ 실시간 웹 검색 (최신 정보)
- ✅ 비개발자 친화적 비교 표
- ✅ AI 추천 포함

---

### 2. 💻 Google AI Studio 코드 분석

```
ZIP 파일 업로드
    ↓
압축 해제
    ↓
.tsx, .jsx 파일 찾기
    ↓
각 컴포넌트 파싱:
  • Props 인터페이스
  • State 변수
  • API 호출 (fetch, axios)
  • 이벤트 핸들러
    ↓
API 엔드포인트 추론:
  fetch('/api/users/:id')
    → GET /api/users/:id
    → 요청: none
    → 응답: UserProps 타입
    ↓
TRD에 자동 반영
```

**특징**:
- ✅ 디자인 코드 → API 명세 자동 생성
- ✅ 누락 방지 (모든 화면의 API 포함)
- ✅ 타입 정보 보존

---

### 3. 📝 5종 문서 자동 생성

```
모든 정보 수집 완료
    ↓
Claude Sonnet으로 생성:
    ↓
1️⃣ TRD (Markdown)
   • 프로젝트 개요
   • 기술 스택 (선택된 것들)
   • 시스템 아키텍처
   • API 명세 개요
   • DB 설계 개요
   • 보안/성능 요구사항
    ↓
2️⃣ API 명세서 (YAML)
   • OpenAPI 3.0 형식
   • 모든 엔드포인트 상세
   • 요청/응답 스키마
    ↓
3️⃣ DB 스키마 (SQL)
   • CREATE TABLE 문
   • 인덱스, 제약조건
   • ERD (Mermaid)
    ↓
4️⃣ 아키텍처 다이어그램 (Mermaid)
   • 시스템 구성도
   • 데이터 흐름
    ↓
5️⃣ 기술 스택 문서 (Markdown)
   • 각 기술 선택 이유
   • 설정 가이드
   • 학습 리소스
```

**특징**:
- ✅ 개발자가 바로 사용 가능한 수준
- ✅ 일관성 보장 (모든 문서가 동기화)
- ✅ 버전 관리 (DB에 저장)

---

## 💾 데이터베이스 구조

### 4개 핵심 테이블

```sql
-- 1️⃣ 세션 테이블
tech_spec_sessions
  ├─ id (UUID, PK)
  ├─ project_id (FK)
  ├─ user_id (FK)
  ├─ current_stage (VARCHAR)
  ├─ completion_percentage (DECIMAL)
  └─ started_at, completed_at (TIMESTAMP)

-- 2️⃣ 기술 조사 테이블
tech_research
  ├─ id (UUID, PK)
  ├─ session_id (FK)
  ├─ gap_category (VARCHAR)
  ├─ options (JSONB)          -- 3개 옵션 상세
  ├─ selected_option (VARCHAR)
  └─ selection_reason (TEXT)

-- 3️⃣ 대화 기록 테이블
tech_conversations
  ├─ id (UUID, PK)
  ├─ session_id (FK)
  ├─ role (VARCHAR)           -- 'agent' or 'user'
  ├─ message (TEXT)
  ├─ message_type (VARCHAR)
  └─ created_at (TIMESTAMP)

-- 4️⃣ 생성 문서 테이블
generated_trd_documents
  ├─ id (UUID, PK)
  ├─ session_id (FK)
  ├─ document_type (VARCHAR)  -- 'final_trd', 'api_spec', etc.
  ├─ content (TEXT)
  ├─ content_format (VARCHAR) -- 'markdown', 'yaml', 'sql'
  ├─ version (INT)
  └─ validated (BOOLEAN)
```

---

## 🔄 ANYON 워크플로우 내 위치

```
┌─────────────────────────────────────┐
│ 선-기획 Agent                       │  사용자 아이디어 구체화
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ 후-기획 Agent                       │  PRD/초기 TRD 작성
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ 디자인 Agent                        │  5종 디자인 문서 + AI Studio 코드
└─────────────────────────────────────┘
              ↓
╔═════════════════════════════════════╗
║ Tech Spec Agent  👈 여기!           ║  기술 스택 선정 + 상세 TRD
╚═════════════════════════════════════╝
              ↓
┌─────────────────────────────────────┐
│ 백로그 Agent                        │  Epic/Story 생성
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ 계획 Agent                          │  티켓별 실행 계획
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ 개발 Agent → 점검 → 리뷰           │  실제 코드 생성
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ 머지 → 충돌 → 아키텍처 → 퀄리티   │  통합 및 품질 관리
└─────────────────────────────────────┘
```

**Tech Spec Agent의 역할**:
- ✅ 기획(PRD/디자인)과 개발(백로그/코드) 사이의 브리지
- ✅ 모호함 제거 (기술 선택 완료)
- ✅ 개발 가능한 수준의 상세 스펙 제공

---

## 📱 사용자 경험 예시

### 시나리오: "반려동물 커뮤니티" 프로젝트

```
[디자인 Agent 완료]
    ↓
사용자: 칸반보드에서 "Tech Spec" 단계로 드래그
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 Agent:
안녕하세요! Tech Spec Agent입니다. 🤖
PRD와 디자인 문서를 분석하겠습니다.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ↓
[분석 중... 15%]
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 Agent:
기획 완전성: 85/100 ✅

기술 스택 결정이 필요한 항목 5개를 발견했습니다:
1. 사용자 인증 시스템
2. 파일 업로드 (반려동물 사진)
3. 데이터베이스
4. 실시간 채팅
5. 배포 환경

첫 번째 항목부터 시작하겠습니다!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ↓
[웹 검색 중... 30%]
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 Agent:
## 사용자 인증 시스템 선택

조사 결과 3가지 옵션:

1. NextAuth.js ⭐ AI 추천
   설명: Next.js 전용 인증 라이브러리
   
   ✅ 장점:
   • 완전 무료
   • Next.js와 완벽한 통합
   • 소셜 로그인 쉬움
   • 커스터마이징 가능
   
   ❌ 단점:
   • 초기 설정 1-2시간 소요
   • Next.js 외에는 사용 불가
   
   📊 인기도: ⭐ 24,000 GitHub stars
   📚 학습 난이도: 중 (2-3시간)
   💰 비용: 무료

2. Firebase Auth
   설명: Google의 완전 관리형 인증
   
   ✅ 장점:
   • 설정 10분
   • 매우 쉬움
   • 안정적
   
   ❌ 단점:
   • 비용 발생 (무료: 월 3,000명)
   • 커스터마이징 제한
   
   📊 인기도: Google 공식
   📚 학습 난이도: 하 (1시간)
   💰 비용: 무료 → $0.0055/인증

3. Auth0
   설명: 엔터프라이즈급 인증
   
   ✅ 장점:
   • 매우 강력
   • 보안 최고
   
   ❌ 단점:
   • 비용 높음 ($23/월~)
   • 복잡함
   
   📊 인기도: 업계 표준
   📚 학습 난이도: 상 (5시간+)
   💰 비용: $23/월~

어떤 옵션을 선택하시겠습니까?
1, 2, 3 또는 "AI 추천"을 입력하세요.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ↓
사용자: 1
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 Agent:
✅ NextAuth.js를 선택하셨습니다!

다음 항목으로 넘어가겠습니다.

## 파일 업로드 (반려동물 사진)

조사 결과 3가지 옵션:
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ↓
[반복... 5개 항목 모두 선택]
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 Agent:
모든 기술 스택 선택이 완료되었습니다! ✅

선택된 기술:
• 인증: NextAuth.js
• 파일: Cloudinary
• DB: PostgreSQL + Prisma
• 실시간: Socket.io
• 배포: Vercel

이제 Google AI Studio 코드를 분석하고
TRD 문서를 생성하겠습니다...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ↓
[코드 분석 중... 60%]
[TRD 생성 중... 75%]
[문서 생성 중... 90%]
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 Agent:
🎉 Tech Spec 작성이 완료되었습니다!

생성된 문서:
✅ TRD (Technical Requirements Document)
✅ API 명세서 (25개 엔드포인트)
✅ 데이터베이스 스키마 (8개 테이블)
✅ 아키텍처 다이어그램
✅ 기술 스택 문서

품질 점수: 95/100

백로그 Agent가 자동으로 시작됩니다!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ↓
[백로그 단계로 자동 전환]
```

**소요 시간**: 약 15-25분 (기술 선택 5개)

---

## 🚀 구현 우선순위

### Phase 1: 기본 구조 (1-2주)
- ✅ LangGraph 노드 스켈레톤
- ✅ PostgreSQL 테이블 생성
- ✅ WebSocket 서버 기본 구조

### Phase 2: 핵심 기능 (2-3주)
- ✅ PRD/디자인 분석 로직
- ✅ 웹 검색 통합
- ✅ 기술 조사 파이프라인
- ✅ 사용자 대화 흐름

### Phase 3: 코드 분석 (1-2주)
- ✅ Google AI Studio ZIP 파서
- ✅ React 컴포넌트 AST 파싱
- ✅ API 엔드포인트 추론

### Phase 4: 문서 생성 (1-2주)
- ✅ TRD 생성 엔진
- ✅ API 명세, DB 스키마 생성
- ✅ 품질 검증 시스템

### Phase 5: 통합 및 테스트 (1주)
- ✅ ANYON 플랫폼 통합
- ✅ 칸반보드 연동
- ✅ 백로그 Agent 트리거

---

## 📈 성공 지표

| 지표 | 목표 | 측정 방법 |
|-----|-----|---------|
| **완료율** | 95% | 시작한 세션 중 TRD 완성 비율 |
| **평균 시간** | 15-25분 | 시작부터 완료까지 |
| **사용자 만족도** | 4.5/5.0 | 완료 후 설문 |
| **TRD 품질** | 90/100 | 자동 검증 점수 |
| **기술 선택 유지율** | 85% | 개발 후에도 선택한 기술 유지 |

---

## 🎓 주요 학습 포인트

### 1. LangGraph 조건부 분기
```python
workflow.add_conditional_edges(
    "validate_decision",
    has_validation_conflict,
    {
        "show_warning": "warn_user",
        "no_conflict": "check_more_decisions"
    }
)
```

### 2. 상태 Annotation (리스트 누적)
```python
from typing import Annotated
import operator

conversation_history: Annotated[List[Dict], operator.add]
# append 대신 += 사용 시 자동 누적
```

### 3. Checkpoint 재개
```python
config = {"configurable": {"thread_id": session_id}}
last_state = await graph.aget_state(config)
# 중단된 지점부터 재개 가능
```

---

이 문서로 Tech Spec Agent의 전체 구조를 한눈에 파악할 수 있습니다! 🎯
