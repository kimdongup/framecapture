import os
from ocrmac import ocrmac

# 💡 프롬프트 박스가 크롭되어 모여있는 폴더 경로를 지정하세요
INPUT_FOLDER = "pure_text_boxes"
OUTPUT_TXT = "apple_live_text_result.txt"


def extract_korean_via_apple_ocr(input_folder, output_txt_path):
    """맥의 온디바이스 Vision LiveText 프레임워크를 연동하여 한글을 정확히 복원하는 함수"""
    if not os.path.exists(input_folder):
        print("오류: 지정한 이미지 폴더가 존재하지 않습니다.")
        return

    # 파일 이름 순서대로 정렬 (타임라인 순서 보장)
    files = sorted(os.listdir(input_folder))
    image_files = [
        f
        for f in files
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))
    ]

    if not image_files:
        print("폴더 내에 인식할 이미지 파일이 없습니다.")
        return

    print(
        f" Apple Vision LiveText 가동: {len(image_files)}개의 이미지 분석을 시작합니다."
    )
    print("-" * 60)

    with open(output_txt_path, "w", encoding="utf-8") as txt_file:
        for idx, file_name in enumerate(image_files, 1):
            file_path = os.path.join(input_folder, file_name)
            print(f"[{idx}/{len(image_files)}] {file_name} 판독 중...")

            try:
                # 💡 [핵심 패치] framework="livetext" 옵션을 추가하여 맥의 한글 통합 사전 엔진을 활성화합니다.
                annotations = ocrmac.OCR(
                    file_path, framework="livetext", unit="line"
                ).recognize()

                # 결과 튜플에서 0번째 요소(추출된 한 줄 문장 문자열)만 쏙 뽑아옵니다.
                extracted_lines = [item[0] for item in annotations]

                if extracted_lines:
                    txt_file.write(f"\n\n=== [{file_name} 프롬프트 단락] ===\n")
                    # 여러 줄을 자연스럽게 줄바꿈하여 텍스트 파일에 누적
                    txt_file.write("\n".join(extracted_lines))
                else:
                    txt_file.write(
                        f"\n\n=== [{file_name}] 추출된 글자가 없습니다. ===\n"
                    )

            except Exception as e:
                print(f"오류 발생 ({file_name}): {e}")

    print("-" * 60)
    print("축하합니다! 맥북 내장 엔진을 이용한 한글/영어 자동 OCR이 완료되었습니다.")
    print(f"최종 텍스트 파일 저장 위치: {os.path.abspath(output_txt_path)}")


if __name__ == "__main__":
    extract_korean_via_apple_ocr(INPUT_FOLDER, OUTPUT_TXT)

