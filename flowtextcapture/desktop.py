"""Native desktop window for FlowTextCapture on macOS, Windows and Linux."""

from __future__ import annotations

import threading
import webbrowser
import shutil
from pathlib import Path

from werkzeug.serving import make_server

from app import OUTPUTS, app


class DesktopAPI:
    """Native-only operations that browsers intentionally cannot perform."""

    def __init__(self) -> None:
        self.window = None

    def save_result(self, job: str, result_type: str) -> dict[str, str | bool]:
        names = {"corrected": "corrected.txt", "extracted": "extracted.txt"}
        filename = names.get(result_type)
        if not filename or Path(job).name != job:
            return {"ok": False, "message": "잘못된 결과 파일 요청입니다."}
        source = (OUTPUTS / job / filename).resolve()
        try:
            source.relative_to(OUTPUTS.resolve())
        except ValueError:
            return {"ok": False, "message": "허용되지 않은 파일 경로입니다."}
        if not source.is_file():
            return {"ok": False, "message": "결과 파일을 찾을 수 없습니다."}

        import webview

        default_name = "FlowTextCapture_교정본.txt" if result_type == "corrected" else "FlowTextCapture_OCR원문.txt"
        chosen = self.window.create_file_dialog(
            webview.FileDialog.SAVE,
            directory=str(Path.home() / "Downloads"),
            save_filename=default_name,
            file_types=("Text files (*.txt)",),
        )
        if not chosen:
            return {"ok": False, "cancelled": True, "message": "저장이 취소되었습니다."}
        destination = Path(chosen[0] if isinstance(chosen, (list, tuple)) else chosen)
        shutil.copy2(source, destination)
        return {"ok": True, "message": f"저장 완료: {destination}"}


class LocalServer:
    """Run Flask on a private, randomly assigned localhost port."""

    def __init__(self) -> None:
        self.server = make_server("127.0.0.1", 0, app, threaded=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()


def run_browser_fallback(server: LocalServer) -> None:
    print(f"FlowTextCapture: {server.url}")
    webbrowser.open(server.url)
    try:
        server.thread.join()
    except KeyboardInterrupt:
        server.stop()


def main() -> None:
    server = LocalServer()
    server.start()
    try:
        import webview
    except ImportError:
        print("pywebview가 없어 기본 브라우저로 실행합니다.")
        run_browser_fallback(server)
        return

    try:
        api = DesktopAPI()
        window = webview.create_window(
            "FlowTextCapture",
            server.url,
            js_api=api,
            width=1120,
            height=820,
            min_size=(720, 620),
            text_select=True,
        )
        api.window = window
        window.events.closed += server.stop
        # Cocoa/WebKit is selected on macOS; other systems use their native webview.
        webview.start(debug=False, private_mode=False)
    except Exception as exc:
        print(f"네이티브 창을 만들 수 없어 브라우저로 전환합니다: {exc}")
        run_browser_fallback(server)
    finally:
        server.stop()


if __name__ == "__main__":
    main()
