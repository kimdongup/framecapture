import os
import cv2
import numpy as np


def crop_only_gray_text_box(input_folder, output_folder):
    """이미지 주변의 상단바와 배경을 모두 지우고, 회색 프롬프트 박스만 정확히 도려내는 함수"""
    if not os.path.exists(input_folder):
        print("오류: 지정한 원본 폴더가 존재하지 않습니다.")
        return

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    files = os.listdir(input_folder)
    image_files = [
        f
        for f in files
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))
    ]

    if not image_files:
        print("폴더 내에 이미지 파일이 없습니다.")
        return

    print(f"총 {len(image_files)}개의 이미지에서 순수 글자 박스만 추출합니다...")
    success_count = 0

    for file_name in image_files:
        input_path = os.path.join(input_folder, file_name)
        output_path = os.path.join(output_folder, file_name)

        img = cv2.imread(input_path)
        if img is None:
            continue

        # 💡 [핵심 변경] 샘플 이미지의 순수 회색 박스 색상(BGR) 범위를 직접 타겟팅합니다.
        # BGR 색상 검출 범위 설정 (너무 어둡거나 밝은 영역 원천 차단)
        lower_gray = np.array([25, 25, 25])  # 어두운 회색 하한선
        upper_gray = np.array([55, 55, 55])  # 밝은 회색 상한선

        # 설정한 색상 범위 안의 회색 박스만 1(흰색)로 만들고 나머지는 0(검은색)으로 마스킹
        mask = cv2.inRange(img, lower_gray, upper_gray)

        # 마스크에서 형태(윤곽선) 추적
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            cv2.imwrite(output_path, img)
            continue

        # 발견된 형태들 중 가장 면적이 큰 영역을 프롬프트 본문 박스로 선택
        best_contour = max(contours, key=cv2.contourArea)

        # 화면 노이즈가 잡히는 것을 방지하기 위해 최소 면적 크기 제한 (5000 픽셀 이상)
        if cv2.contourArea(best_contour) > 5000:
            x, y, w, h = cv2.boundingRect(best_contour)

            # 💡 글자가 테두리에 너무 바짝 붙어 짤리는 것을 막기 위해 사방으로 5픽셀 마진 추가
            margin = 5
            ny = max(0, y - margin)
            nx = max(0, x - margin)
            nh = min(img.shape[0] - ny, h + (margin * 2))
            nw = min(img.shape[1] - nx, w + (margin * 2))

            # 최종 크롭 수행
            cropped_box = img[ny : ny + nh, nx : nx + nw]
            cv2.imwrite(output_path, cropped_box)
            success_count += 1
        else:
            cv2.imwrite(output_path, img)

    print("-" * 40)
    print(f"작업 완료! {success_count}개의 이미지에서 회색 박스를 성공적으로 추출했습니다.")
    print(f"저장 위치: {os.path.abspath(output_folder)}")


# --- 사용 예시 ---
if __name__ == "__main__":
    # 💡 원본 폴더와 정제될 결과 폴더명을 지정하세요.
    INPUT_FOLDER = "cropped_frames_60"
    BOX_OUTPUT_FOLDER = "pure_text_boxes"

    crop_only_gray_text_box(INPUT_FOLDER, BOX_OUTPUT_FOLDER)

