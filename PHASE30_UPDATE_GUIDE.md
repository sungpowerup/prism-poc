\# PRISM Phase 3.0 업데이트 가이드



\*\*배포일\*\*: 2025-10-22  

\*\*버전\*\*: Phase 3.0 (Layout Detection)  

\*\*주요 개선\*\*: CV 기반 Layout Detection + Region-based VLM Analysis



---



\## 📦 새로운 파일 목록



\### 1. Core 모듈 (신규/업데이트)



```

core/

├── layout\_detector.py         # ✨ Layout Detection (신규)

├── section\_chunker.py          # ✨ Section-aware Chunker (신규)

├── phase30\_pipeline.py         # ✨ Phase 3.0 파이프라인 (신규)

└── vlm\_service.py              # 🔄 VLM 서비스 (기존 사용)

```



\### 2. Prompts (신규/업데이트)



```

prompts/

├── layout\_prompt.py            # ✨ Layout Detection 프롬프트 (신규)

├── chart\_prompt.py             # 🔄 차트 프롬프트 (업데이트)

└── table\_prompt.py             # 🔄 표 프롬프트 (업데이트)

```



\### 3. 애플리케이션 (신규)



```

app\_phase30.py                  # ✨ Phase 3.0 Streamlit 앱 (신규)

```



\### 4. 문서 (신규)



```

PHASE30\_UPDATE\_GUIDE.md         # 이 파일

```



---



\## 🚀 Git 업데이트 명령어



\### Step 1: 새 파일 추가



```bash

\# 프로젝트 루트에서 실행



\# 1. Core 모듈 추가

git add core/layout\_detector.py

git add core/section\_chunker.py

git add core/phase30\_pipeline.py



\# 2. Prompts 추가/업데이트

git add prompts/layout\_prompt.py

git add prompts/chart\_prompt.py

git add prompts/table\_prompt.py



\# 3. 앱 추가

git add app\_phase30.py



\# 4. 문서 추가

git add PHASE30\_UPDATE\_GUIDE.md

```



\### Step 2: 변경 사항 커밋



```bash

git commit -m "feat: Phase 3.0 - Layout Detection + Region-based Analysis



✨ 주요 신규 기능:

\- Layout Detection: CV + VLM 하이브리드 영역 감지

\- Region-based VLM Analysis: 개별 영역별 정밀 분석

\- Section-aware Chunking: 섹션 구조 보존

\- 데이터 정확도 100% 목표 (권역, 성별 등)



📄 신규 파일:

\- core/layout\_detector.py (CV 기반 영역 감지)

\- core/section\_chunker.py (구조 인식 청킹)

\- core/phase30\_pipeline.py (Phase 3.0 파이프라인)

\- prompts/layout\_prompt.py (Layout Detection 프롬프트)

\- app\_phase30.py (Phase 3.0 Streamlit 앱)



🔄 업데이트 파일:

\- prompts/chart\_prompt.py (데이터 정확도 강화)

\- prompts/table\_prompt.py (구조 보존 강화)



🎯 성능 목표:

\- 권역 데이터: 33.3% → 100%

\- K리그 성별: 0% → 100%

\- 섹션 추출: 0% → 100%

\- 개별 차트 구분: 0% → 100%

\- 종합 점수: 17.8점 → 95점+"

```



\### Step 3: GitHub에 푸시



```bash

\# main 브랜치로 푸시

git push origin main



\# 또는 feature 브랜치 생성

git checkout -b feature/phase30-layout-detection

git push origin feature/phase30-layout-detection

```



---



\## 🧪 로컬 테스트 방법



\### 1. 환경 설정



```bash

\# 가상환경 활성화

source venv/bin/activate  # Mac/Linux

venv\\Scripts\\activate     # Windows



\# 의존성 확인 (추가 패키지 없음)

pip list | grep -E "opencv|anthropic|streamlit"

```



\### 2. 개별 모듈 테스트



\#### Layout Detector 테스트



```bash

python -c "from core.layout\_detector import LayoutDetector; print('✅ LayoutDetector 로드 성공')"

```



\#### Section Chunker 테스트



```bash

python core/section\_chunker.py

```



출력 예시:

```

생성된 청크: 4개



============================================================

ID: chunk\_000

Type: section\_header

Section: 06 응답자 특성

Content: \[섹션] 06 응답자 특성...

```



\### 3. 전체 파이프라인 테스트



```bash

\# CLI로 실행

python -m core.phase30\_pipeline input/test\_parser\_02.pdf output azure\_openai

```



\*\*예상 출력\*\*:

```

============================================================

PRISM Phase 3.0 Pipeline 초기화

============================================================

✅ PDF Processor

✅ VLM Service (azure\_openai)

✅ Layout Detector

✅ Section-aware Chunker

============================================================



--- Stage 1: PDF → Page Images ---

✅ 3개 페이지 변환 완료



============================================================

페이지 1/3 처리

============================================================



--- Stage 2: Layout Detection ---

1\. 헤더 감지 중...

&nbsp;  → 2개 헤더 감지

2\. 차트 감지 중...

&nbsp;  → 4개 차트 감지

3\. 표 감지 중...

&nbsp;  → 0개 표 감지

4\. 지도 감지 중...

&nbsp;  → 1개 지도 감지



총 7개 영역 감지 완료



--- Stage 3: Region-based Extraction ---

\[Region 1/7] header

&nbsp;  헤더: 06 응답자 특성

...



--- Stage 4: Section-aware Chunking ---

✅ 15개 청크 생성 완료



✅ Phase 3.0 처리 완료

&nbsp;  총 처리 시간: 120.5초

&nbsp;  감지된 영역: 21개

&nbsp;  생성된 청크: 45개

```



\### 4. Streamlit 앱 테스트



```bash

\# 앱 실행

streamlit run app\_phase30.py



\# 브라우저에서 확인

\# http://localhost:8501

```



\*\*확인 사항\*\*:

\- ✅ Phase 3.0 배지 표시

\- ✅ Layout Detection 개선사항 박스

\- ✅ PDF 업로드 및 처리

\- ✅ 4개 탭 표시 (개요, 감지 영역, 청크, 다운로드)

\- ✅ JSON/MD 다운로드 가능



---



\## 📊 Phase 2.9 vs 3.0 비교



\### 아키텍처 변화



| 항목 | Phase 2.9 | Phase 3.0 |

|------|-----------|-----------|

| \*\*영역 감지\*\* | ❌ 없음 | ✅ Layout Detection |

| \*\*처리 단위\*\* | 페이지 전체 | 개별 영역 |

| \*\*VLM 호출\*\* | 페이지당 1회 | 영역당 1회 (더 정밀) |

| \*\*청킹 기준\*\* | 길이 기반 | 구조 기반 |

| \*\*메타데이터\*\* | 기본 정보 | section\_path, chart\_number 등 |



\### 품질 개선



```

Phase 2.9:

❌ 권역 데이터: 33.3% 정확도

❌ K리그 성별: 0% 정확도

❌ 섹션 헤더: 추출 안됨

❌ 개별 차트: 구분 안됨

❌ 종합 점수: 17.8점



Phase 3.0 목표:

✅ 권역 데이터: 100% 정확도

✅ K리그 성별: 100% 정확도

✅ 섹션 헤더: 100% 추출

✅ 개별 차트: 완벽 구분

✅ 종합 점수: 95점+

```



---



\## 🐛 알려진 이슈 및 해결 방법



\### 1. OpenCV ImportError



\*\*문제\*\*:

```

ImportError: libGL.so.1: cannot open shared object file

```



\*\*해결\*\* (Linux):

```bash

sudo apt-get update

sudo apt-get install -y libgl1-mesa-glx

```



\*\*해결\*\* (Windows):

```bash

pip install --upgrade opencv-python

```



\### 2. Layout Detection 속도 느림



\*\*문제\*\*: 페이지당 처리 시간이 30초 이상



\*\*원인\*\*: VLM 검증을 모든 영역에 수행



\*\*해결\*\*:

```python

\# layout\_detector.py에서 VLM 검증 비활성화

layout\_detector = LayoutDetector(use\_vlm\_validation=False)

```



\*\*또는\*\* 임계값 조정:

```python

self.thresholds\['vlm\_confidence\_threshold'] = 0.9  # 0.7 → 0.9

```



\### 3. 메모리 부족 (대용량 PDF)



\*\*문제\*\*: 20페이지 이상 처리 시 메모리 부족



\*\*해결\*\*: 배치 처리

```python

\# 5페이지씩 분할 처리

for i in range(0, total\_pages, 5):

&nbsp;   result = pipeline.process\_pdf(pdf\_path, max\_pages=5)

```



---



\## 🎯 다음 단계 (Phase 3.1 예정)



\### 우선순위 1: OCR 통합



```python

\# core/ocr\_service.py (신규)

class OCRService:

&nbsp;   """PaddleOCR 통합"""

&nbsp;   def extract\_text(self, crop\_image):

&nbsp;       # 헤더, 텍스트 영역은 OCR 우선 사용

&nbsp;       pass

```



\### 우선순위 2: Layout Detection 고도화



```python

\# YOLO 또는 Detectron2 모델 사용

class DeepLayoutDetector:

&nbsp;   """딥러닝 기반 Layout Detection"""

&nbsp;   def \_\_init\_\_(self):

&nbsp;       self.model = load\_model('layout\_detection\_yolo.pt')

```



\### 우선순위 3: 데이터 검증 레이어



```python

\# core/data\_validator.py (신규)

class DataValidator:

&nbsp;   """추출된 데이터 검증"""

&nbsp;   def validate\_regional\_data(self, regions):

&nbsp;       # 지역 개수 확인

&nbsp;       # 합계 100% 확인

&nbsp;       # 지역명 중복 확인

&nbsp;       pass

```



---



\## 💡 팀 피드백 반영



\### 김민지 (PM)

> "경쟁사 수준 달성 필요. 구조 인식 필수."



\*\*✅ Phase 3.0 해결\*\*: Layout Detection + Section-aware Chunking



\### 박준호 (AI/ML)

> "VLM 프롬프트를 차트 타입별로 특화."



\*\*✅ Phase 3.0 해결\*\*: 차트 타입별 전용 프롬프트 (PIE, BAR, LINE 등)



\### 이서영 (Backend)

> "확장성 고려. 대용량 처리 가능해야 함."



\*\*⏳ Phase 3.1 예정\*\*: 배치 처리, 멀티 프로세싱



\### 정수아 (QA)

> "데이터 정확도 검증 로직 필요."



\*\*⏳ Phase 3.1 예정\*\*: DataValidator 구현



---



\## 🎉 Phase 3.0 성공 기준



배포 성공 조건:



\- \[x] 모든 모듈 정상 임포트

\- \[x] Layout Detection 동작

\- \[x] Region-based Extraction 동작

\- \[x] Section-aware Chunking 동작

\- \[x] Streamlit 앱 실행

\- \[ ] 권역 데이터 95%+ 정확 (테스트 필요)

\- \[ ] K리그 성별 100% 정확 (테스트 필요)

\- \[ ] 종합 점수 90점+ (경쟁사 비교 필요)



---



\## 📞 문제 발생 시



1\. \*\*GitHub Issues\*\*: 상세 로그 첨부

2\. \*\*Slack #prism-poc\*\*: 긴급 문의

3\. \*\*Email\*\*: dev@prism-poc.com



---



\*\*작성\*\*: PRISM 개발팀  

\*\*검토\*\*: 김민지 (PM), 박준호 (AI/ML Lead)  

\*\*승인일\*\*: 2025-10-22



\*\*Phase 3.0: Layout Detection의 시대가 열렸습니다! 🚀\*\*

