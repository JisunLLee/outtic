import tkinter as tk
import queue
import sys
from pynput import mouse
from PIL import ImageGrab

from .color_finder import SearchDirection

class AppUI:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self.mouse_controller = mouse.Controller()

        self._initialize_vars()
        self._setup_ui()
        self._process_ui_queue()
        
        # 창 닫기 이벤트 처리
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _initialize_vars(self):
        """UI와 연동될 Tkinter 변수들을 초기화합니다."""
        c = self.controller # 컨트롤러의 초기값으로 변수 초기화
        self.coord1_var = tk.StringVar(value=str(c.position1))
        self.coord2_var = tk.StringVar(value=str(c.position2))
        self.coord3_var = tk.StringVar(value=str(c.position3))
        self.coord4_var = tk.StringVar(value=str(c.position4))
        self.coord5_var = tk.StringVar(value=str(c.position5))
        self.color_var = tk.StringVar(value=str(c.color))
        self.color4_var = tk.StringVar(value=str(c.color4))
        self.color5_var = tk.StringVar(value=str(c.color5))
        self.tolerance_var = tk.IntVar(value=c.color_tolerance)
        self.fail_delay_var = tk.StringVar(value=str(int(c.fail_click_delay * 1000)))
        self.use_fail_sequence_var = tk.BooleanVar(value=True)
        self.use_position5_var = tk.BooleanVar(value=True)
        self.pos4_clicks_var = tk.StringVar(value=str(c.pos4_click_count))
        self.pos5_clicks_var = tk.StringVar(value=str(c.pos5_click_count))
        self.use_same_color4_var = tk.BooleanVar(value=False)
        self.use_same_color5_var = tk.BooleanVar(value=False)
        self.offset3_var = tk.StringVar(value=str(c.click_offset3))
        self.offset4_var = tk.StringVar(value=str(c.click_offset4))
        self.complete_delay_var = tk.StringVar(value=str(int(c.complete_click_delay * 1000)))
        self.offset5_var = tk.StringVar(value=str(c.click_offset5))
        self.max_fail_clicks_var = tk.StringVar(value=str(c.max_fail_clicks))
        self.memo_var = tk.StringVar()

        self.SEARCH_DIRECTION_MAP = {
            SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT.name: "→↓",
            SearchDirection.TOP_RIGHT_TO_BOTTOM_LEFT.name: "←↓",
            SearchDirection.BOTTOM_LEFT_TO_TOP_RIGHT.name: "→↑",
            SearchDirection.BOTTOM_RIGHT_TO_TOP_LEFT.name: "←↑",
        }
        self.direction_var = tk.StringVar(value=self.SEARCH_DIRECTION_MAP[c.search_direction.name])
        self.status = tk.StringVar(value="대기 중...")

        self.area_window = None
        self.marker_windows = []
        self.ui_queue = queue.Queue()
        self.WINDOW_COLORS = {
            'default': "#2e2e2e",
            'searching': "#5B5B00",
            'flash_success': "#004d00"
        }

    def get_all_vars(self):
        """컨트롤러가 UI의 모든 변수를 가져갈 수 있도록 딕셔너리로 반환합니다."""
        return {
            'coord1_var': self.coord1_var,
            'coord2_var': self.coord2_var,
            'coord3_var': self.coord3_var,
            'coord4_var': self.coord4_var,
            'coord5_var': self.coord5_var,
            'color_var': self.color_var,
            'color4_var': self.color4_var,
            'color5_var': self.color5_var,
            'tolerance_var': self.tolerance_var,
            'fail_delay_var': self.fail_delay_var,
            'use_fail_sequence_var': self.use_fail_sequence_var,
            'use_position5_var': self.use_position5_var,
            'pos4_clicks_var': self.pos4_clicks_var,
            'pos5_clicks_var': self.pos5_clicks_var,
            'use_same_color4_var': self.use_same_color4_var,
            'use_same_color5_var': self.use_same_color5_var,
            'offset3_var': self.offset3_var,
            'offset4_var': self.offset4_var,
            'complete_delay_var': self.complete_delay_var,
            'offset5_var': self.offset5_var,
            'max_fail_clicks_var': self.max_fail_clicks_var,
            'memo_var': self.memo_var,
            'direction_var': self.direction_var,
        }

    def _setup_ui(self):
        """애플리케이션의 UI를 생성하고 배치합니다."""
        self.root.title("샘플 테스터")

        window_width = 330
        window_height = 710 # UI 항목 추가로 높이 증가

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x_coordinate = 0
        y_coordinate = screen_height - window_height - 60

        self.root.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")
        self.update_window_bg('default')

        settings_frame = tk.Frame(self.root, bg="#2e2e2e")
        settings_frame.pack(padx=10, pady=5, fill="x", anchor="n")
        settings_frame.grid_columnconfigure(0, weight=1)

        self._create_value_button_row(settings_frame, 0, self.coord1_var, "1번 좌표", lambda: self.start_coordinate_picker(1))
        self._create_value_button_row(settings_frame, 1, self.coord2_var, "2번 좌표", lambda: self.start_coordinate_picker(2))
        self._create_value_button_row(settings_frame, 2, self.color_var, "색상", lambda: self.start_color_picker(0))

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

        complete_frame = self._create_complete_settings_frame(settings_frame)
        complete_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=5, pady=(5,0))

        tk.Label(settings_frame, textvariable=self.status, fg="lightblue", bg="#2e2e2e", anchor="w").grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        area1_frame = self._create_area_settings_frame(settings_frame, 1, self.coord4_var, self.use_fail_sequence_var, self.pos4_clicks_var, self.color4_var, self.use_same_color4_var, self.offset4_var)
        area1_frame.grid(row=6, column=0, columnspan=2, sticky="ew", padx=5, pady=(5,0))

        area2_frame = self._create_area_settings_frame(settings_frame, 2, self.coord5_var, self.use_position5_var, self.pos5_clicks_var, self.color5_var, self.use_same_color5_var, self.offset5_var)
        area2_frame.grid(row=7, column=0, columnspan=2, sticky="ew", padx=5, pady=(5,0))

        self._create_entry_row(settings_frame, 8, "구역 딜레이(ms)", self.fail_delay_var)

        self._create_entry_row(settings_frame, 9, "시도횟수", self.max_fail_clicks_var)

        action_frame = tk.Frame(self.root, bg="#2e2e2e")
        action_frame.pack(pady=10, padx=10, fill="x", anchor="n")
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(1, weight=1)

        self.show_area_button = tk.Button(action_frame, text="영역확인", command=self.show_area)
        self.show_area_button.grid(row=0, column=0, sticky="ew", padx=2)

        self.find_button = tk.Button(action_frame, text="찾기(Shift+ESC)", command=self.controller.toggle_search)
        self.find_button.grid(row=0, column=1, sticky="ew", padx=2)

        if sys.platform == "darwin":
            self.root.bind("<Command-s>", self.controller.apply_settings)
        else:
            self.root.bind("<Control-s>", self.controller.apply_settings)
        
        # --- 메모 입력창 ---
        self.memo_entry = tk.Entry(self.root, textvariable=self.memo_var, bg='#444444', fg='white', insertbackground='white', borderwidth=0, highlightthickness=1, highlightcolor="#555555", highlightbackground="#555555")
        self.memo_entry.pack(fill='x', padx=10, pady=(0, 10))


    def _create_entry_row(self, parent, row, label_text, var):
        tk.Label(parent, text=label_text, fg="white", bg="#2e2e2e").grid(row=row, column=0, padx=(0, 10), pady=5, sticky="e")
        tk.Entry(parent, textvariable=var, width=15).grid(row=row, column=1, sticky="ew")

    def _create_value_button_row(self, parent, row, var, button_text, button_command):
        tk.Label(parent, textvariable=var, width=15, anchor="w", relief="sunken", fg="black", bg="white").grid(row=row, column=0, sticky="ew", pady=2)
        tk.Button(parent, text=button_text, command=button_command).grid(row=row, column=1, padx=5, sticky="ew")

    def _create_complete_settings_frame(self, parent):
        frame = tk.LabelFrame(parent, text="완료 설정", fg="white", bg="#2e2e2e", padx=5, pady=5)
        frame.grid_columnconfigure(0, weight=1)

        self._create_value_button_row(frame, 0, self.coord3_var, "완료 좌표", lambda: self.start_coordinate_picker(3))
        
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
        frame = tk.LabelFrame(parent, text="", fg="white", bg="#2e2e2e", padx=5, pady=5)
        frame.grid_columnconfigure(0, weight=1)

        title_frame = tk.Frame(frame, bg="#2e2e2e")
        title_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))

        coord_row_frame = tk.Frame(frame, bg="#2e2e2e")
        coord_row_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        coord_row_frame.grid_columnconfigure(0, weight=1)
        coord_value_label = tk.Label(coord_row_frame, textvariable=coord_var, width=15, anchor="w", relief="sunken")
        coord_select_button = tk.Button(coord_row_frame, text="좌표", command=lambda: self.start_coordinate_picker(area_index + 3))
        coord_value_label.grid(row=0, column=0, sticky="ew", pady=2)
        coord_select_button.grid(row=0, column=1, padx=5, sticky="ew")

        def toggle_coord_widgets_state():
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
        
        count_offset_frame = tk.Frame(frame, bg="#2e2e2e")
        count_offset_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        count_offset_frame.grid_columnconfigure(1, weight=1)
        count_offset_frame.grid_columnconfigure(3, weight=1)
        tk.Label(count_offset_frame, text="클릭횟수", fg="white", bg="#2e2e2e").grid(row=0, column=0, padx=(0, 5), sticky='e')
        tk.Entry(count_offset_frame, textvariable=clicks_var, width=5).grid(row=0, column=1, sticky="ew")
        tk.Label(count_offset_frame, text="클릭 오차", fg="white", bg="#2e2e2e").grid(row=0, column=2, padx=(10, 5), sticky='e')
        tk.Entry(count_offset_frame, textvariable=offset_var, width=5).grid(row=0, column=3, sticky="ew")

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

        toggle_color_widgets_state()
        toggle_coord_widgets_state()

        return frame

    def _process_ui_queue(self):
        try:
            while True:
                task = self.ui_queue.get_nowait()
                task()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._process_ui_queue)

    def queue_task(self, task):
        """다른 스레드에서 UI 업데이트 작업을 큐에 추가합니다."""
        self.ui_queue.put(task)

    def start_coordinate_picker(self, position_index):
        self.update_status(f"{position_index}번 좌표 지정: 2초 후 마우스 위치를 저장합니다...")

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
            self.update_status(status_text)
            print(f"{position_index}번 좌표: {new_pos}")
            self.flash_window()

        self.root.after(2000, grab_coord_after_delay)

    def start_color_picker(self, color_index=0):
        self.update_status(f"색상 지정({color_index if color_index != 0 else '기본'}): 2초 후 마우스 위치를 캡처합니다...")

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

            self.update_status(status_text)
            print(status_text)
            self.flash_window()

        self.root.after(2000, grab_color_after_delay)

    def show_area(self):
        if self.area_window and self.area_window.winfo_exists():
            self.area_window.destroy()
        for marker in self.marker_windows:
            if marker and marker.winfo_exists():
                marker.destroy()
        self.marker_windows.clear()

        self.controller.apply_settings()
        if "오류" in self.get_status():
            return

        c = self.controller
        left, top, right, bottom = c.area
        width = c.area_width
        height = c.area_height

        self.area_window = tk.Toplevel(self.root)
        self.area_window.overrideredirect(True)
        self.area_window.geometry(f"{width}x{height}+{left}+{top}")
        self.area_window.configure(bg="red", highlightthickness=0)
        self.area_window.attributes('-alpha', 0.4)
        self.area_window.attributes('-topmost', True)
        self.area_window.after(3000, self.area_window.destroy)

        coords_to_show = {
            "1": (c.position1, "#4A90E2"),
            "2": (c.position2, "#4A90E2"),
            "완": (c.position3, "#50E3C2"),
            "G1": (c.position4, "#F5A623"),
            "G2": (c.position5, "#BD10E0")
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

        self.update_status("영역 및 모든 좌표 표시 중...")

    def flash_window(self, flash_state='flash_success', duration=150):
        self.update_window_bg(flash_state)
        self.root.after(duration, lambda: self.update_window_bg('default'))

    def play_sound(self, count=1):
        for i in range(count):
            self.root.after(i * 150, self.root.bell)

    def update_window_bg(self, state='default'):
        color = self.WINDOW_COLORS.get(state, self.WINDOW_COLORS['default'])
        self.root.configure(bg=color)

    def update_status(self, text):
        self.status.set(text)

    def get_status(self):
        return self.status.get()

    def update_button_text(self, text):
        self.find_button.config(text=text)

    def on_closing(self):
        """창을 닫을 때 컨트롤러의 리소스를 정리하고 창을 닫습니다."""
        self.controller.on_closing()
        self.root.destroy()