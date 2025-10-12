\# 🔧 Detectron2 설치 가이드



\*\*PRISM Phase 2.1 - Layout Detection 개선\*\*



Detectron2는 Facebook Research의 고성능 물체 탐지 라이브러리입니다.  

문서 레이아웃 분석(표, 그림, 텍스트 영역 탐지)에 사용됩니다.



---



\## 📋 설치 전 요구사항



\### 필수 패키지

```bash

Python: 3.8 - 3.11

PyTorch: 1.10 이상

CUDA: 11.1 이상 (GPU 사용 시)

```



\### 시스템 체크

```bash

\# Python 버전 확인

python --version



\# PyTorch 및 CUDA 확인

python -c "import torch; print(f'PyTorch: {torch.\_\_version\_\_}'); print(f'CUDA: {torch.cuda.is\_available()}')"

```



\*\*예상 출력:\*\*

```

PyTorch: 2.0.1

CUDA: True  # GPU 있으면 True, 없으면 False

```



---



\## 🚀 설치 방법



\### Option 1: GPU 환경 (권장)



\*\*1. CUDA Toolkit 설치 (Windows)\*\*

```bash

\# NVIDIA 웹사이트에서 다운로드

https://developer.nvidia.com/cuda-downloads



\# 또는 conda로 설치

conda install cudatoolkit=11.8 -c pytorch

```



\*\*2. PyTorch 설치 (CUDA 버전)\*\*

```bash

pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

```



\*\*3. Detectron2 설치\*\*

```bash

\# 방법 A: pip (권장)

pip install 'git+https://github.com/facebookresearch/detectron2.git'



\# 방법 B: 소스 빌드

git clone https://github.com/facebookresearch/detectron2.git

cd detectron2

pip install -e .

```



---



\### Option 2: CPU 환경 (GPU 없는 경우)



\*\*1. PyTorch 설치 (CPU 버전)\*\*

```bash

pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

```



\*\*2. Detectron2 설치 (CPU)\*\*

```bash

\# 빌드 도구 설치 (Windows)

pip install --upgrade setuptools wheel



\# Detectron2 소스 다운로드

git clone https://github.com/facebookresearch/detectron2.git

cd detectron2



\# CPU 전용 빌드

FORCE\_CUDA=0 pip install -e .

```



\*\*⚠️ 주의:\*\*  

CPU 모드는 GPU보다 10-20배 느립니다. 테스트용으로만 권장합니다.



---



\### Option 3: 사전 빌드 버전 (빠른 설치)



```bash

\# Python 3.8, PyTorch 1.10, CUDA 11.1

pip install detectron2 -f \\

&nbsp; https://dl.fbaipublicfiles.com/detectron2/wheels/cu111/torch1.10/index.html



\# Python 3.9, PyTorch 1.13, CPU

pip install detectron2 -f \\

&nbsp; https://dl.fbaipublicfiles.com/detectron2/wheels/cpu/torch1.13/index.html

```



\*\*💡 Tip:\*\* 사전 빌드 버전은 빠르지만, 최신 버전이 아닐 수 있습니다.



---



\## ✅ 설치 확인



```python

\# test\_detectron2.py

import torch

import detectron2

from detectron2 import model\_zoo

from detectron2.config import get\_cfg



print("✅ Detectron2 설치 성공!")

print(f"   Version: {detectron2.\_\_version\_\_}")

print(f"   PyTorch: {torch.\_\_version\_\_}")

print(f"   CUDA available: {torch.cuda.is\_available()}")



\# Config 로드 테스트

cfg = get\_cfg()

cfg.merge\_from\_file(model\_zoo.get\_config\_file("COCO-Detection/faster\_rcnn\_R\_50\_FPN\_3x.yaml"))

print("✅ Config 로드 성공!")

```



\*\*실행:\*\*

```bash

python test\_detectron2.py

```



\*\*예상 출력:\*\*

```

✅ Detectron2 설치 성공!

&nbsp;  Version: 0.6

&nbsp;  PyTorch: 2.0.1

&nbsp;  CUDA available: True

✅ Config 로드 성공!

```



---



\## 🔧 문제 해결



\### 문제 1: CUDA 버전 불일치



\*\*증상:\*\*

```

RuntimeError: CUDA mismatch: detectron2 was compiled with CUDA 11.1 but PyTorch was compiled with CUDA 11.8

```



\*\*해결:\*\*

```bash

\# PyTorch와 CUDA 버전을 맞춰 재설치

pip uninstall torch torchvision detectron2

pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

pip install 'git+https://github.com/facebookresearch/detectron2.git'

```



---



\### 문제 2: Visual C++ 빌드 도구 누락 (Windows)



\*\*증상:\*\*

```

error: Microsoft Visual C++ 14.0 or greater is required

```



\*\*해결:\*\*

1\. Visual Studio Build Tools 다운로드:  

&nbsp;  https://visualstudio.microsoft.com/downloads/

2\. "C++ 빌드 도구" 선택 후 설치

3\. Detectron2 재설치



---



\### 문제 3: 메모리 부족 (GPU)



\*\*증상:\*\*

```

CUDA out of memory

```



\*\*해결:\*\*

```python

\# models/layout\_detector.py 수정

cfg.MODEL.ROI\_HEADS.BATCH\_SIZE\_PER\_IMAGE = 128  # 기본값: 512

cfg.MODEL.DEVICE = "cpu"  # GPU 메모리 부족 시 CPU 사용

```



---



\### 문제 4: import 오류



\*\*증상:\*\*

```

ModuleNotFoundError: No module named 'detectron2'

```



\*\*해결:\*\*

```bash

\# 가상환경 확인

which python

pip list | grep detectron2



\# 재설치

pip uninstall detectron2

pip install 'git+https://github.com/facebookresearch/detectron2.git'

```



---



\## 📊 성능 비교



| 환경 | 처리 속도 | 메모리 사용 |

|------|----------|------------|

| \*\*Mock Mode\*\* | 0.1초/페이지 | 100MB |

| \*\*Detectron2 (CPU)\*\* | 2-3초/페이지 | 2GB |

| \*\*Detectron2 (GPU)\*\* | 0.3-0.5초/페이지 | 4GB (VRAM) |



\*\*권장:\*\*

\- 개발/테스트: Mock Mode

\- 프로덕션: Detectron2 (GPU)



---



\## 🎯 PRISM에서 사용하기



\### 자동 감지 및 폴백



```python

\# models/layout\_detector.py

class LayoutDetector:

&nbsp;   def \_\_init\_\_(self):

&nbsp;       try:

&nbsp;           from detectron2 import model\_zoo

&nbsp;           from detectron2.config import get\_cfg

&nbsp;           from detectron2.engine import DefaultPredictor

&nbsp;           

&nbsp;           cfg = get\_cfg()

&nbsp;           cfg.merge\_from\_file(model\_zoo.get\_config\_file(

&nbsp;               "COCO-Detection/faster\_rcnn\_R\_50\_FPN\_3x.yaml"

&nbsp;           ))

&nbsp;           cfg.MODEL.WEIGHTS = model\_zoo.get\_checkpoint\_url(

&nbsp;               "COCO-Detection/faster\_rcnn\_R\_50\_FPN\_3x.yaml"

&nbsp;           )

&nbsp;           cfg.MODEL.DEVICE = "cuda" if torch.cuda.is\_available() else "cpu"

&nbsp;           

&nbsp;           self.predictor = DefaultPredictor(cfg)

&nbsp;           self.use\_detectron = True

&nbsp;           print("✅ Detectron2 loaded successfully")

&nbsp;           

&nbsp;       except ImportError:

&nbsp;           print("⚠️  Detectron2 not available. Using Mock mode.")

&nbsp;           self.use\_detectron = False

```



\*\*결과:\*\*

\- Detectron2 설치됨 → 자동 사용

\- Detectron2 없음 → Fallback Table Extractor 사용



---



\## 📦 전체 설치 스크립트



\### Windows (GPU)

```bash

\# install\_detectron2\_gpu.bat

@echo off

echo Installing Detectron2 (GPU)...



REM CUDA 확인

python -c "import torch; print(torch.cuda.is\_available())"



REM PyTorch (CUDA 11.8)

pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118



REM Detectron2

pip install git+https://github.com/facebookresearch/detectron2.git



REM 확인

python -c "import detectron2; print('Success!')"



pause

```



\### Linux (GPU)

```bash

\#!/bin/bash

\# install\_detectron2\_gpu.sh



echo "Installing Detectron2 (GPU)..."



\# PyTorch (CUDA 11.8)

pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118



\# Detectron2

pip install 'git+https://github.com/facebookresearch/detectron2.git'



\# 확인

python -c "import detectron2; print('Success!')"

```



\### CPU 전용 (모든 OS)

```bash

\#!/bin/bash

\# install\_detectron2\_cpu.sh



echo "Installing Detectron2 (CPU)..."



\# PyTorch (CPU)

pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu



\# Detectron2 (소스 빌드)

git clone https://github.com/facebookresearch/detectron2.git

cd detectron2

FORCE\_CUDA=0 pip install -e .



\# 확인

python -c "import detectron2; print('Success!')"

```



---



\## 🚀 다음 단계



1\. \*\*설치 완료 후:\*\*

```bash

\# PRISM 파이프라인 테스트

python core/phase2\_pipeline.py data/uploads/test.pdf

```



2\. \*\*성능 확인:\*\*

```bash

\# 청킹 품질 테스트

python tests/test\_chunking\_quality.py data/processed/test\_chunks.json

```



3\. \*\*Mock Mode와 비교:\*\*

&nbsp;  - Mock Mode: 표 추출 0개

&nbsp;  - Detectron2: 표 추출 성공!



---



\## 📞 문제 발생 시



1\. \*\*GitHub Issues:\*\*  

&nbsp;  https://github.com/facebookresearch/detectron2/issues



2\. \*\*PRISM 팀 슬랙:\*\*  

&nbsp;  #prism-tech-support



3\. \*\*이메일:\*\*  

&nbsp;  hwang.taemin@prism.ai (황태민 - DevOps Lead)



---



\## ✅ 체크리스트



설치 완료 확인:



\- \[ ] Python 3.8-3.11 설치

\- \[ ] PyTorch 설치 및 CUDA 확인

\- \[ ] Detectron2 설치

\- \[ ] `import detectron2` 성공

\- \[ ] PRISM 파이프라인 테스트 완료

\- \[ ] 표 추출 성공 확인



\*\*모두 체크되면 Phase 2.1 준비 완료!\*\* 🎉

