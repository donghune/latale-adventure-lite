# 숫자 템플릿 생성 가이드

이 디렉토리에 게임 화면에서 추출한 숫자 템플릿 이미지를 저장합니다.
템플릿 매칭을 통해 게임 화면의 숫자를 인식하는 데 사용됩니다.

## 파일 명명 규칙

- 기본 형식: `{숫자}.png` (예: `0.png`, `1.png`, ..., `9.png`)
- 여러 변형: `{숫자}_{번호}.png` (예: `0_1.png`, `0_2.png`)
- 변형이 많을수록 인식 정확도가 향상됩니다

## 템플릿 만드는 방법

### 방법 1: 자동 추출 (권장)

Python 코드를 사용하여 게임 스크린샷에서 숫자를 자동으로 잘라냅니다:

```python
import cv2
from desktop.capture.matcher import DigitMatcher

# 게임 스크린샷 로드
image = cv2.imread("game_screenshot.png")

# 숫자 이미지 자동 추출
count = DigitMatcher.extract_templates_from_image(
    image,
    output_dir="desktop/capture/templates",
    label_prefix=""
)
print(f"{count}개의 숫자 이미지가 추출되었습니다")
```

추출된 파일(`digit_0.png`, `digit_1.png`, ...)을 확인하고
실제 숫자에 맞게 이름을 변경하세요 (예: `digit_0.png` -> `3.png`).

### 방법 2: 수동 추출

1. 게임 화면에서 숫자가 보이는 부분을 스크린샷합니다
2. 이미지 편집 프로그램(그림판, Photoshop 등)으로 각 숫자를 개별 잘라냅니다
3. 각 숫자를 해당하는 파일 이름으로 저장합니다

## 권장 사항

- **이미지 크기**: 높이 20~30px 권장
- **배경**: 가능하면 깨끗한 배경의 숫자를 사용하세요
- **그레이스케일**: 컬러/그레이스케일 모두 가능 (자동 변환됨)
- **여러 변형**: 같은 숫자의 다른 모양을 여러 개 저장하면 인식률이 올라갑니다
- **파일 형식**: PNG 형식 사용

## 필요한 파일

최소한 0~9까지 각 숫자에 대해 하나의 템플릿이 필요합니다:

```
templates/
  0.png
  1.png
  2.png
  3.png
  4.png
  5.png
  6.png
  7.png
  8.png
  9.png
```
