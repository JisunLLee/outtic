import tkinter as tk
import threading
from pynput import mouse
from PIL import ImageGrab
from global_hotkey_listener import GlobalHotkeyListener
from color_finder import ColorFinder, SearchDirection

class SampleApp:
    def __init__(self, root):
        self.root = root

        self._initialize_attributes()
        self._setup_ui()

        # 핵심 로직 컴포넌트 초기화
        self.color_finder = ColorFinder(sleep_time=self.sleep_time)
        self.global_hotkey_listener = GlobalHotkeyListener(self.click_found_position)
        self.global_hotkey_listener.start()

        # 창 닫기 이벤트 처리
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _initialize_attributes(self):
        """애플리케이션의 모든 속성을 초기화합니다."""
        # 설정값
        self.position1 = (53, 182)
        self.position2 = (713, 647)
        self.color = (0, 204, 204)
        self.color_tolerance = 15
        self.search_direction = SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT
        self.sleep_time = 0.02

        # UI와 연동될 Tkinter 변수
        self.coord1_var = tk.StringVar(value=str(self.position1))
        self.coord2_var = tk.StringVar(value=str(self.position2))
        self.color_var = tk.StringVar(value=str(self.color))
        self.tolerance_var = tk.IntVar(value=self.color_tolerance)
        self.status = tk.StringVar(value="대기 중...")

        # 내부 상태 변수
        self.listener = None
        self.area = 0, 0, 0, 0
        self.area_width = 0
        self.area_height = 0

    def _setup_ui(self):
        """애플리케이션의 UI를 생성하고 배치합니다."""
        self.root.title("샘플 테스터")
        self.root.geometry("330x500")
        self.root.configure(bg="#2e2e2e")

        # UI 위젯 생성
        self._create_coord_entry(0, "1번 좌표", self.coord1_var, 1)
        self._create_coord_entry(1, "2번 좌표", self.coord2_var, 2)

        # 색상 표시 UI (기존 코드의 버그 수정 및 재배치)
        tk.Label(self.root, text="색상", fg="white", bg="#2e2e2e").grid(
            row=2, column=0, padx=10, pady=10, sticky="e"
        )
        tk.Label(self.root, textvariable=self.color_var, width=15, anchor="w", relief="sunken", fg="black", bg="white").grid(
            row=2, column=1
        )
        tk.Button(self.root, text="색상 따기", command=self.start_color_picker).grid(
            row=2, column=2, padx=5
        )

        # 허용 오차 입력 UI
        tk.Label(self.root, text="허용 오차", fg="white", bg="#2e2e2e").grid(
            row=3, column=0, padx=10, pady=10, sticky="e"
        )
        tk.Entry(self.root, textvariable=self.tolerance_var, width=15).grid(
            row=3, column=1, columnspan=2, sticky="ew", padx=5
        )

        # 상태 메시지
        tk.Label(self.root, textvariable=self.status, fg="lightblue", bg="#2e2e2e", anchor="w").grid(
            row=4, column=0, columnspan=3, sticky="w", padx=10, pady=5
        )

        # 초기 영역 계산 및 찾기 버튼
        self.find_button = tk.Button(self.root, text="찾기 (F4)", command=self.click_found_position)
        self.find_button.grid(row=5, column=0, columnspan=3, pady=10, padx=10, sticky="ew")

    def _create_coord_entry(self, row, label_text, coord_var, position_index):
        """좌표 선택을 위한 UI 한 줄을 생성하는 헬퍼 메소드"""
        tk.Label(self.root, text=label_text, fg="white", bg="#2e2e2e").grid(
            row=row, column=0, padx=10, pady=10, sticky="e"
            )
        tk.Label(self.root, textvariable=coord_var, width=15, anchor="w", relief="sunken", fg="black", bg="white").grid(
            row=row, column=1
            )
        tk.Button(self.root, text="좌표 따기", command=lambda: self.start_coordinate_picker(position_index)).grid(
            row=row, column=2, padx=5
            )

    def _start_mouse_listener(self, on_click_callback, status_message):
        """마우스 입력을 감지하는 리스너를 시작하는 공통 헬퍼 메소드"""
        if self.listener and self.listener.is_alive():
            self.status.set("오류: 이미 다른 값을 선택 중입니다.")
            return

        self.status.set(status_message)

        def on_click(x, y, button, pressed):
            if pressed and button == mouse.Button.right:
                # 실제 작업은 제공된 콜백 함수에서 수행 (UI 안전성을 위해 after 사용)
                self.root.after(0, lambda: on_click_callback(x, y))
                return False  # 리스너를 중지합니다.

        def listener_target():
            self.listener = mouse.Listener(on_click=on_click)
            self.listener.run()
            self.listener = None
        
        threading.Thread(target=listener_target, daemon=True).start()

    def start_coordinate_picker(self, position_index):
        """좌표 따기 리스너를 시작합니다."""
        def on_coordinate_click(x, y):
            new_pos = (int(x), int(y))
            if position_index == 1:
                self.position1 = new_pos
                self.coord1_var.set(str(new_pos))
            elif position_index == 2:
                self.position2 = new_pos
                self.coord2_var.set(str(new_pos))
            
            self.status.set(f"{position_index}번 좌표 저장 완료: {new_pos}")
            self._parse_area() # 좌표가 변경되었으므로 영역을 다시 계산

        self._start_mouse_listener(on_coordinate_click, "마우스 오른쪽 클릭으로 좌표를 선택하세요...")

    def start_color_picker(self):
        """색상 따기 리스너를 시작합니다."""
        def on_color_click(x, y):
            # 클릭된 위치의 1x1 스크린샷을 찍어 색상 값을 얻습니다.
            ix, iy = int(x), int(y)
            # .convert('RGB')를 호출하여 반환값이 항상 (R, G, B) 튜플이 되도록 보장합니다.
            # 이렇게 하면 회색조(grayscale) 이미지 등에서 정수 값이 반환되어 발생하는 오류를 방지합니다.
            screenshot = ImageGrab.grab(bbox=(ix, iy, ix + 1, iy + 1)).convert('RGB')
            pixel_color = screenshot.getpixel((0, 0))
            new_color = pixel_color
            
            self.color = new_color
            self.color_var.set(str(new_color))
            self.status.set(f"색상 저장 완료: {new_color}")

        self._start_mouse_listener(on_color_click, "마우스 오른쪽 클릭으로 색상을 선택하세요...")

    def _parse_area(self):
        """두 좌표를 기반으로 사각 영역을 계산합니다. 좌표 순서에 상관없이 동작합니다."""
        x1, y1 = self.position1
        x2, y2 = self.position2
        
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)

        self.area = (left, top, right, bottom)
        self.area_width = right - left
        self.area_height = bottom - top

        print(f"영역 좌표: {self.area}")
        print(f"영역 Width: {self.area_width}")
        print(f"영역 Height: {self.area_height}")

    def click_found_position(self):
        try:
            tolerance = self.tolerance_var.get()
        except tk.TclError:
            self.status.set("오류: 허용 오차는 숫자여야 합니다.")
            return

        abs_x, abs_y = self.color_finder.find_color_in_area(self.area, self.color, tolerance, self.search_direction)

        if abs_x is not None and abs_y is not None:
            # 지정된 좌표 (abs_x, abs_y)를 클릭합니다.
            self.color_finder.click_action(abs_x, abs_y)
        else:
            print("Color not found in the specified area.")

    def on_closing(self):
        """창을 닫을 때 리소스를 안전하게 정리합니다."""
        self.global_hotkey_listener.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    sampleApp = SampleApp(root)
    root.mainloop()