import subprocess
import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class AppReloader(FileSystemEventHandler):
    """파일 변경을 감지하고 스크립트를 다시 시작하는 클래스"""

    def __init__(self, script_to_watch):
        self.script_to_watch = script_to_watch
        self.process = None
        self.start_process()

    def start_process(self):
        """스크립트 프로세스를 시작 (이미 실행 중이면 종료 후 재시작)"""
        if self.process:
            print("--- 기존 프로세스를 종료합니다. ---")
            self.process.terminate()
            self.process.wait()

        # 현재 활성화된 가상환경의 파이썬을 사용합니다.
        python_executable = sys.executable
        self.process = subprocess.Popen([python_executable, self.script_to_watch])
        print(f"--- '{self.script_to_watch}'를 PID {self.process.pid}로 시작했습니다. ---")

    def on_modified(self, event):
        """파일이 수정되었을 때 호출됩니다."""
        if not event.is_directory and event.src_path.endswith(self.script_to_watch):
            print(f"--- '{self.script_to_watch}' 파일 변경 감지. 앱을 다시 로드합니다. ---")
            self.start_process()


if __name__ == "__main__":
    script_to_run = "sample_app.py"
    event_handler = AppReloader(script_to_run)

    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)  # 현재 디렉토리 감시
    observer.start()
    print(f"--- '{script_to_run}' 파일의 변경을 감시합니다. 종료하려면 Ctrl+C를 누르세요. ---")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
    observer.join()
    print("--- 감시를 종료합니다. ---")