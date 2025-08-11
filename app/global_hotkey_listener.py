from pynput import keyboard

class GlobalHotkeyListener:
    def __init__(self, hotkey_map):
        """
        hotkey_map: {'shift+esc': start_func, keyboard.Key.esc: stop_func}
        와 같은 형식의 딕셔너리
        """
        self.hotkey_map = hotkey_map
        self.keyboard_listener = None
        self.tab_pressed = False
        print("--- GlobalHotkeyListener ---")

    def _on_press(self, key):
        """전역 단축키가 눌렸을 때 호출됩니다."""
        if key == keyboard.Key.tab:
            self.tab_pressed = True
        
        # Tab + ESC 조합
        if self.tab_pressed and key == keyboard.Key.esc:
            if 'tab+esc' in self.hotkey_map:
                print("[Tab+ESC]")
                self.hotkey_map['tab+esc']()
                return # 단독 ESC 콜백이 실행되지 않도록 함

        # 단독 ESC
        if not self.tab_pressed and key == keyboard.Key.esc:
            if keyboard.Key.esc in self.hotkey_map:
                print("[ESC]")
                self.hotkey_map[keyboard.Key.esc]()

    def _on_release(self, key):
        """키에서 손을 뗐을 때 호출됩니다."""
        if key == keyboard.Key.tab:
            self.tab_pressed = False

    def start(self):
        """시스템 전역의 키보드 입력을 감지하는 리스너를 시작합니다."""
        if self.keyboard_listener is None or not self.keyboard_listener.is_alive():
            from pynput import keyboard
            self.keyboard_listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
            self.keyboard_listener.start()
            print("--- 전역 단축키 리스너 시작 ---")

    def stop(self):
        """전역 키보드 리스너를 중지합니다."""
        if self.keyboard_listener and self.keyboard_listener.is_alive():
            self.keyboard_listener.stop()
            print("--- 전역 키보드 리스너 중지 ---")
    
