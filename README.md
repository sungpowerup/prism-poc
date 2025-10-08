\# 🔷 PRISM POC - Local sLLM



\*\*Progressive Reasoning \& Intelligence for Structured Materials\*\*



VLM 기반 문서 전처리 POC - Local sLLM 버전 (무료)



---



\## 🎯 특징



\- ✅ \*\*완전 무료\*\*: Ollama + LLaVA (GPU 전기료만)

\- ✅ \*\*오프라인 가능\*\*: 인터넷 불필요

\- ✅ \*\*데이터 안전\*\*: 외부 전송 없음

\- ✅ \*\*간단 설치\*\*: 10분 설정



---



\## 📋 요구사항



\### 하드웨어

\- \*\*GPU\*\*: NVIDIA RTX 3050 이상 (4GB+ VRAM) 권장

\- \*\*RAM\*\*: 8GB 이상

\- \*\*Storage\*\*: 10GB 여유 공간



\### 소프트웨어

\- \*\*OS\*\*: Windows 10/11

\- \*\*Python\*\*: 3.11+ (3.13.7 테스트됨)

\- \*\*Ollama\*\*: 최신 버전



---



\## 🚀 설치 방법



\### 1. Ollama 설치



```powershell

\# https://ollama.com/download/windows

\# OllamaSetup.exe 다운로드 및 설치

```



\### 2. 모델 다운로드



```powershell

ollama pull llama3.2-vision

```



\### 3. 프로젝트 설정



```powershell

\# 가상환경

python -m venv venv

venv\\Scripts\\activate



\# 패키지 설치

pip install -r requirements.txt

```



\### 4. 실행



```powershell

\# 터미널 1: Ollama 서버 (백그라운드 실행 중)

\# (별도 실행 불필요)



\# 터미널 2: Streamlit 앱

streamlit run app.py

```



---



\## 📖 사용 방법



1\. \*\*PDF 업로드\*\*: 10MB, 20페이지까지

2\. \*\*VLM 처리\*\*: 페이지당 5-10초 (GPU 성능에 따라)

3\. \*\*결과 확인\*\*: 페이지별 자연어 캡션



---



\## 🔧 설정



`.env` 파일:



```bash

OLLAMA\_BASE\_URL=http://localhost:11434

OLLAMA\_MODEL=llama3.2-vision

DEFAULT\_VLM\_PROVIDER=local\_sllm

```



---



\## 📊 성능



\- \*\*정확도\*\*: ~70-75%

\- \*\*속도\*\*: 5-10초/페이지 (RTX 3050)

\- \*\*비용\*\*: 무료 (GPU 전기료만)



---



\## 🐛 문제 해결



\### Ollama 서버 오류

```powershell

\# 프로세스 확인

Get-Process ollama



\# 재시작

Stop-Process -Name ollama -Force

ollama serve

```



\### GPU 메모리 부족

```powershell

\# 더 작은 모델 사용

ollama pull llama3.2-vision

```



---



\## 📞 지원



\- GitHub Issues

\- Claude 프로젝트 채팅



---



\## 📄 라이선스



MIT License



---



\*\*개발:\*\* PRISM 팀  

\*\*버전:\*\* 0.1.0  

\*\*날짜:\*\* 2025년 10월 8일

