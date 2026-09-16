import os
import cv2
from skimage.metrics import structural_similarity as ssim


def remove_sequential_duplicates(folder_path, similarity_threshold=0.98):
    """앞뒤 이미지를 순차적으로 비교하여 기준점과 유사한 뒤의 이미지를 제거하는 함수

    :param folder_path: 정제할 이미지들이 들어있는 폴더 경로
    :param similarity_threshold: 유사도 임계값 (0.98 = 98% 이상 시각적 구조가 일치하면 중복으로 판단)
    """
    if not os.path.exists(folder_path):
        print("오류: 지정한 폴더가 존재하지 않습니다.")
        return

    # 1. 파일 이름 순서대로 정렬 (타임라인 순서 보장)
    files = sorted(os.listdir(folder_path))
    image_files = [
        f
        for f in files
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))
    ]

    if len(image_files) < 2:
        print("분석할 이미지가 충분하지 않습니다. (최소 2장 필요)")
        return

    print(
        f"총 {len(image_files)}개의 이미지에서 순차적 중복 제거를 시작합니다..."
    )
    print("구조적 유사성(SSIM) 알고리즘 분석 중...")
    print("-" * 50)

    # 2. 첫 번째 이미지를 최초의 '비교 기준점(Reference)'으로 설정
    ref_idx = 0
    ref_name = image_files[ref_idx]
    ref_path = os.path.join(folder_path, ref_name)
    ref_img = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)

    deleted_count = 0

    # 3. 두 번째 이미지부터 순차적으로 탐색
    for i in range(1, len(image_files)):
        current_name = image_files[i]
        current_path = os.path.join(folder_path, current_name)
        current_img = cv2.imread(current_path, cv2.IMREAD_GRAYSCALE)

        if current_img is None or ref_img is None:
            continue

        # 💡 [핵심] 두 이미지의 해상도(크기)가 다른 경우를 대비해 크기를 강제로 맞춥니다.
        if ref_img.shape != current_img.shape:
            current_img = cv2.resize(
                current_img, (ref_img.shape[1], ref_img.shape[0])
            )

        # 4. 두 이미지 간의 구조적 유사도(SSIM) 계산 (결과값: 0.0 ~ 1.0)
        score, _ = ssim(ref_img, current_img, full=True)

        # 5. 설정한 임계값보다 유사도가 높으면 '중복'으로 판단하여 삭제
        if score >= similarity_threshold:
            try:
                os.remove(current_path)
                print(
                    f"-> [삭제] {current_name} (기준점 {ref_name}와 {score*100:.2f}% 일치)"
                )
                deleted_count += 1
            except Exception as e:
                print(f"파일 삭제 오류 ({current_name}): {e}")
        else:
            # 💡 [핵심] 다른 이미지로 판명되면, 이 이미지를 '새로운 비교 기준점'으로 교체합니다!
            print(
                f"[유지] {current_name} (새로운 내용 감지, 이전 기준점과 유사도: {score*100:.2f}%)"
            )
            ref_name = current_name
            ref_path = current_path
            ref_img = current_img  # 기준점 이미지 데이터 갱신

    print("-" * 50)
    print(f"작업 완료! 총 {deleted_count}개의 연속 중복 이미지를 청소했습니다.")
    print(f"현재 폴더에는 내용이 전환되는 핵심 장면만 생존해 있습니다.")


if __name__ == "__main__":
    # 💡 글씨만 크롭했던 대상 폴더명을 지정해 주세요.
    TARGET_FOLDER = "captured_frames"

    # similarity_threshold=0.98 (98% 이상 같으면 지웁니다)
    # 글자가 1~2글자 미세하게 바뀌는 것까지 다 잡아내려면 0.99로 높이시고,
    # 굵직하게 단락이 바뀔 때만 남기려면 0.95~0.97로 낮춰보세요.
    remove_sequential_duplicates(TARGET_FOLDER, similarity_threshold=0.98)

