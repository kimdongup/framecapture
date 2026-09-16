# FlowTextCapture

영상 구간 선택, 프레임 샘플링, 자동 텍스트 영역 검출, 연속 중복 제거, OCR, 맞춤법 후처리를 하나의 파이프라인으로 통합한 프로그램입니다. 기존 `1down.py`~`5ext.py` 파일은 비교와 복구를 위해 그대로 두었습니다.

## 설치 및 실행

```bash
python -m venv .venv
source .venv/bin/activate             # Windows: .venv\Scripts\activate
pip install -r requirements-macos.txt # macOS
# pip install -r requirements-windows.txt  # Windows
python gui.py                         # 데스크톱 앱 실행
```

`gui.py`는 macOS, Windows, Linux에서 독립된 데스크톱 창을 엽니다. macOS에서는 Cocoa/WebKit, Windows에서는 사용 가능한 네이티브 WebView를 활용합니다. 네이티브 WebView를 사용할 수 없는 환경에서는 기본 브라우저로 자동 전환됩니다.

## 모바일 접속 모드

같은 Wi-Fi의 휴대폰에서 사용하려면 다음처럼 서버 모드로 실행한 뒤 컴퓨터의 로컬 IP와 포트 `5000`으로 접속합니다. 신뢰하는 사설망에서만 사용하세요.

```bash
VIDEO_OCR_HOST=0.0.0.0 python app.py
```

모바일은 반응형 웹 UI로 지원합니다. 데스크톱 앱과 모바일 화면은 같은 처리 엔진과 설정을 사용하며, 영상 처리는 서버를 실행하는 Mac/Windows/Linux 컴퓨터가 담당합니다.

지원 브라우저에서는 홈 화면에 추가하여 PWA 형태로 열 수 있습니다. 일반 브라우저 접속은 HTTP에서도 가능하지만, 일부 모바일 브라우저의 PWA 설치와 오프라인 앱 셸은 HTTPS 또는 localhost에서만 허용됩니다.

CLI도 사용할 수 있습니다.

```bash
python video_ocr.py my_video.mp4 --start 10 --end 80 --interval 0.5
```

결과는 `outputs/<작업명>/`에 생성됩니다. `corrected.txt`는 맞춤법 후처리본, `extracted.txt`는 OCR 원문, `results.json`은 타임스탬프와 이미지 경로를 포함합니다. LanguageTool을 사용할 수 없으면 공백 정규화만 수행하며 OCR 원문은 항상 별도 보존됩니다.

## 플랫폼별 OCR

- macOS: `auto`에서 Apple Vision/Live Text를 먼저 사용합니다.
- Windows: `auto`에서 Tesseract를 사용합니다. Windows 설치본에는 Tesseract 실행 파일과 `kor`, `eng` 학습 데이터를 `tesseract/` 폴더로 함께 넣을 수 있습니다.
- EasyOCR와 PyTorch는 배포 크기를 줄이기 위해 사용하지 않습니다.

## 운영체제별 빌드

코드베이스와 빌드 설정은 하나이며 각 운영체제에서 한 번씩 빌드합니다. 다른 OS용 실행 파일을 교차 빌드하지 않습니다.

```bash
pip install -r requirements-build.txt
pyinstaller --clean FlowTextCapture.spec
```

- macOS 빌드 결과: `dist/FlowTextCapture.app`
- Windows 빌드 결과: `dist/FlowTextCapture.exe`

Windows에서 Tesseract를 실행 파일에 포함하려면 프로젝트의 `tesseract/` 폴더에 `tesseract.exe`와 `tessdata/kor.traineddata`, `tessdata/eng.traineddata`를 넣고 spec의 `datas`에 추가합니다. 시스템에 설치된 Tesseract를 사용하는 경우에는 추가 번들이 필요하지 않습니다.

자동 크롭은 색상값에 의존하지 않습니다. 문자에서 반복되는 수평 그래디언트를 찾아 중앙에 가까운 텍스트 묶음을 합치며, 확신할 수 없을 때는 중앙의 넓은 안전 영역을 남겨 글자가 잘리는 위험을 줄입니다.
