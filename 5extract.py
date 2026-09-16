import os  # 💡 이 부분이 누락되어 에러가 발생했습니다. 추가해 주세요!
from ocrmac import ocrmac


INPUT_FOLDER = "captured_frames"
OUTPUT_TXT = "apple_live_text_result.txt"


def extract_text_via_apple_ocr(input_folder, output_txt_path):
    """맥 순정 Vision Framework를 사용하여 폴더 내 이미지 글자를 최고 화질로 추출하는 함수"""
    if not os.path.exists(input_folder):
        print("오류: 지정한 이미지 폴더가 존재하지 않습니다.")
        return

    # 1. 파일 이름 순서대로 정렬 (타임라인 순서 보장)
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
        f" Apple Vision Framework 가동: {len(image_files)}개의 이미지 분석을 시작합니다."
    )
    print("-" * 60)

    # 2. 결과 텍스트 파일 생성
    with open(output_txt_path, "w", encoding="utf-8") as txt_file:
        for idx, file_name in enumerate(image_files, 1):
            file_path = os.path.join(input_folder, file_name)
            print(f"[{idx}/{len(image_files)}] {file_name} 판독 중...")

            try:
                # 💡 [핵심] 맥 미리보기와 동일한 '정밀 인식 모드'로 이미지 판독
                # recognition_level='accurate' 옵션이 맥 라이브 텍스트와 동일한 품질을 냅니다.
                annotations = ocrmac.OCR(
                    file_path, recognition_level="accurate"
                ).recognize()

                # 결과물에서 위치 정보 좌표를 제외하고 순수 텍스트만 추출
                extracted_lines = [item[0] for item in annotations]

                if extracted_lines:
                    txt_file.write(f"\n\n=== [{file_name} 프롬프트 단락] ===\n")
                    # 추출된 문장들을 자연스럽게 줄바꿈하여 누적 저장
                    txt_file.write("\n".join(extracted_lines))
                else:
                    txt_file.write(
                        f"\n\n=== [{file_name}] 추출된 글자가 없습니다. ===\n"
                    )

            except Exception as e:
                print(f"오류 발생 ({file_name}): {e}")

    print("-" * 60)
    print("축하합니다! 맥 순정 OCR 자동화 처리가 모두 완료되었습니다.")
    print(f"최종 고품질 텍스트 파일: {os.path.abspath(output_txt_path)}")


if __name__ == "__main__":
    extract_text_via_apple_ocr(INPUT_FOLDER, OUTPUT_TXT)

