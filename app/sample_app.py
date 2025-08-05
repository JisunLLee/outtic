import tkinter as tk
import threading
from pynput import mouse
from global_hotkey_listener import GlobalHotkeyListener
from color_finder import ColorFinder, SearchDirection

class SampleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("샘플 테스터")

        self.root.geometry("330x500")
        self.root.configure(bg="#2e2e2e")

        self.position1 = (53, 182)
        self.position2 = (713, 647)
        self.color = (0, 204, 204)
        
        # 색상 유사도 허용 범위 (0~255, 값이 클수록 더 넓은 범위의 색상을 찾음)
        # 예: 10은 매우 유사한 색상, 50은 눈에 띄게 다른 색상도 포함할 수 있음
        self.color_tolerance = 15
        # 탐색 방향 설정
        self.search_direction = SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT
        self.sleep_time = 0.02

        # 좌표 표시용 변수
        self.coord1 = tk.StringVar(value=str(self.position1))
        self.coord2 = tk.StringVar(value=str(self.position2))

        # 마우스 리스너 참조
        self.listener = None

        # UI 위젯 생성
        self._create_coord_entry(0, "1번 좌표", self.coord1, 1)
        self._create_coord_entry(1, "2번 좌표", self.coord2, 2)
        self._create_coord_entry(3, "색상", self.color, 3)

        # 상태 메시지
        self.status = tk.StringVar(value="대기 중...")
        tk.Label(root, textvariable=self.status, fg="lightblue", bg="#2e2e2e", anchor="w").grid(
            row=2, column=0, columnspan=3, sticky="w", padx=10, pady=5
        )

        self._parse_area()
        self.find_button = tk.Button(root, text="찾기", command=self.click_found_position)
        self.find_button.grid(row=3, column=0, columnspan=3, pady=10, padx=10, sticky="ew")

        self.color_finder = ColorFinder(sleep_time=self.sleep_time)
        # 앱의 활성화 여부와 상관없이 동작하는 전역 키보드 리스너를 시작합니다.
        self.global_hotkey_listener = GlobalHotkeyListener(self.click_found_position)
        self.global_hotkey_listener.start()


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

    def start_coordinate_picker(self, position_index):
        """마우스 오른쪽 클릭으로 좌표를 가져오는 리스너를 시작합니다."""
        if self.listener and self.listener.is_alive():
            self.status.set("오류: 이미 다른 좌표를 선택 중입니다.")
            return

        self.status.set("마우스 오른쪽 클릭으로 좌표를 선택하세요...")

        def on_click(x, y, button, pressed):
            if pressed and button == mouse.Button.right:
                new_pos = (int(x), int(y))

                def update_ui():
                    if position_index == 1:
                        self.position1 = new_pos
                        self.coord1.set(str(new_pos))
                    elif position_index == 2:
                        self.position2 = new_pos
                        self.coord2.set(str(new_pos))
                    
                    self.status.set(f"{position_index}번 좌표 저장 완료: {new_pos}")
                    self._parse_area() # 좌표가 변경되었으므로 영역을 다시 계산합니다.

                self.root.after(0, update_ui)
                return False  # 리스너를 중지합니다.

        def listener_target():
            self.listener = mouse.Listener(on_click=on_click)
            self.listener.run()
            self.listener = None

        threading.Thread(target=listener_target, daemon=True).start()

    def _parse_area(self):
        x1, y1 = self.position1
        x2, y2 = self.position2
        width = x2 - x1
        height = y2 - y1
        self.area = (x1, y1, x2, y2)
        self.area_width = width
        self.area_height = height
        print(f"영역 좌표: {self.area}")
        print(f"영역 Width: {width}")
        print(f"영역 Height: {height}")

    def click_found_position(self):
        abs_x, abs_y = self.color_finder.find_color_in_area(self.area, self.color, self.color_tolerance, self.search_direction)

        if abs_x is not None and abs_y is not None:
            # 지정된 좌표 (abs_x, abs_y)를 클릭합니다.
            self.color_finder.click_action(abs_x, abs_y)
        else:
            print("Color not found in the specified area.")

if __name__ == "__main__":
    root = tk.Tk()
    sampleApp = SampleApp(root)
    root.mainloop()