from moviepy.video.io.VideoFileClip import VideoFileClip


def cut_video(input_path, output_path, start_time, end_time):
    try:
        with VideoFileClip(input_path) as video:
            # 💡 기존 subclip 대신 'subclipped'를 사용합니다.
            clipped_video = video.subclipped(start_time, end_time)

            clipped_video.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
            )
        print(f"성공: 영상을 잘라 '{output_path}'로 저장했습니다.")
    except Exception as e:
        print(f"오류가 발생했습니다: {e}")


if __name__ == "__main__":
    # 💡 2분 16초 ~ 2분 26초를 초 단위로 환산 (136초 ~ 146초)
    # 최신 버전에서는 문자열("00:02:16") 오류가 날 수 있으므로 안전하게 '숫자(초)'로 입력해 주세요.
    cut_video("my_video.mp4", "trimmed_video.mp4", 136, 146)

