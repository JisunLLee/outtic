from pynput import keyboard

class GlobalHotkeyListener:
    def __init__(self, hotkey_map):
        """
        hotkey_map: {'<shift>+<esc>': start_func, keyboard.Key.esc: stop_func} 와 같은 딕셔너리
        """
        self.hotkey_map = hotkey_map
        self.listener = None
        self.pressed_keys = set()

    def _on_press(self, key):
        # Shift + ESC 조합 감지
        if key in {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r, keyboard.Key.esc}:
            self.pressed_keys.add(key)
            
            # Shift와 Esc가 모두 눌렸는지 확인
            if any(k in self.pressed_keys for k in {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r}) and keyboard.Key.esc in self.pressed_keys:
                if 'shift+esc' in self.hotkey_map:
                    self.hotkey_map['shift+esc']()

        # 단독 ESC 키 감지 (조합키가 아닐 때만)
        elif key == keyboard.Key.esc and len(self.pressed_keys) == 0:
             if keyboard.Key.esc in self.hotkey_map:
                self.hotkey_map[keyboard.Key.esc]()

    def _on_release(self, key):
        try:
            self.pressed_keys.remove(key)
        except KeyError:
            pass

    def start(self):
        if self.listener is None or not self.listener.is_alive():
            self.listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
            self.listener.start()
            print("--- 전역 단축키 리스너 시작 ---")

    def stop(self):
        if self.listener and self.listener.is_alive():
            self.listener.stop()
            print("--- 전역 단축키 리스너 중지 ---")