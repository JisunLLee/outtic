from pynput import keyboard

class GlobalHotkeyListener:
    def __init__(self, hotkey_map):
        """
        hotkey_map: {'<shift>+s': start_func, '<esc>': stop_func} 와 같은 딕셔너리.
        pynput.keyboard.GlobalHotKeys를 사용합니다.
        """
        self.hotkey_map = hotkey_map
        self.listener = None

    def start(self):
        """리스너를 시작합니다."""
        if self.listener is None:
            # GlobalHotKeys는 별도 스레드에서 실행되며, 조합키 처리에 매우 안정적입니다.
            self.listener = keyboard.GlobalHotKeys(self.hotkey_map)
            self.listener.start()
            print("--- 전역 단축키 리스너 시작 ---")

    def stop(self):
        """리스너를 중지합니다."""
        if self.listener and self.listener.is_alive():
            self.listener.stop()
            print("--- 전역 단축키 리스너 중지 ---")