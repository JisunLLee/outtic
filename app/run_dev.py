import subprocess
import sys
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class AppReloader(FileSystemEventHandler):
    """파일 변경을 감지하고 스크립트를 다시 시작하는 클래스"""

    def __init__(self, script_to_run):
        self.script_to_run = script_to_run
        self.process = None
        self.last_reload_time = 0
        self.start_process()

    def start_process(self):
        """스크립트 프로세스를 시작 (이미 실행 중이면 종료 후 재시작)"""
        if self.process:
            print("--- 기존 프로세스를 종료합니다. ---")
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()

        # 현재 활성화된 가상환경의 파이썬을 사용합니다.
        python_executable = sys.executable
        # 절대 경로를 사용하여 실행 파일 위치를 명확히 합니다.
        script_path = os.path.join(os.getcwd(), self.script_to_run)
        self.process = subprocess.Popen([python_executable, script_path])
        print(f"--- '{self.script_to_run}'를 PID {self.process.pid}로 시작했습니다. ---")

    def on_any_event(self, event):
        """파일 수정, 생성, 이동 등 모든 이벤트를 감지하여 .py 파일인 경우 재시작합니다."""
        if event.is_directory:
            return

        # 수정(modified), 생성(created), 이동(moved) 이벤트를 모두 처리 (Atomic Save 대응)
        if event.event_type in ('modified', 'created', 'moved') and event.src_path.endswith(".py"):
            # 너무 짧은 간격으로 재시작되지 않도록 1초 디바운스 적용
            if time.time() - self.last_reload_time < 1.0:
                return
            
            print(f"--- 파일 변경 감지 ({event.event_type}): {event.src_path} ---")
            self.last_reload_time = time.time()
            self.start_process()

if __name__ == "__main__":
    # 스크립트 파일의 위치를 기준으로 프로젝트 루트 경로를 계산하여 작업 디렉토리를 변경합니다.
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    script_to_run = "run_auttic.py" # 실행할 메인 스크립트
    event_handler = AppReloader(script_to_run)

    observer = Observer()
    observer.schedule(event_handler, path=os.getcwd(), recursive=True)  # 절대 경로로 감시 시작
    observer.start()
    print(f"--- './' 폴더의 변경을 감시합니다. 종료하려면 Ctrl+C를 누르세요. ---")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
    observer.join()
    print("--- 감시를 종료합니다. ---")