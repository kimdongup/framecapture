import os
import cv2
import easyocr


def extract_text_to_single_file(input_folder, output_txt_path):
    """폴더 내 모든 이미지에서 글자를 추출하여 하나의 텍스트 파일로 모으는 함수

    :param input_folder: 글자를 추출할 이미지들이 들어있는 폴더 경로 (예: 'only_gray_boxes')
    :param output_txt_path: 저장할 통합 텍스트 파일 경로 (예: 'extracted_prompt.txt')
    """
    if not os.path.exists(input_folder):
        print("오류: 지정한 이미지 폴더가 존재하지 않습니다.")
        return

    # 1. 폴더 내 이미지 파일 목록 정렬 (타임라인 순서대로 정렬됨)
    files = sorted(os.listdir(input_folder))
    image_files = [
        f
        for f in files
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))
    ]

    if not image_files:
        print("폴더 내에 인식할 이미지 파일이 없습니다.")
        return

    # 2. EasyOCR 판독기 설정 (한국어 및 영어 동시 인식)
    print("OCR 판독기를 초기화하는 중입니다... (최초 실행 시 다소 시간이 걸릴 수 있습니다.)")
    reader = easyocr.Reader(["ko", "en"])

    print(f"총 {len(image_files)}개의 이미지에서 텍스트 추출을 시작합니다.")
    print("-" * 50)

    # 3. 텍스트 파일 쓰기 모드로 열기 (UTF-8 인코딩으로 한글 깨짐 방지)
    with open(output_txt_path, "w", encoding="utf-8") as txt_file:
        for idx, file_name in enumerate(image_files, 1):
            file_path = os.path.join(input_folder, file_name)
            print(f"[{idx}/{len(image_files)}] {file_name} 분석 중...")

            # 이미지 읽기
            img = cv2.imread(file_path)
            if img is None:
                continue

            # 4. OCR 글자 추출 수행
            # detail=0으로 설정하면 위치 좌표를 제외하고 순수 '텍스트 문자열'만 리스트로 반환합니다.
            results = reader.readtext(img, detail=0)

            if results:
                # 텍스트 파일에 파일 정보 기록 (출처 구분용)
                txt_file.write(f"\n\n=== [파일: {file_name}] 추출 결과 ===\n")

                # 추출된 글자들을 줄바꿈을 포함하여 연결 후 파일에 저장
                full_text = "\n".join(results)
                txt_file.write(full_text)
            else:
                txt_file.write(
                    f"\n\n=== [파일: {file_name}] 추출된 글자가 없습니다. ===\n"
                )

    print("-" * 50)
    print(f"모든 작업이 성공적으로 완료되었습니다!")
    print(f"최종 텍스트 파일 저장 위치: {os.path.abspath(output_txt_path)}")


# --- 사용 예시 ---
if __name__ == "__main__":
    # 💡 글자가 들어있는 이미지 폴더와 저장할 텍스트 파일명을 지정해 주세요.
    INPUT_FOLDER = "only_gray_boxes"
    FINAL_TEXT_FILE = "result_prompt_collection.txt"

    extract_text_to_single_file(INPUT_FOLDER, FINAL_TEXT_FILE)

