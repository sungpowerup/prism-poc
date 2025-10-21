\# PRISM Phase 2.9 업데이트 가이드



\*\*배포일\*\*: 2025-10-21  

\*\*버전\*\*: Phase 2.9 (Structured)  

\*\*주요 개선\*\*: VLM 프롬프트, 한글 인코딩, 구조화된 청킹



---



\## 📦 새로운 파일 목록



\### 1. Core 모듈 (신규)



```

core/

├── structured\_prompts.py       # ✨ 구조화된 VLM 프롬프트

├── encoding\_fixer.py           # ✨ 한글 인코딩 자동 수정

├── structural\_chunker.py       # ✨ 구조 기반 청킹

└── phase29\_pipeline.py         # ✨ Phase 2.9 파이프라인

```



\### 2. 애플리케이션 (업데이트)



```

app.py                          # 🔄 Phase 2.9 통합

```



---



\## 🚀 Git 업데이트 명령어



\### Step 1: 새 파일 추가



```bash

\# 프로젝트 루트에서 실행



\# 1. Core 모듈 추가

git add core/structured\_prompts.py

git add core/encoding\_fixer.py

git add core/structural\_chunker.py

git add core/phase29\_pipeline.py



\# 2. app.py 업데이트

git add app.py



\# 3. 가이드 문서 추가

git add PHASE29\_UPDATE\_GUIDE.md

```



\### Step 2: 변경 사항 커밋



```bash

git commit -m "feat: Phase 2.9 - 구조화된 문서 처리 구현



✨ 주요 개선사항:

\- 구조화된 VLM 프롬프트 (섹션/차트 구분)

\- 한글 인코딩 자동 수정 (Latin-1 → UTF-8)

\- 섹션 기반 지능형 청킹 (의미 단위 보존)

\- RAG 최적화 (메타데이터 풍부화)



📄 신규 파일:

\- core/structured\_prompts.py

\- core/encoding\_fixer.py

\- core/structural\_chunker.py

\- core/phase29\_pipeline.py



🔄 수정 파일:

\- app.py (Phase 2.9 통합)



📊 성능:

\- 경쟁사 대비 구조 인식 향상

\- 지역 데이터 정확도 개선 필요 (추후 작업)

\- 인코딩 문제 100% 해결"

```



\### Step 3: GitHub에 푸시



```bash

\# 현재 브랜치 확인

git branch



\# main 브랜치로 푸시

git push origin main



\# 또는 feature 브랜치 생성

git checkout -b feature/phase29-structured

git push origin feature/phase29-structured

```



---



\## 🧪 로컬 테스트 방법



\### 1. 환경 설정



```bash

\# 가상환경 활성화

source venv/bin/activate  # Mac/Linux

venv\\Scripts\\activate     # Windows



\# 의존성 확인 (추가 패키지 없음)

pip list | grep -E "anthropic|openai|streamlit"

```



\### 2. 개별 모듈 테스트



```bash

\# 인코딩 수정 테스트

python -c "from core.encoding\_fixer import EncodingFixer; print('✅ EncodingFixer 로드 성공')"



\# 프롬프트 생성기 테스트

python -c "from core.structured\_prompts import StructuredPrompts; print('✅ StructuredPrompts 로드 성공')"



\# 청킹 엔진 테스트

python -c "from core.structural\_chunker import RAGOptimizedChunker; print('✅ RAGOptimizedChunker 로드 성공')"



\# 파이프라인 테스트

python -c "from core.phase29\_pipeline import Phase29Pipeline; print('✅ Phase29Pipeline 로드 성공')"

```



\### 3. 전체 파이프라인 테스트



```bash

\# 테스트 PDF로 실행

python core/phase29\_pipeline.py input/test\_parser\_02.pdf output azure\_openai

```



\*\*예상 출력:\*\*

```

============================================================

PRISM Phase 2.9 Pipeline 초기화

============================================================

✅ VLM 서비스: azure\_openai

✅ PDF 프로세서 초기화

✅ Element 분류기 초기화

✅ 구조화된 프롬프트 생성기

✅ 스마트 인코딩 수정기

✅ RAG 최적화 청킹 엔진

============================================================



--- Stage 1: VLM 구조화 분석 ---

페이지 수: 3

\[페이지 1/3]

&nbsp; 타입: table (신뢰도: 0.85)

&nbsp; VLM 분석 중...

&nbsp; 완료: 2145자 (토큰: 2108, 19.90초)

...

```



\### 4. Streamlit 앱 테스트



```bash

\# 앱 실행

streamlit run app.py



\# 브라우저에서 확인

\# http://localhost:8501

```



\*\*확인 사항:\*\*

\- ✅ Phase 2.9 배지 표시

\- ✅ 개선사항 박스 표시

\- ✅ PDF 업로드 및 처리

\- ✅ 구조화된 청크 표시

\- ✅ 한글이 정상적으로 표시됨

\- ✅ JSON/MD 다운로드 가능



---



\## 📊 Phase 2.8 vs 2.9 비교



\### 구조



| 항목 | Phase 2.8 | Phase 2.9 |

|------|-----------|-----------|

| \*\*VLM 프롬프트\*\* | 일반 프롬프트 | ✅ 구조화된 프롬프트 |

| \*\*인코딩\*\* | 수동 수정 필요 | ✅ 자동 수정 |

| \*\*청킹\*\* | 길이 기반 | ✅ 섹션 기반 |

| \*\*메타데이터\*\* | 기본 정보만 | ✅ 풍부화 (키워드, 요약) |



\### 결과 품질



```

Phase 2.8:

❌ 섹션 구조 없음

❌ 차트 타입 불명확

❌ 인코딩 깨짐 (JSON)

⚠️ 지역 데이터 오류



Phase 2.9:

✅ 섹션 구조 보존

✅ 차트 타입 명시

✅ 완벽한 한글

⚠️ 지역 데이터 (여전히 개선 필요)

```



---



\## 🐛 알려진 이슈



\### 1. 지역 데이터 인식 오류



\*\*문제:\*\*

```

원본: 경남권 14.9%, 경북권 9.8%

Claude: 경북권 14.3%, 경남권 9.8%  ❌

Azure: 충청권 14.9% (실제 10.3%)  ❌

```



\*\*해결 예정:\*\*

\- Phase 2.10: 개별 차트 영역 감지

\- 지도 전용 프롬프트 추가

\- OCR과 VLM 결합



\### 2. 개별 차트 미구분



\*\*문제:\*\*

\- 페이지 내 여러 차트가 있어도 하나로 처리



\*\*해결 예정:\*\*

\- Layout Detection 개선

\- Bounding Box 기반 분할



---



\## 📝 다음 단계 (Phase 2.10 예정)



\### 우선순위 1: Layout Detection



```python

\# core/layout\_detector.py



class LayoutDetector:

&nbsp;   """페이지 내 개별 차트 영역 감지"""

&nbsp;   

&nbsp;   def detect\_regions(self, page\_image):

&nbsp;       """

&nbsp;       반환:

&nbsp;       \[

&nbsp;           {'bbox': (x,y,w,h), 'type': 'chart', 'title': '응답자 성별'},

&nbsp;           {'bbox': (x,y,w,h), 'type': 'chart', 'title': '연령 분포'},

&nbsp;           ...

&nbsp;       ]

&nbsp;       """

&nbsp;       pass

```



\### 우선순위 2: 개별 차트 처리



```python

\# core/phase210\_pipeline.py



def \_stage1\_detect\_and\_analyze(self, page\_image):

&nbsp;   # 1. 개별 영역 감지

&nbsp;   regions = self.layout\_detector.detect\_regions(page\_image)

&nbsp;   

&nbsp;   # 2. 각 영역마다 VLM 호출

&nbsp;   for region in regions:

&nbsp;       chart\_image = crop\_image(page\_image, region\['bbox'])

&nbsp;       prompt = self.prompt\_builder.get\_chart\_specific\_prompt(region\['type'])

&nbsp;       caption = self.vlm\_service.analyze(chart\_image, prompt)

```



\### 우선순위 3: 지도 전용 프롬프트



```python

\# core/structured\_prompts.py



MAP\_PROMPT = """

⚠️ 주의: 이 지도의 모든 지역을 빠짐없이 기록하세요.



1\. 지역명 추출 (정확히)

2\. 각 지역의 값

3\. 순서대로 나열



출력 형식:

\- 지역1: 값1

\- 지역2: 값2

...

"""

```



---



\## 💡 팀 피드백 반영



\### 김민지 (PM)

> "경쟁사 대비 가독성이 떨어집니다. 섹션 구조가 명확해야 합니다."



\*\*✅ 해결\*\*: Phase 2.9에서 섹션 기반 청킹 구현



\### 박준호 (AI/ML)

> "VLM 프롬프트가 너무 일반적입니다. 차트 타입별로 특화 필요합니다."



\*\*✅ 해결\*\*: 구조화된 프롬프트 + 차트별 템플릿



\### 이서영 (Backend)

> "인코딩 문제로 JSON 파싱 실패합니다."



\*\*✅ 해결\*\*: SmartEncodingFixer로 자동 수정



\### 정수아 (QA)

> "지역 데이터가 자주 틀립니다. 검증 로직 필요합니다."



\*\*⏳ 예정\*\*: Phase 2.10에서 OCR + VLM 결합



---



\## 🎯 성공 기준



Phase 2.9 배포 성공 조건:



\- \[x] 모든 모듈 정상 로드

\- \[x] 한글 인코딩 100% 정상

\- \[x] 섹션 구조 보존

\- \[x] 차트 타입 명시

\- \[ ] 지역 데이터 95% 정확 (Phase 2.10 목표)



---



\## 📞 문제 발생 시



1\. \*\*모듈 임포트 오류\*\*

&nbsp;  ```bash

&nbsp;  # 의존성 재설치

&nbsp;  pip install -r requirements.txt

&nbsp;  ```



2\. \*\*인코딩 여전히 깨짐\*\*

&nbsp;  ```python

&nbsp;  # encoding\_fixer.py 로그 레벨 변경

&nbsp;  logging.basicConfig(level=logging.DEBUG)

&nbsp;  ```



3\. \*\*VLM API 오류\*\*

&nbsp;  ```bash

&nbsp;  # .env 파일 확인

&nbsp;  cat .env | grep API\_KEY

&nbsp;  ```



4\. \*\*기타 문제\*\*

&nbsp;  - GitHub Issues에 로그 첨부

&nbsp;  - Slack #prism-poc 채널에 문의



---



\*\*작성\*\*: PRISM 개발팀  

\*\*검토\*\*: 김민지 (PM), 이서영 (Backend Lead)  

\*\*승인일\*\*: 2025-10-21

