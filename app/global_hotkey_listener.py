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
        # 현재 눌린 키를 집합에 추가합니다.
        self.pressed_keys.add(key)

        # Shift 키가 눌려있는지 확인합니다.
        is_shift_pressed = any(k in self.pressed_keys for k in {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r})

        # Shift + ESC 조합을 확인합니다.
        if is_shift_pressed and keyboard.Key.esc in self.pressed_keys:
            if 'shift+esc' in self.hotkey_map:
                self.hotkey_map['shift+esc']()
        # Shift가 눌리지 않은 상태에서 ESC 키가 눌렸는지 확인합니다.
        elif key == keyboard.Key.esc and not is_shift_pressed:
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