import tkinter as tk
import threading
import time
import ast
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
        self.mouse_controller = mouse.Controller()
        self.global_hotkey_listener = GlobalHotkeyListener(self.toggle_search)
        self.global_hotkey_listener.start()

        # 창 닫기 이벤트 처리
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _initialize_attributes(self):
        """애플리케이션의 모든 속성을 초기화합니다."""
        # 설정값
        self.position1 = (53, 182)
        self.position2 = (713, 647)
        self.position3 = (0, 0) # 완료 후 클릭할 좌표
        self.color = (0, 204, 204)
        self.color_tolerance = 15
        self.search_direction = SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT
        self.sleep_time = 0.02

        # UI와 연동될 Tkinter 변수
        self.coord1_var = tk.StringVar(value=str(self.position1))
        self.coord2_var = tk.StringVar(value=str(self.position2))
        self.coord3_var = tk.StringVar(value=str(self.position3))
        self.color_var = tk.StringVar(value=str(self.color))
        self.tolerance_var = tk.IntVar(value=self.color_tolerance)

        # UI 표시용 텍스트 맵
        self.SEARCH_DIRECTION_MAP = {
            SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT.name: "→↓",
            SearchDirection.TOP_RIGHT_TO_BOTTOM_LEFT.name: "←↓",
            SearchDirection.BOTTOM_LEFT_TO_TOP_RIGHT.name: "→↑",
            SearchDirection.BOTTOM_RIGHT_TO_TOP_LEFT.name: "←↑",
        }
        self.direction_var = tk.StringVar(value=self.SEARCH_DIRECTION_MAP[self.search_direction.name])
        self.status = tk.StringVar(value="대기 중...")

        # 내부 상태 변수
        self.listener = None
        self.area = (0, 0, 0, 0)
        self.area_width = 0
        self.area_height = 0
        self.is_searching = False
        self.search_thread = None
        self.area_window = None # 영역 확인 창을 위한 참조

        # 초기 영역 계산
        self._parse_area()

    def _setup_ui(self):
        """애플리케이션의 UI를 생성하고 배치합니다."""
        self.root.title("샘플 테스터")
        self.root.geometry("330x500")
        self.root.configure(bg="#2e2e2e")

        # --- 설정 프레임 ---
        settings_frame = tk.Frame(self.root, bg="#2e2e2e")
        settings_frame.pack(padx=10, pady=5, fill="x", anchor="n")
        settings_frame.grid_columnconfigure(1, weight=1) # 중앙 위젯이 공간을 차지하도록

        # --- UI 위젯 동적 생성 ---
        self._create_ui_row(settings_frame, 0, "1번 좌표", self.coord1_var,
                            button_text="좌표 따기",
                            button_command=lambda: self.start_coordinate_picker(1))

        self._create_ui_row(settings_frame, 1, "2번 좌표", self.coord2_var,
                            button_text="좌표 따기",
                            button_command=lambda: self.start_coordinate_picker(2))

        self._create_ui_row(settings_frame, 2, "대상 색상", self.color_var,
                            button_text="대상 지정",
                            button_command=self.start_color_picker)
        self._create_ui_row(settings_frame, 3, "완료선택", self.coord3_var,
                            button_text="좌표 따기",
                            button_command=lambda: self.start_coordinate_picker(3))

        self._create_ui_row(settings_frame, 4, "색상 오차(채널별)", self.tolerance_var,
                            widget_type='entry')

        self._create_ui_row(settings_frame, 5, "탐색 방향", self.direction_var,
                            widget_type='optionmenu',
                            options=self.SEARCH_DIRECTION_MAP)

        # --- 상태 메시지 프레임 ---
        tk.Label(self.root, textvariable=self.status, fg="lightblue", bg="#2e2e2e", anchor="w").pack(
            fill="x", padx=10, pady=5, anchor="n")

        # --- 액션 버튼 프레임 ---
        action_frame = tk.Frame(self.root, bg="#2e2e2e")
        action_frame.pack(pady=10, padx=10, fill="x", anchor="n")
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(1, weight=1)
        action_frame.grid_columnconfigure(2, weight=1)

        # --- 적용 버튼 ---
        self.apply_button = tk.Button(action_frame, text="적용하기", command=self._apply_settings)
        self.apply_button.grid(row=0, column=0, sticky="ew", padx=2)

        # --- 영역 확인 버튼 ---
        self.show_area_button = tk.Button(action_frame, text="영역확인", command=self.show_area)
        self.show_area_button.grid(row=0, column=1, sticky="ew", padx=2)

        # --- 찾기 버튼 ---
        self.find_button = tk.Button(action_frame, text="찾기 (F4)", command=self.toggle_search)
        self.find_button.grid(row=0, column=2, sticky="ew", padx=2)

    def _create_ui_row(self, parent, row, label_text, var, widget_type='label', options=None, button_text=None, button_command=None):
        """설정 UI 한 줄을 생성하는 범용 헬퍼 메서드"""
        tk.Label(parent, text=label_text, fg="white", bg="#2e2e2e").grid(row=row, column=0, padx=(0, 10), pady=5, sticky="e")
        if widget_type == 'label':
            tk.Label(parent, textvariable=var, width=15, anchor="w", relief="sunken", fg="black", bg="white").grid(row=row, column=1, sticky="ew")
        elif widget_type == 'entry':
            tk.Entry(parent, textvariable=var, width=15).grid(row=row, column=1, sticky="ew")
        elif widget_type == 'optionmenu' and options:
            option_menu = tk.OptionMenu(parent, var, *options.values())
            option_menu.config(bg="#555555", fg="white", activebackground="#666666", activeforeground="white", highlightthickness=0)
            option_menu["menu"].config(bg="#555555", fg="white")
            option_menu.grid(row=row, column=1, sticky="ew")
        if button_text and button_command:
            tk.Button(parent, text=button_text, command=button_command).grid(row=row, column=2, padx=5, sticky="w")

    def _start_mouse_listener(self, on_click_callback, status_message):
        """마우스 입력을 감지하는 리스너를 시작하는 공통 헬퍼 메소드"""
        if self.listener and self.listener.is_alive():
            self.status.set("오류: 이미 다른 값을 선택 중입니다.")
            return

        self.status.set(status_message)

        def on_click(x, y, button, pressed):
            if pressed and button == mouse.Button.right:
                self.root.after(0, lambda: on_click_callback(x, y))
                return False

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
                self.coord1_var.set(str(new_pos))
            elif position_index == 2:
                self.coord2_var.set(str(new_pos))
            elif position_index == 3:
                self.coord3_var.set(str(new_pos))
            
            if position_index == 3:
                status_text = f"완료선택 좌표 저장 완료: {new_pos}"
            else:
                status_text = f"{position_index}번 좌표 저장 완료: {new_pos}"
            self.status.set(status_text)

        self._start_mouse_listener(on_coordinate_click, "마우스 오른쪽 클릭으로 좌표를 선택하세요...")

    def start_color_picker(self):
        """사용자가 마우스를 올려둔 위치의 색상을 캡처합니다."""
        self.status.set("3초 후 마우스 위치의 색상을 캡처합니다. 커서를 대상 위에 두세요...")

        def grab_color_after_delay():
            x, y = self.mouse_controller.position
            ix, iy = int(x), int(y)
            
            screenshot = ImageGrab.grab(bbox=(ix, iy, ix + 1, iy + 1)).convert('RGB')
            pixel_color = screenshot.getpixel((0, 0))
            new_color = pixel_color
            
            self.color_var.set(str(new_color))
            self.status.set(f"색상 저장 완료: {new_color}")
            print(f"캡쳐된 색상: {new_color}")

        self.root.after(3000, grab_color_after_delay)

    def show_area(self):
        """선택된 두 좌표를 기준으로 사각형 영역을 화면에 표시합니다."""
        if self.area_window and self.area_window.winfo_exists():
            self.area_window.destroy()

        self._apply_settings()
        if "오류" in self.status.get():
            return

        left, top, right, bottom = self.area
        width = self.area_width
        height = self.area_height

        self.area_window = tk.Toplevel(self.root)
        self.area_window.overrideredirect(True)
        self.area_window.geometry(f"{width}x{height}+{left}+{top}")
        self.area_window.configure(bg="red", highlightthickness=0)
        self.area_window.attributes('-alpha', 0.4)
        self.area_window.attributes('-topmost', True)

        self.status.set(f"영역 표시: ({left},{top}) - ({right},{bottom})")
        self.area_window.after(3000, self.area_window.destroy)

    def _apply_settings(self):
        """UI의 설정값들을 실제 애플리케이션 상태에 적용합니다."""
        try:
            self.position1 = ast.literal_eval(self.coord1_var.get())
            self.position2 = ast.literal_eval(self.coord2_var.get())
            self.position3 = ast.literal_eval(self.coord3_var.get())
            self.color = ast.literal_eval(self.color_var.get())
            self.color_tolerance = self.tolerance_var.get()

            selected_display_name = self.direction_var.get()
            reversed_direction_map = {v: k for k, v in self.SEARCH_DIRECTION_MAP.items()}
            direction_name = reversed_direction_map.get(selected_display_name)
            if direction_name:
                self.search_direction = SearchDirection[direction_name]

            self._parse_area()
            self.status.set("설정이 성공적으로 적용되었습니다.")
            print("--- Settings Applied ---")

        except (ValueError, SyntaxError) as e:
            error_msg = f"설정 적용 오류: 입력값을 확인하세요. ({e})"
            self.status.set(error_msg)
        except tk.TclError:
            self.status.set("설정 적용 오류: 허용 오차는 숫자여야 합니다.")

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

    def _play_success_sound(self):
        """작업 성공 시 시스템 비프음을 3번 재생합니다."""
        for i in range(4):
            # 150ms 간격으로 벨 소리를 예약하여 "삐-삐-삐" 효과를 냅니다.
            self.root.after(i * 150, self.root.bell)

    def toggle_search(self):
        """색상 검색을 시작하거나 중지하는 토글 메서드입니다."""
        if self.is_searching:
            self.is_searching = False
            self.find_button.config(text="찾기 (F4)")
            self.status.set("검색이 중지되었습니다.")
            print("--- 색상 검색 OFF ---")
            return

        self._apply_settings()
        if "오류" in self.status.get():
            return

        self.is_searching = True
        self.status.set("색상 검색 중... (F4로 중지)")
        self.find_button.config(text="중지 (F4)")
        print("--- 색상 검색 ON ---")

        self.search_thread = threading.Thread(target=self._search_worker, daemon=True)
        self.search_thread.start()

    def _search_worker(self):
        """(스레드 워커) 색상을 주기적으로 검색하고, 찾으면 클릭 후 종료합니다."""
        while self.is_searching:
            abs_x, abs_y = self.color_finder.find_color_in_area(self.area, self.color, self.color_tolerance, self.search_direction)

            if abs_x is not None and abs_y is not None:
                self.color_finder.click_action(abs_x, abs_y)

                if self.position3 != (0, 0):
                    time.sleep(0.1)
                    comp_x, comp_y = self.position3
                    self.color_finder.click_action(comp_x, comp_y)
                    status_message = f"색상 클릭 후 완료선택({comp_x},{comp_y}) 클릭"
                else:
                    status_message = f"색상 발견 및 클릭 완료: ({abs_x}, {abs_y})"

                self.is_searching = False
                self.root.after(0, self._play_success_sound)
                self.root.after(0, lambda msg=status_message: self.status.set(msg))
                self.root.after(0, lambda: self.find_button.config(text="찾기 (F4)"))
                print("--- 색상 발견, 작업 완료, 검색 종료 ---")
                return

            time.sleep(0.1)

    def on_closing(self):
        """창을 닫을 때 리소스를 안전하게 정리합니다."""
        self.is_searching = False
        self.global_hotkey_listener.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    sampleApp = SampleApp(root)
    root.mainloop()
