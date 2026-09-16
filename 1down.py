from moviepy.video.io.VideoFileClip import VideoFileClip


def cut_video(input_path, output_path, start_time, end_time):
    """MP4 동영상의 특정 구간을 잘라서 저장하는 함수

    :param input_path: 원본 영상 파일 경로 (예: 'origin.mp4')
    :param output_path: 저장할 영상 파일 경로 (예: 'output.mp4')
    :param start_time: 시작 시간 (초 단위 또는 "시:분:초" 문자열)
    :param end_time: 종료 시간 (초 단위 또는 "시:분:초" 문자열)
    """
    try:
        # 1. 원본 동영상 파일 로드
        with VideoFileClip(input_path) as video:
            # 2. 지정한 구간만큼 서브클립 생성
            clipped_video = video.subclip(start_time, end_time)

            # 3. 잘라낸 영상을 파일로 저장 (오디오 포함)
            clipped_video.write_videofile(
                output_path,
                codec="libx264",  # MP4 표준 코덱
                audio_codec="aac",  # 오디오 코덱
            )
        print(f"성공: 영상을 잘라 '{output_path}'로 저장했습니다.")

    except Exception as e:
        print(f"오류가 발생했습니다: {e}")


# --- 사용 예시 ---
if __name__ == "__main__":
    # 원본 파일명, 저장할 파일명 설정
    ORIGIN_FILE = "origin.mp4"
    OUTPUT_FILE = "trimmed_video.mp4"

    # 방법 A: 초 단위로 지정하는 방법 (예: 2분 16초 ~ 2분 26초)
    # 2분 16초 = 136초 / 2분 26초 = 146초
    START = 136
    END = 146

    # 방법 B: 문자열로 직접 지정하는 방법 (시:분:초)
    # START = "00:02:16"
    # END = "00:02:26"

    # 함수 실행
    cut_video(ORIGIN_FILE, OUTPUT_FILE, START, END)

