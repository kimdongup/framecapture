import os
import cv2


def extract_frames(video_path, output_dir, every_frame=False):
    """영상의 프레임을 이미지 파일로 캡처하여 저장하는 함수

    :param video_path: 원본 영상 파일 경로 (예: 'trimmed_video.mp4')
    :param output_dir: 캡처본을 저장할 폴더명
    :param every_frame: True면 모든 프레임 저장, False면 1초에 1장만 저장
    """
    # 저장할 폴더가 없으면 새로 생성
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 비디오 파일 열기
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("오류: 영상을 열 수 없습니다. 파일 경로를 확인해 주세요.")
        return

    # 영상 정보 가져오기
    fps = round(cap.get(cv2.CAP_PROP_FPS))  # 초당 프레임 수 (예: 30fps)
    print(f"영상 FPS(초당 프레임): {fps}")

    frame_count = 0
    saved_count = 0

    while True:
        ret, frame = cap.read()

        # 더 이상 읽을 프레임이 없으면 반복문 종료
        if not ret:
            break

        # 추출 조건 설정
        # every_frame이 True이거나, 1초(fps) 주기에 해당하는 프레임일 때만 저장
        if every_frame or (frame_count % fps == 0):
            # 파일명 형식: 폴더/frame_000001.png
            file_name = f"frame_{frame_count:06d}.png"
            file_path = os.path.join(output_dir, file_name)

            # 이미지 저장
            cv2.imwrite(file_path, frame)
            saved_count += 1

        frame_count += 1

    # 자원 해제
    cap.release()
    print("-" * 40)
    print(f"작업 완료! 총 {saved_count}개의 이미지가 저장되었습니다.")
    print(f"저장 위치: {os.path.abspath(output_dir)}")


# --- 사용 예시 ---
if __name__ == "__main__":
    # 💡 파일명과 저장할 폴더명을 본인 환경에 맞게 입력하세요.
    VIDEO_FILE = "trimmed_video.mp4"
    OUTPUT_FOLDER = "captured_frames"

    # 옵션 선택
    # False: 1초당 1장만 저장 (10초 영상이면 약 10장 생성 - 글자 읽기용으로 추천)
    # True: 모든 프레임 저장 (10초 영상, 30fps 기준 300장 생성)
    SAVE_ALL = True

    extract_frames(VIDEO_FILE, OUTPUT_FOLDER, every_frame=SAVE_ALL)

