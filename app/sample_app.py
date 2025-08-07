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
            keyboard.Key.esc: lambda: self.stop_search() # 기본 인자로 호출하기 위해 람다 사용
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
        self.color4 = self.color # 구역 1에서 찾을 색상, 기본 색상으로 초기화
        self.color5 = self.color # 구역 2에서 찾을 색상, 기본 색상으로 초기화
        self.color_tolerance = 15
        self.search_direction = SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT
        self.sleep_time = 0.02
        self.fail_click_delay = 0.50 # 색상 찾기 실패 시 클릭 딜레이 (500ms)
        self.complete_click_delay = 0.02 # 완료 클릭 딜레이
        # 실패 시 시퀀스 클릭 횟수
        self.pos4_click_count = 3
        self.pos5_click_count = 2
        # 클릭 위치 오차
        self.click_offset3 = 0
        self.click_offset4 = 5
        self.click_offset5 = 5
        # 자동 중단 설정
        self.max_fail_clicks = 525

        # UI와 연동될 Tkinter 변수
        self.coord1_var = tk.StringVar(value=str(self.position1))
        self.coord2_var = tk.StringVar(value=str(self.position2))
        self.coord3_var = tk.StringVar(value=str(self.position3))
        self.coord4_var = tk.StringVar(value=str(self.position4))
        self.coord5_var = tk.StringVar(value=str(self.position5))
        self.color_var = tk.StringVar(value=str(self.color))
        self.color4_var = tk.StringVar(value=str(self.color4))
        self.color5_var = tk.StringVar(value=str(self.color5))
        self.tolerance_var = tk.IntVar(value=self.color_tolerance)
        self.fail_delay_var = tk.StringVar(value=str(int(self.fail_click_delay * 1000)))
        self.use_fail_sequence_var = tk.BooleanVar(value=True) # 구역 1 체크박스
        self.use_position5_var = tk.BooleanVar(value=True) # 구역 2 체크박스
        self.pos4_clicks_var = tk.StringVar(value=str(self.pos4_click_count))
        self.pos5_clicks_var = tk.StringVar(value=str(self.pos5_click_count))
        self.use_same_color4_var = tk.BooleanVar(value=False) # 체크 시 구역1 색상 사용
        self.use_same_color5_var = tk.BooleanVar(value=False) # 체크 시 구역2 색상 사용
        self.offset3_var = tk.StringVar(value=str(self.click_offset3))
        self.offset4_var = tk.StringVar(value=str(self.click_offset4))
        self.complete_delay_var = tk.StringVar(value=str(int(self.complete_click_delay * 1000)))
        self.offset5_var = tk.StringVar(value=str(self.click_offset5))

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
        self.next_color_after_pos4 = self.color # 구역 1 시퀀스 후 찾을 색상
        self.next_color_after_pos5 = self.color # 구역 2 시퀀스 후 찾을 색상
        self.current_search_color = self.color # 현재 검색 대상 색상
        self.fail_sequence_step = 0
        self.fail_sequence_click_count = 0
        self.total_fail_clicks = 0 # 실패 시퀀스 총 클릭 횟수 카운터
        self.fail_sequence_target_coord = None # 현재 시퀀스 스텝에서 클릭할 고정된 랜덤 좌표
        self.area_window = None # 영역 확인 창을 위한 참조
        self.marker_windows = [] # 좌표 마커 창들을 위한 참조
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
        window_height = 650

        # 화면 크기 가져오기
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 창을 좌측 하단에 위치시키기 위한 x, y 좌표 계산
        x_coordinate = 0
        y_coordinate = screen_height - window_height - 60

        self.root.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")
        self._update_window_bg('default')

        # --- 설정 프레임 ---
        settings_frame = tk.Frame(self.root, bg="#2e2e2e")
        settings_frame.pack(padx=10, pady=5, fill="x", anchor="n")
        settings_frame.grid_columnconfigure(0, weight=1) # 값 표시 레이블이 확장되도록

        # --- UI 위젯 동적 생성 ---
        self._create_value_button_row(settings_frame, 0, self.coord1_var, "1번 좌표", lambda: self.start_coordinate_picker(1))
        self._create_value_button_row(settings_frame, 1, self.coord2_var, "2번 좌표", lambda: self.start_coordinate_picker(2))
        self._create_value_button_row(settings_frame, 2, self.color_var, "색상", lambda: self.start_color_picker(0))

        # --- 색상 오차, 탐색 방향 설정 ---
        general_settings_frame = tk.Frame(settings_frame, bg="#2e2e2e")
        general_settings_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
        general_settings_frame.grid_columnconfigure(1, weight=1)
        tk.Label(general_settings_frame, text="색상 오차", fg="white", bg="#2e2e2e").grid(row=0, column=0, padx=(0, 5))
        tk.Entry(general_settings_frame, textvariable=self.tolerance_var, width=5).grid(row=0, column=1, sticky="ew")
        tk.Label(general_settings_frame, text="탐색 방향", fg="white", bg="#2e2e2e").grid(row=0, column=2, padx=(10, 5))
        option_menu = tk.OptionMenu(general_settings_frame, self.direction_var, *self.SEARCH_DIRECTION_MAP.values())
        option_menu.config(bg="#555555", fg="white", activebackground="#666666", activeforeground="white", highlightthickness=0)
        option_menu["menu"].config(bg="#555555", fg="white")
        option_menu.grid(row=0, column=3, sticky="w")

        # --- 완료 설정 프레임 ---
        complete_frame = self._create_complete_settings_frame(settings_frame)
        complete_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=5, pady=(5,0))

        # --- 상태 메시지 ---
        tk.Label(settings_frame, textvariable=self.status, fg="lightblue", bg="#2e2e2e", anchor="w").grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        # --- 구역 1, 2 설정 프레임 ---
        area1_frame = self._create_area_settings_frame(settings_frame, 1, self.coord4_var, self.use_fail_sequence_var, self.pos4_clicks_var, self.color4_var, self.use_same_color4_var, self.offset4_var)
        area1_frame.grid(row=6, column=0, columnspan=2, sticky="ew", padx=5, pady=(5,0))

        area2_frame = self._create_area_settings_frame(settings_frame, 2, self.coord5_var, self.use_position5_var, self.pos5_clicks_var, self.color5_var, self.use_same_color5_var, self.offset5_var)
        area2_frame.grid(row=7, column=0, columnspan=2, sticky="ew", padx=5, pady=(5,0))

        # --- 구역선택 딜레이 ---
        self._create_entry_row(settings_frame, 8, "구역선택 딜레이(ms)", self.fail_delay_var)

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
        if sys.platform == "darwin":
            self.root.bind("<Command-s>", self._apply_settings)
        else:
            self.root.bind("<Control-s>", self._apply_settings)

    def _create_entry_row(self, parent, row, label_text, var):
        """레이블과 입력창으로 구성된 한 줄의 UI를 생성합니다."""
        tk.Label(parent, text=label_text, fg="white", bg="#2e2e2e").grid(row=row, column=0, padx=(0, 10), pady=5, sticky="e")
        tk.Entry(parent, textvariable=var, width=15).grid(row=row, column=1, sticky="ew")

    def _create_value_button_row(self, parent, row, var, button_text, button_command):
        """값 표시 레이블과 액션 버튼으로 구성된 한 줄의 UI를 생성합니다."""
        tk.Label(parent, textvariable=var, width=15, anchor="w", relief="sunken", fg="black", bg="white").grid(row=row, column=0, sticky="ew", pady=2)
        tk.Button(parent, text=button_text, command=button_command).grid(row=row, column=1, padx=5, sticky="ew")

    def _create_complete_settings_frame(self, parent):
        """'완료' 설정을 위한 UI 그룹(LabelFrame)을 생성합니다."""
        frame = tk.LabelFrame(parent, text="완료 설정", fg="white", bg="#2e2e2e", padx=5, pady=5)
        frame.grid_columnconfigure(0, weight=1)

        self._create_value_button_row(frame, 0, self.coord3_var, "완료 좌표", lambda: self.start_coordinate_picker(3))
        
        # 클릭 오차와 딜레이를 한 줄에 배치
        offset_delay_frame = tk.Frame(frame, bg="#2e2e2e")
        offset_delay_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        offset_delay_frame.grid_columnconfigure(1, weight=1)
        offset_delay_frame.grid_columnconfigure(3, weight=1)
        tk.Label(offset_delay_frame, text="클릭 오차", fg="white", bg="#2e2e2e").grid(row=0, column=0, padx=(0, 5), sticky='e')
        tk.Entry(offset_delay_frame, textvariable=self.offset3_var, width=5).grid(row=0, column=1, sticky="ew")
        tk.Label(offset_delay_frame, text="클릭 딜레이", fg="white", bg="#2e2e2e").grid(row=0, column=2, padx=(10, 5), sticky='e')
        tk.Entry(offset_delay_frame, textvariable=self.complete_delay_var, width=5).grid(row=0, column=3, sticky="ew")
        
        return frame

    def _create_area_settings_frame(self, parent, area_index, coord_var, use_var, clicks_var, color_var, use_same_color_var, offset_var):
        """'구역' 설정을 위한 UI 그룹(LabelFrame)을 생성합니다."""
        frame = tk.LabelFrame(parent, text="", fg="white", bg="#2e2e2e", padx=5, pady=5)
        frame.grid_columnconfigure(0, weight=1)

        # --- 커스텀 타이틀 바: [v] 구역 1 ---
        title_frame = tk.Frame(frame, bg="#2e2e2e")
        title_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))

        # Row 1: 좌표 (수동 생성하여 상태 제어)
        coord_row_frame = tk.Frame(frame, bg="#2e2e2e")
        coord_row_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        coord_row_frame.grid_columnconfigure(0, weight=1)
        coord_value_label = tk.Label(coord_row_frame, textvariable=coord_var, width=15, anchor="w", relief="sunken")
        coord_select_button = tk.Button(coord_row_frame, text="좌표", command=lambda: self.start_coordinate_picker(area_index + 3))
        coord_value_label.grid(row=0, column=0, sticky="ew", pady=2)
        coord_select_button.grid(row=0, column=1, padx=5, sticky="ew")

        def toggle_coord_widgets_state():
            """'사용' 체크박스 상태에 따라 좌표 위젯의 상태를 변경합니다."""
            if use_var.get():
                coord_value_label.config(bg='white', fg='black')
                coord_select_button.config(state='normal')
            else:
                coord_value_label.config(bg='#555555', fg='#999999')
                coord_select_button.config(state='disabled')

        tk.Checkbutton(title_frame, variable=use_var, text="", command=toggle_coord_widgets_state,
                                bg="#2e2e2e", fg="white", selectcolor="#2e2e2e",
                                activebackground="#2e2e2e", activeforeground="white",
                                highlightthickness=0, borderwidth=0).pack(side="left")
        tk.Label(title_frame, text=f"구역 {area_index}", fg="white", bg="#2e2e2e").pack(side="left")
        
        # Row 2: 클릭횟수와 클릭 오차를 한 줄에 배치
        count_offset_frame = tk.Frame(frame, bg="#2e2e2e")
        count_offset_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        count_offset_frame.grid_columnconfigure(1, weight=1)
        count_offset_frame.grid_columnconfigure(3, weight=1)
        tk.Label(count_offset_frame, text="클릭횟수", fg="white", bg="#2e2e2e").grid(row=0, column=0, padx=(0, 5), sticky='e')
        tk.Entry(count_offset_frame, textvariable=clicks_var, width=5).grid(row=0, column=1, sticky="ew")
        tk.Label(count_offset_frame, text="클릭 오차", fg="white", bg="#2e2e2e").grid(row=0, column=2, padx=(10, 5), sticky='e')
        tk.Entry(count_offset_frame, textvariable=offset_var, width=5).grid(row=0, column=3, sticky="ew")

        # Row 3: 찾을색상 (커스텀 레이아웃)
        color_row = tk.Frame(frame, bg="#2e2e2e")
        color_row.grid(row=3, column=0, columnspan=2, sticky="ew")
        color_row.grid_columnconfigure(1, weight=1)

        color_value_label = tk.Label(color_row, textvariable=color_var, width=15, anchor="w", relief="sunken")
        color_select_button = tk.Button(color_row, text="색상", command=lambda: self.start_color_picker(area_index + 3))

        def toggle_color_widgets_state():
            if use_same_color_var.get():
                color_value_label.config(bg='white', fg='black')
                color_select_button.config(state='normal')
            else:
                color_value_label.config(bg='#555555', fg='#999999')
                color_select_button.config(state='disabled')

        color_checkbox = tk.Checkbutton(color_row, variable=use_same_color_var, command=toggle_color_widgets_state,
                                        bg="#2e2e2e", selectcolor="#2e2e2e", activebackground="#2e2e2e",
                                        highlightthickness=0, borderwidth=0)
        
        color_checkbox.grid(row=0, column=0)
        color_value_label.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        color_select_button.grid(row=0, column=2)

        # 초기 상태를 설정하기 위해 함수들을 호출합니다.
        toggle_color_widgets_state()
        toggle_coord_widgets_state()

        return frame

    def _process_ui_queue(self):
        """메인 스레드에서 UI 업데이트 큐를 주기적으로 확인하고 처리합니다."""
        try:
            while True:
                task = self.ui_queue.get_nowait()
                task()
        except queue.Empty:
            pass
        finally:
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

    def start_color_picker(self, color_index=0):
        """사용자가 마우스를 올려둔 위치의 색상을 2초 후에 캡처합니다."""
        self.status.set(f"색상 지정({color_index if color_index != 0 else '기본'}): 2초 후 마우스 위치를 캡처합니다...")

        def grab_color_after_delay():
            x, y = self.mouse_controller.position
            ix, iy = int(x), int(y)
            
            screenshot = ImageGrab.grab(bbox=(ix, iy, ix + 1, iy + 1)).convert('RGB')
            pixel_color = screenshot.getpixel((0, 0))
            new_color = pixel_color

            if color_index == 0:
                self.color_var.set(str(new_color))
                status_text = f"기본 색상 저장 완료: {new_color}"
            elif color_index == 4:
                self.color4_var.set(str(new_color))
                status_text = f"구역 1 색상 저장 완료: {new_color}"
            elif color_index == 5:
                self.color5_var.set(str(new_color))
                status_text = f"구역 2 색상 저장 완료: {new_color}"

            self.status.set(status_text)
            print(status_text)
            self._flash_window()

        self.root.after(2000, grab_color_after_delay)

    def show_area(self):
        """선택된 두 좌표를 기준으로 사각형 영역과 모든 개별 좌표를 화면에 표시합니다."""
        if self.area_window and self.area_window.winfo_exists():
            self.area_window.destroy()
        for marker in self.marker_windows:
            if marker and marker.winfo_exists():
                marker.destroy()
        self.marker_windows.clear()

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
        self.area_window.after(3000, self.area_window.destroy)

        coords_to_show = {
            "1": (self.position1, "#4A90E2"),
            "2": (self.position2, "#4A90E2"),
            "완": (self.position3, "#50E3C2"),
            "G1": (self.position4, "#F5A623"),
            "G2": (self.position5, "#BD10E0")
        }
        marker_size = 20
        for name, (pos, color) in coords_to_show.items():
            x, y = pos
            if x == 0 and y == 0: continue

            marker = tk.Toplevel(self.root)
            marker.overrideredirect(True)
            marker.geometry(f"{marker_size}x{marker_size}+{x - marker_size//2}+{y - marker_size//2}")
            marker.configure(bg=color, highlightthickness=1, highlightbackground="white")
            marker.attributes('-alpha', 0.7)
            marker.attributes('-topmost', True)
            tk.Label(marker, text=name, bg=color, fg="white", font=("Helvetica", 8, "bold")).pack(expand=True, fill='both')
            marker.after(3000, marker.destroy)
            self.marker_windows.append(marker)

        self.status.set("영역 및 모든 좌표 표시 중...")

    def _apply_settings(self, event=None):
        """UI의 설정값들을 실제 애플리케이션 상태에 적용합니다."""
        try:
            self.position1 = ast.literal_eval(self.coord1_var.get())
            self.position2 = ast.literal_eval(self.coord2_var.get())
            self.position3 = ast.literal_eval(self.coord3_var.get())
            self.position4 = ast.literal_eval(self.coord4_var.get())
            self.position5 = ast.literal_eval(self.coord5_var.get())
            self.color = ast.literal_eval(self.color_var.get())
            self.color4 = ast.literal_eval(self.color4_var.get())
            self.color5 = ast.literal_eval(self.color5_var.get())
            self.color_tolerance = self.tolerance_var.get()
            # ms 단위의 문자열을 초 단위의 float으로 변환
            self.fail_click_delay = int(self.fail_delay_var.get()) / 1000.0
            self.use_fail_sequence = self.use_fail_sequence_var.get()
            self.use_position5 = self.use_position5_var.get()
            self.pos4_click_count = int(self.pos4_clicks_var.get())
            self.pos5_click_count = int(self.pos5_clicks_var.get())
            self.click_offset3 = int(self.offset3_var.get())
            self.click_offset4 = int(self.offset4_var.get())
            self.click_offset5 = int(self.offset5_var.get())
            self.complete_click_delay = int(self.complete_delay_var.get()) / 1000.0

            # '색상' 체크박스 상태에 따라 다음에 찾을 색상을 미리 결정합니다.
            # 체크하면(True) 구역별 색상 사용, 체크 해제하면(False) 기본 색상 사용.
            if self.use_same_color4_var.get():
                self.next_color_after_pos4 = self.color4
            else:
                self.next_color_after_pos4 = self.color
            if self.use_same_color5_var.get():
                self.next_color_after_pos5 = self.color5
            else:
                self.next_color_after_pos5 = self.color

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

            self.fail_sequence_target_coord = None # 검색 시작 시 시퀀스 목표 좌표 초기화
            self.current_search_color = self.color # 검색 시작 시 항상 기본 색상으로 초기화
            self.fail_sequence_step = 0
            self.fail_sequence_click_count = 0
            self.total_fail_clicks = 0 # 총 실패 클릭 카운터 초기화
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

    def stop_search(self, message="검색이 중지되었습니다.", auto_stopped=False):
        """색상 검색을 중지합니다."""
        if not self.is_searching:
            return
        
        # 검색 스레드를 즉시 중지시키기 위해 플래그는 바로 변경합니다.
        self.is_searching = False

        # UI 업데이트 작업을 큐에 넣습니다.
        def stop_search_task():
            self.find_button.config(text="찾기(Shift+ESC)")
            self.status.set(message)
            self._update_window_bg('default')

            if auto_stopped:
                # 자동 중단 시 3번 울림
                for i in range(3):
                    self.root.after(i * 150, self.root.bell)
            else:
                # 수동 중단 시 2번 울림
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
            abs_x, abs_y = self.color_finder.find_color_in_area(self.area, self.current_search_color, self.color_tolerance, self.search_direction)

            if abs_x is not None and abs_y is not None:
                self.color_finder.click_action(abs_x, abs_y)

                if self.position3 != (0, 0):
                    time.sleep(0.1)
                    comp_x, comp_y = self.position3

                    # '완료' 클릭에 대한 오차 계산
                    final_comp_x, final_comp_y = comp_x, comp_y
                    if self.click_offset3 > 0:
                        offset_x = random.randint(-self.click_offset3, self.click_offset3)
                        offset_y = random.randint(-self.click_offset3, self.click_offset3)
                        final_comp_x += offset_x
                        final_comp_y += offset_y
                    self.color_finder.click_action(final_comp_x, final_comp_y, delay=self.complete_click_delay)
                    status_message = f"색상 클릭 후 완료선택({final_comp_x},{final_comp_y}) 클릭"
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
                # 현재 스텝(0: position4, 1: position5)에 따라 클릭할 좌표, 횟수, 오차 결정
                if self.fail_sequence_step == 0:
                    target_coord = self.position4
                    target_offset = self.click_offset4
                    coord_num = 4
                    total_clicks_for_step = self.pos4_click_count
                else: # self.fail_sequence_step == 1
                    target_coord = self.position5
                    target_offset = self.click_offset5
                    coord_num = 5
                    total_clicks_for_step = self.pos5_click_count

                # 현재 스텝의 첫 번째 클릭인 경우에만 새로운 랜덤 좌표를 계산합니다.
                if self.fail_sequence_click_count == 0:
                    base_x, base_y = target_coord
                    final_x, final_y = base_x, base_y
                    if target_offset > 0:
                        offset_x = random.randint(-target_offset, target_offset)
                        offset_y = random.randint(-target_offset, target_offset)
                        final_x += offset_x
                        final_y += offset_y
                    self.fail_sequence_target_coord = (final_x, final_y)

                # 클릭 실행 여부 결정 (position5는 체크박스 확인)
                should_click = False
                if coord_num == 4:
                    should_click = True
                elif coord_num == 5:
                    should_click = self.use_position5 # position5 사용 여부 확인

                # 조건이 맞으면 클릭 실행
                if should_click and self.fail_sequence_target_coord and self.fail_sequence_target_coord != (0, 0):
                    fail_x, fail_y = self.fail_sequence_target_coord
                    # 상태 메시지 업데이트를 큐에 넣습니다.
                    self.ui_queue.put(lambda c=coord_num, cl=self.fail_sequence_click_count, tc=total_clicks_for_step, total=self.total_fail_clicks:
                                      self.status.set(f"구역 선택: 구역{c-3} ({cl + 1}/{tc}) | 총 {total + 1}/{self.max_fail_clicks}"))
                    
                    # 딜레이 계산 및 클릭
                    final_delay = self.fail_click_delay
                    if self.fail_click_delay > 0:
                        random_offset = random.uniform(-0.1, 0.1)
                        final_delay = self.fail_click_delay + random_offset
                    self.color_finder.click_action(fail_x, fail_y, delay=max(0, final_delay))

                    # 자동 중단 로직
                    self.total_fail_clicks += 1
                    if self.total_fail_clicks >= self.max_fail_clicks:
                        print(f"--- 최대 실패 클릭 횟수({self.max_fail_clicks})에 도달하여 자동 중단합니다. ---")
                        self.ui_queue.put(lambda: self.stop_search(message="최대 클릭 도달, 자동 중단됨", auto_stopped=True))
                        return # 워커 스레드 종료

                # 현재 스텝의 클릭 카운트 증가
                self.fail_sequence_click_count += 1
                if self.fail_sequence_click_count >= total_clicks_for_step:
                    self.fail_sequence_target_coord = None # 다음 스텝을 위해 랜덤 좌표 초기화
                    self.fail_sequence_click_count = 0
                    self.fail_sequence_step = 1 - self.fail_sequence_step # 0 -> 1, 1 -> 0

                    # 방금 완료된 스텝에 따라 다음 검색 색상을 업데이트합니다.
                    if self.fail_sequence_step == 1: # 0->1로 변경된 직후 (구역 1 클릭 완료)
                        self.current_search_color = self.next_color_after_pos4
                        print(f"다음 검색 색상 변경 (구역1 규칙): {self.current_search_color}")
                    else: # 1->0으로 변경된 직후 (구역 2 클릭 완료)
                        self.current_search_color = self.next_color_after_pos5
                        print(f"다음 검색 색상 변경 (구역2 규칙): {self.current_search_color}")


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
