from pynput import keyboard

class GlobalHotkeyListener:
    def __init__(self, callback):
        self.callback = callback
        self.keyboard_listener = None
        print("--- GlobalHotkeyListener ---")

    def _on_press(self, key):
        """전역 단축키가 눌렸을 때 호출됩니다."""
        try:
            if key == keyboard.Key.f4:
                print("[F4]")
                self.callback()
        except AttributeError:
            # 특수 키가 아닌 일반 키 (예: 'a', 'b')는 .char 속성을 가집니다.
            pass

    def start(self):
        """시스템 전역의 키보드 입력을 감지하는 리스너를 시작합니다."""
        if self.keyboard_listener is None or not self.keyboard_listener.is_alive():
            from pynput import keyboard
            self.keyboard_listener = keyboard.Listener(on_press=self._on_press)
            self.keyboard_listener.start()
            print("--- 전역 단축키 리스너 시작 ---")

    def stop(self):
        """전역 키보드 리스너를 중지합니다."""
        if self.keyboard_listener and self.keyboard_listener.is_alive():
            self.keyboard_listener.stop()
            print("--- 전역 키보드 리스너 중지 ---")
    
