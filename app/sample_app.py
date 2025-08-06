import tkinter as tk
import threading
import time
import ast
import queue
import random
import sys
from pynput import mouse
from pynput import keyboard
from PIL import ImageGrab
from color_finder import ColorFinder, SearchDirection
from global_hotkey_listener import GlobalHotkeyListener

class SampleApp:
    def __init__(self, root):
        self.root = root

        self._initialize_attributes()
        self._setup_ui()
        self._process_ui_queue() # UI 업데이트 큐 처리 시작

        # 핵심 로직 컴포넌트 초기화
        self.color_finder = ColorFinder(sleep_time=self.sleep_time)
        self.mouse_controller = mouse.Controller()
        hotkey_map = {
            'shift+esc': self.start_search,
            keyboard.Key.esc: self.stop_search
        }
        self.global_hotkey_listener = GlobalHotkeyListener(hotkey_map)
        self.global_hotkey_listener.start()

        # 창 닫기 이벤트 처리
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _initialize_attributes(self):
        """애플리케이션의 모든 속성을 초기화합니다."""
        # 설정값
        self.position1 = (75, 193)
        self.position2 = (451, 485)
        self.position3 = (805, 704) # 색상 선택 완료 후 클릭할 좌표
        self.position4 = (813, 396) # 색상 선택 실패 시 클릭할 첫 번째 좌표
        self.position5 = (815, 429) # 색상 선택 실패 시 클릭할 두 번째 좌표
        self.color = (0, 204, 204)
        self.color_tolerance = 15
        self.search_direction = SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT
        self.sleep_time = 0.02
        self.fail_click_delay = 0.36 # 색상 찾기 실패 시 클릭 딜레이 (360ms)
        # 실패 시 시퀀스 클릭 횟수
        self.pos4_click_count = 3
        self.pos5_click_count = 2

        # UI와 연동될 Tkinter 변수
        self.coord1_var = tk.StringVar(value=str(self.position1))
        self.coord2_var = tk.StringVar(value=str(self.position2))
        self.coord3_var = tk.StringVar(value=str(self.position3))
        self.coord4_var = tk.StringVar(value=str(self.position4))
        self.coord5_var = tk.StringVar(value=str(self.position5))
        self.color_var = tk.StringVar(value=str(self.color))
        self.tolerance_var = tk.IntVar(value=self.color_tolerance)
        self.fail_delay_var = tk.StringVar(value=str(int(self.fail_click_delay * 1000)))
        self.use_fail_sequence_var = tk.BooleanVar(value=True) # 구역 1 체크박스
        self.use_position5_var = tk.BooleanVar(value=True) # 구역 2 체크박스
        self.pos4_clicks_var = tk.StringVar(value=str(self.pos4_click_count))
        self.pos5_clicks_var = tk.StringVar(value=str(self.pos5_click_count))

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
        self.use_fail_sequence = False
        self.use_position5 = False
        self.fail_sequence_step = 0
        self.fail_sequence_click_count = 0
        self.area_window = None # 영역 확인 창을 위한 참조
        self.ui_queue = queue.Queue() # UI 업데이트 작업을 위한 큐
        # 창 배경색 상태 관리
        self.WINDOW_COLORS = {
            'default': "#2e2e2e",
            'searching': "#5B5B00", # 어두운 노란색
            'flash_success': "#004d00" # 어두운 녹색
        }

        # 초기 영역 계산
        self._parse_area()

    def _setup_ui(self):
        """애플리케이션의 UI를 생성하고 배치합니다."""
        self.root.title("샘플 테스터")

        window_width = 330
        window_height = 480

        # 화면 크기 가져오기
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 창을 좌측 하단에 위치시키기 위한 x, y 좌표 계산
        # 작업 표시줄이나 독(Dock)을 고려하여 약간의 여백(offset)을 줍니다.
        x_coordinate = 0
        y_coordinate = screen_height - window_height - 60

        self.root.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")
        self._update_window_bg('default')

        # --- 설정 프레임 ---
        settings_frame = tk.Frame(self.root, bg="#2e2e2e")
        settings_frame.pack(padx=10, pady=5, fill="x", anchor="n")
        settings_frame.grid_columnconfigure(1, weight=1) # 중앙 위젯이 공간을 차지하도록

        # --- UI 위젯 동적 생성 ---
        self._create_ui_row(settings_frame, 0, "1번 좌표", self.coord1_var,
                            button_text="선택",
                            button_command=lambda: self.start_coordinate_picker(1))

        self._create_ui_row(settings_frame, 1, "2번 좌표", self.coord2_var,
                            button_text="선택",
                            button_command=lambda: self.start_coordinate_picker(2))

        self._create_ui_row(settings_frame, 2, "색상", self.color_var,
                            button_text="선택",
                            button_command=self.start_color_picker)
        self._create_ui_row(settings_frame, 3, "완료", self.coord3_var,
                            button_text="선택",
                            button_command=lambda: self.start_coordinate_picker(3))
        
        self._create_ui_row(settings_frame, 4, "구역 1", self.coord4_var,
                            button_text="선택",
                            button_command=lambda: self.start_coordinate_picker(4),
                            checkbox_var=self.use_fail_sequence_var,
                            checkbox_text="사용")

        self._create_ui_row(settings_frame, 5, "구역 2", self.coord5_var,
                            button_text="선택",
                            button_command=lambda: self.start_coordinate_picker(5),
                            checkbox_var=self.use_position5_var,
                            checkbox_text="사용")

        self._create_ui_row(settings_frame, 6, "구역 1 클릭(번)", self.pos4_clicks_var,
                            widget_type='entry')

        self._create_ui_row(settings_frame, 7, "구역 2 클릭(번)", self.pos5_clicks_var,
                            widget_type='entry')

        self._create_ui_row(settings_frame, 8, "구역선택 딜레이(ms)", self.fail_delay_var,
                            widget_type='entry')

        self._create_ui_row(settings_frame, 9, "색상 오차", self.tolerance_var,
                            widget_type='entry')

        self._create_ui_row(settings_frame, 10, "탐색 방향", self.direction_var,
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

        # --- 영역 확인 버튼 ---
        self.show_area_button = tk.Button(action_frame, text="영역확인", command=self.show_area)
        self.show_area_button.grid(row=0, column=0, sticky="ew", padx=2)

        # --- 찾기 버튼 ---
        self.find_button = tk.Button(action_frame, text="찾기(Shift+ESC)", command=self.toggle_search)
        self.find_button.grid(row=0, column=1, sticky="ew", padx=2)

        # --- 적용하기 단축키 바인딩 ---
        # OS에 따라 다른 단축키를 바인딩합니다.
        if sys.platform == "darwin": # macOS
            self.root.bind("<Command-s>", self._apply_settings)
        else: # Windows, Linux
            self.root.bind("<Control-s>", self._apply_settings)

    def _create_ui_row(self, parent, row, label_text, var, widget_type='label', options=None, button_text=None, button_command=None, checkbox_var=None, checkbox_text=None):
        """설정 UI 한 줄을 생성하는 범용 헬퍼 메서드"""
        tk.Label(parent, text=label_text, fg="white", bg="#2e2e2e").grid(row=row, column=0, padx=(0, 10), pady=5, sticky="e")

        # 중앙 위젯(값 표시/입력)과 체크박스를 담을 프레임
        widget_frame = tk.Frame(parent, bg="#2e2e2e")
        widget_frame.grid(row=row, column=1, sticky="ew")
        widget_frame.grid_columnconfigure(0, weight=1) # 주 위젯이 확장되도록 설정

        if widget_type == 'label':
            tk.Label(widget_frame, textvariable=var, width=15, anchor="w", relief="sunken", fg="black", bg="white").grid(row=0, column=0, sticky="ew")
        elif widget_type == 'entry':
            tk.Entry(widget_frame, textvariable=var, width=15).grid(row=0, column=0, sticky="ew")
        elif widget_type == 'optionmenu' and options:
            option_menu = tk.OptionMenu(widget_frame, var, *options.values())
            option_menu.config(bg="#555555", fg="white", activebackground="#666666", activeforeground="white", highlightthickness=0)
            option_menu["menu"].config(bg="#555555", fg="white")
            option_menu.grid(row=0, column=0, sticky="ew")

        if checkbox_var and checkbox_text:
            cb = tk.Checkbutton(widget_frame, text=checkbox_text, variable=checkbox_var, 
                                bg="#2e2e2e", fg="white", selectcolor="#2e2e2e", 
                                activebackground="#2e2e2e", activeforeground="white", 
                                highlightthickness=0, borderwidth=0)
            cb.grid(row=0, column=1, padx=5)

        if button_text and button_command:
            tk.Button(parent, text=button_text, command=button_command).grid(row=row, column=2, padx=5, sticky="w")

    def _process_ui_queue(self):
        """메인 스레드에서 UI 업데이트 큐를 주기적으로 확인하고 처리합니다."""
        try:
            while True:
                # 큐에서 작업을 가져옵니다. 블로킹하지 않습니다.
                task = self.ui_queue.get_nowait()
                task()  # 가져온 함수를 실행합니다.
        except queue.Empty:
            pass  # 큐가 비어있으면 아무것도 하지 않습니다.
        finally:
            # 100ms 후에 다시 이 함수를 호출하도록 예약합니다.
            self.root.after(100, self._process_ui_queue)

    def start_coordinate_picker(self, position_index):
        """사용자가 마우스를 올려둔 위치의 좌표를 2초 후에 캡처합니다."""
        self.status.set(f"{position_index}번 좌표 지정: 2초 후 마우스 위치를 저장합니다...")

        def grab_coord_after_delay():
            x, y = self.mouse_controller.position
            new_pos = (int(x), int(y))

            if position_index == 1:
                self.coord1_var.set(str(new_pos))
            elif position_index == 2:
                self.coord2_var.set(str(new_pos))
            elif position_index == 3:
                self.coord3_var.set(str(new_pos))
            elif position_index == 4:
                self.coord4_var.set(str(new_pos))
            elif position_index == 5:
                self.coord5_var.set(str(new_pos))

            if position_index == 3:
                status_text = f"완료선택 좌표 저장 완료: {new_pos}"
            elif position_index == 4:
                status_text = f"구역 1 좌표 저장 완료: {new_pos}"
            elif position_index == 5:
                status_text = f"구역 2 좌표 저장 완료: {new_pos}"
            else:
                status_text = f"{position_index}번 좌표 저장 완료: {new_pos}"
            self.status.set(status_text)
            print(f"{position_index}번 좌표: {new_pos}")
            self._flash_window()

        self.root.after(2000, grab_coord_after_delay)

    def start_color_picker(self):
        """사용자가 마우스를 올려둔 위치의 색상을 2초 후에 캡처합니다."""
        self.status.set("색상 지정: 2초 후 마우스 위치의 색상을 캡처합니다...")

        def grab_color_after_delay():
            x, y = self.mouse_controller.position
            ix, iy = int(x), int(y)
            
            screenshot = ImageGrab.grab(bbox=(ix, iy, ix + 1, iy + 1)).convert('RGB')
            pixel_color = screenshot.getpixel((0, 0))
            new_color = pixel_color
            
            self.color_var.set(str(new_color))
            self.status.set(f"색상 저장 완료: {new_color}")
            print(f"캡쳐된 색상: {new_color}")
            self._flash_window()

        self.root.after(2000, grab_color_after_delay)

    def show_area(self):
        """선택된 두 좌표를 기준으로 사각형 영역을 화면에 표시합니다."""
        if self.area_window and self.area_window.winfo_exists():
            self.area_window.destroy()

        # '영역확인' 시 최신 UI 값을 반영하기 위해 설정을 먼저 적용합니다.
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

    def _apply_settings(self, event=None):
        """UI의 설정값들을 실제 애플리케이션 상태에 적용합니다."""
        try:
            self.position1 = ast.literal_eval(self.coord1_var.get())
            self.position2 = ast.literal_eval(self.coord2_var.get())
            self.position3 = ast.literal_eval(self.coord3_var.get())
            self.position4 = ast.literal_eval(self.coord4_var.get())
            self.position5 = ast.literal_eval(self.coord5_var.get())
            self.color = ast.literal_eval(self.color_var.get())
            self.color_tolerance = self.tolerance_var.get()
            # ms 단위의 문자열을 초 단위의 float으로 변환
            self.fail_click_delay = int(self.fail_delay_var.get()) / 1000.0
            self.use_fail_sequence = self.use_fail_sequence_var.get()
            self.use_position5 = self.use_position5_var.get()
            self.pos4_click_count = int(self.pos4_clicks_var.get())
            self.pos5_click_count = int(self.pos5_clicks_var.get())

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

    def _flash_window(self, flash_state='flash_success', duration=150):
        """창 배경색을 잠시 변경하여 시각적 피드백을 줍니다."""
        self._update_window_bg(flash_state)
        self.root.after(duration, lambda: self._update_window_bg('default'))

    def _play_success_sound(self):
        """작업 성공 시 시스템 비프음을 4번 재생합니다."""
        for i in range(4):
            # 200ms 간격으로 벨 소리를 예약하여 "삐-삐-삐-삐-" 효과를 냅니다.
            self.root.after(i * 200, self.root.bell)

    def _update_window_bg(self, state='default'):
        """창의 배경색을 상태에 따라 업데이트합니다."""
        color = self.WINDOW_COLORS.get(state, self.WINDOW_COLORS['default'])
        self.root.configure(bg=color)

    def start_search(self):
        """색상 검색을 시작합니다."""
        def start_search_task():
            if self.is_searching:
                return
            self._apply_settings()
            if "오류" in self.status.get():
                return

            self.fail_sequence_step = 0
            self.fail_sequence_click_count = 0
            self.is_searching = True

            # --- UI 업데이트 ---
            self.status.set("색상 검색 중... (ESC로 중지)")
            self.find_button.config(text="중지 (ESC)")
            self._update_window_bg('searching')
            self.root.bell() # 시작음
            print("--- 색상 검색 ON ---")

            # --- 백그라운드 작업 시작 ---
            self.search_thread = threading.Thread(target=self._search_worker, daemon=True)
            self.search_thread.start()
        
        # UI 업데이트 작업을 큐에 넣습니다.
        self.ui_queue.put(start_search_task)

    def stop_search(self):
        """색상 검색을 중지합니다."""
        if not self.is_searching:
            return
        
        # 검색 스레드를 즉시 중지시키기 위해 플래그는 바로 변경합니다.
        self.is_searching = False

        # UI 업데이트 작업을 큐에 넣습니다.
        def stop_search_task():
            self.find_button.config(text="찾기(Shift+ESC)")
            self.status.set("검색이 중지되었습니다.")
            self._update_window_bg('default')
            self.root.bell()
            self.root.after(150, self.root.bell)
            print("--- 색상 검색 OFF ---")
        self.ui_queue.put(stop_search_task)

    def toggle_search(self):
        """UI 버튼 클릭 시 검색을 토글합니다."""
        if self.is_searching:
            self.stop_search()
        else:
            self.start_search()

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
                # UI 업데이트 작업을 큐에 넣습니다.
                self.ui_queue.put(self._play_success_sound)
                self.ui_queue.put(lambda msg=status_message: self.status.set(msg))
                self.ui_queue.put(lambda: self.find_button.config(text="찾기(Shift+ESC)"))
                self.ui_queue.put(lambda: self._update_window_bg('default'))

                print("--- 색상 발견, 작업 완료, 검색 종료 ---")
                return

            # --- 색상을 찾지 못했을 때의 로직 ---
            if self.use_fail_sequence:
                # 현재 스텝(0: position4, 1: position5)에 따라 클릭할 좌표와 횟수 결정
                if self.fail_sequence_step == 0:
                    target_coord = self.position4
                    coord_num = 4
                    total_clicks_for_step = self.pos4_click_count
                else: # self.fail_sequence_step == 1
                    target_coord = self.position5
                    coord_num = 5
                    total_clicks_for_step = self.pos5_click_count

                # 클릭 실행 여부 결정 (position5는 체크박스 확인)
                should_click = False
                if coord_num == 4:
                    should_click = True
                elif coord_num == 5:
                    should_click = self.use_position5 # position5 사용 여부 확인

                # 조건이 맞으면 클릭 실행
                if should_click and target_coord and target_coord != (0, 0):
                    fail_x, fail_y = target_coord
                    # 상태 메시지 업데이트를 큐에 넣습니다.
                    self.ui_queue.put(lambda c=coord_num, cl=self.fail_sequence_click_count, tc=total_clicks_for_step: 
                                      self.status.set(f"구역 선택: 구역{c-3} ({cl + 1}/{tc})"))
                    
                    # 딜레이 계산 및 클릭
                    final_delay = self.fail_click_delay
                    if self.fail_click_delay > 0:
                        random_offset = random.uniform(-0.1, 0.1)
                        final_delay = self.fail_click_delay + random_offset
                    self.color_finder.click_action(fail_x, fail_y, delay=max(0, final_delay))

                # 현재 스텝의 클릭 카운트 증가
                self.fail_sequence_click_count += 1
                if self.fail_sequence_click_count >= total_clicks_for_step:
                    self.fail_sequence_click_count = 0
                    self.fail_sequence_step = 1 - self.fail_sequence_step # 0 -> 1, 1 -> 0

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
