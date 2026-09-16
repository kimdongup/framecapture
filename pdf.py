import os
import img2pdf


def images_to_pdf(folder_path, output_pdf_path):
    """폴더 내의 모든 이미지 파일을 이름 순으로 정렬하여 하나의 PDF로 만드는 함수

    :param folder_path: 이미지들이 저장된 폴더 경로
    :param output_pdf_path: 생성할 PDF 파일명 (예: 'result.pdf')
    """
    if not os.path.exists(folder_path):
        print("오류: 지정한 폴더가 존재하지 않습니다.")
        return

    # 1. 폴더 내 이미지 파일 목록 가져오기 및 이름순 정렬
    files = sorted(os.listdir(folder_path))
    image_files = [
        os.path.join(folder_path, f)
        for f in files
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff"))
    ]

    if not image_files:
        print("폴더 내에 변환할 이미지 파일이 없습니다.")
        return

    print(f"총 {len(image_files)}장의 이미지를 PDF로 변환하는 중...")

    try:
        # 2. 이미지들을 하나의 PDF 데이터로 변환 후 파일 저장
        with open(output_pdf_path, "wb") as f:
            f.write(img2pdf.convert(image_files))

        print("-" * 40)
        print(f"성공: PDF 생성이 완료되었습니다.")
        print(f"저장 위치: {os.path.abspath(output_pdf_path)}")

    except Exception as e:
        print(f"오류가 발생했습니다: {e}")


# --- 사용 예시 ---
if __name__ == "__main__":
    # 💡 이미지가 들어있는 폴더명과 저장할 PDF 파일명을 입력하세요.
    TARGET_FOLDER = "pure_text_boxes"
    OUTPUT_FILE = "prompt_images_collection.pdf"

    images_to_pdf(TARGET_FOLDER, OUTPUT_FILE)

