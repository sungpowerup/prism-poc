\# PRISM POC - Changelog



\## \[2025-10-09] OCR + Ollama 통합



\### 🎉 주요 변경사항



\#### 1. OCR 통합 (PaddleOCR)

\- \*\*파일\*\*: `core/pdf\_processor.py`

\- \*\*변경\*\*:

&nbsp; - PaddleOCR 추가 (한국어 OCR)

&nbsp; - PDF 페이지에서 텍스트 자동 추출

&nbsp; - OCR 신뢰도 계산

\- \*\*이슈 수정\*\*:

&nbsp; - `show\_log` 파라미터 제거 (PaddleOCR 3.2.0 호환)

&nbsp; - 이모지 제거 (Windows cp949 인코딩 오류 방지)



\#### 2. Ollama (Local sLLM) 지원

\- \*\*파일\*\*: `core/vlm\_service.py`

\- \*\*변경\*\*:

&nbsp; - Anthropic Claude API → Ollama API로 전환

&nbsp; - 로컬 Vision Language Model 지원

&nbsp; - llava:7b, llama3.2-vision 등 사용 가능

\- \*\*장점\*\*:

&nbsp; - API 비용 $0

&nbsp; - 완전 로컬 실행

&nbsp; - 데이터 프라이시 보장



\#### 3. 프롬프트 개선

\- \*\*파일\*\*: `core/vlm\_service.py`

\- \*\*변경\*\*:

&nbsp; - OCR 텍스트를 프롬프트에 포함

&nbsp; - 한국어 최적화 프롬프트

&nbsp; - Element 타입별 맞춤 프롬프트



\#### 4. UI 개선

\- \*\*파일\*\*: `app.py`

\- \*\*변경\*\*:

&nbsp; - OCR 텍스트 표시 탭 추가

&nbsp; - OCR 신뢰도 메트릭 추가

&nbsp; - Element별 4개 탭 (OCR/VLM/이미지/메타데이터)



\### 📦 의존성 추가



```txt

paddlepaddle

paddleocr

```



\### 🔧 설정 변경



\#### .env 파일

\- `OLLAMA\_BASE\_URL`: Ollama 서버 주소

\- `OLLAMA\_MODEL`: 사용할 Vision 모델

\- `DEFAULT\_VLM\_PROVIDER`: local\_sllm



\### 🐛 버그 수정



1\. \*\*PaddleOCR 파라미터 오류\*\*

&nbsp;  - `show\_log=False` 제거

&nbsp;  - PaddleOCR 3.2.0 호환



2\. \*\*Windows 인코딩 오류\*\*

&nbsp;  - 로그 메시지에서 이모지 제거

&nbsp;  - cp949 인코딩 문제 해결



3\. \*\*Import 오류\*\*

&nbsp;  - `Database` import 제거

&nbsp;  - `ElementClassifier` 옵션 처리



\### 📊 성능



\- \*\*OCR\*\*: 3-5초/페이지 (CPU)

\- \*\*VLM\*\*: 40-60초/페이지 (llava:7b, RTX 3050)

\- \*\*총\*\*: 45-65초/페이지



\### 🎯 다음 단계



\- \[ ] GPU 최적화

\- \[ ] 병렬 처리

\- \[ ] 캐싱 시스템

\- \[ ] Azure OpenAI Vision API 통합 (옵션)



---



\## \[이전 버전]



\### \[2025-10-08] 초기 버전

\- PDF 파싱

\- Element 추출

\- Claude Vision API 통합

\- 기본 UI

