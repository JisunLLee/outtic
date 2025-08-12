import tkinter as tk
from tkinter import ttk
import queue

from .color_finder import SearchDirection

class AppUI:
    """
    애플리케이션의 모든 UI 요소 생성과 배치를 담당하는 클래스입니다.
    """
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self.area_marker_windows = []
        self.point_marker_windows = []
        self.ui_queue = queue.Queue()
        self.area_vars = {}
        self._initialize_vars()
        self._setup_ui()
        self._process_ui_queue()

    def _initialize_vars(self):
        """UI에 사용될 Tkinter 변수들을 초기화합니다."""
        c = self.controller
        self.color_tolerance_var = tk.StringVar(value="15") # 색상 오차
        self.color_area_tolerance_var = tk.StringVar(value="5") # 색영역 오차
        self.complete_delay_var = tk.StringVar(value="2") # 완료 딜레이
        self.p1_var = tk.StringVar(value=str(c.p1))
        self.p2_var = tk.StringVar(value=str(c.p2))
        self.color_var = tk.StringVar(value=str(c.color))
        self.area_delay_var = tk.StringVar(value="30") # 구역 딜레이
        self.complete_coord_var = tk.StringVar(value=str(c.complete_coord)) # 완료 좌표

        # 탐색 방향 Enum과 UI 표시 문자열을 매핑합니다.
        self.SEARCH_DIRECTION_MAP = {
            SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT: "→↓",
            SearchDirection.TOP_RIGHT_TO_BOTTOM_LEFT: "←↓",
            SearchDirection.BOTTOM_LEFT_TO_TOP_RIGHT: "→↑",
            SearchDirection.BOTTOM_RIGHT_TO_TOP_LEFT: "←↑",
        }
        self.direction_var = tk.StringVar(value=self.SEARCH_DIRECTION_MAP[c.search_direction])
        self.use_sequence_var = tk.BooleanVar(value=True)
        self.total_tries_var = tk.StringVar(value="225")
        self.status_var = tk.StringVar(value="대기 중...")
        
        # --- 구역별 변수 초기화 ---
        # 나중에 구역 2, 3, 4를 추가할 때 아래 라인을 추가하면 됩니다.
        self._initialize_area_vars(1)
        self._initialize_area_vars(2)

    def _initialize_area_vars(self, area_number: int):
        """지정된 번호의 구역에 대한 Tkinter 변수들을 초기화하고 저장합니다."""
        self.area_vars[area_number] = {
            'use_var': tk.BooleanVar(value=True),
            'coord_var': tk.StringVar(value="(0, 0)"),
            'clicks_var': tk.StringVar(value="6"),
            'offset_var': tk.StringVar(value="2"),
            # 각 구역별 탐색 영역을 위한 좌표 변수를 추가합니다.
            'p1_var': tk.StringVar(value="(0, 0)"),
            'p2_var': tk.StringVar(value="(0, 0)"),
            # 구역별 개별 탐색 영역 사용 여부
            'use_area_bounds_var': tk.BooleanVar(value=True), # 기본값: 개별 영역 사용 안 함
            # 구역별 색상 및 탐색 방향을 위한 변수 추가
            'use_color_var': tk.BooleanVar(value=True), # 기본적으로는 구역별 색상 사용 안 함
            'color_var': tk.StringVar(value="(0, 0, 0)"),
            'direction_var': tk.StringVar(value=self.SEARCH_DIRECTION_MAP[self.controller.search_direction]),
            'use_direction_var': tk.BooleanVar(value=True), # 기본적으로 구역별 탐색 방향 사용 안 함
        }

    def _setup_ui(self):
        """메인 UI를 생성하고 배치합니다."""
        self.root.title("Auto Color Clicker")
        self.root.geometry("400x720") # 구역 UI 추가를 위해 높이 조정
        self.root.configure(bg="#2e2e2e")
        self.root.resizable(True, True)

        main_frame = tk.Frame(self.root, bg="#2e2e2e", padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 기본 설정 그룹 ---
        basic_group = self._create_labeled_frame(main_frame, "기본")
        basic_group.pack(fill=tk.X, pady=(0, 10))

        # Row 1: 색상오차, 색상영역 오차
        # row1_container = tk.Frame(self.root, bg="#2e2e2e")
        # row1_container.pack(fill=tk.X, expand=True)
        # 예시: 왼쪽 프레임이 오른쪽 프레임보다 2배 더 넓게 설정 (2:1 비율)
        row1_container, (left_frame, right_frame) = self._create_split_container(basic_group, weights=[1, 1])
        self._create_labeled_entry(left_frame, "색상오차:", self.color_tolerance_var).pack(expand=True, fill=tk.X)
        self._create_labeled_entry(right_frame, "색영역오차:", self.color_area_tolerance_var).pack(expand=True, fill=tk.X)

        # Row 2: 영역 설정
        row2_container, (left_frame, right_frame) = self._create_split_container(basic_group, weights=[1, 1])
        p1_selector_frame, _, _ = self._create_coordinate_selector(left_frame, self.p1_var, "↖영역", command=lambda: self.controller.start_coordinate_picker('p1'))
        p1_selector_frame.pack(expand=True, fill=tk.X)
        p2_selector_frame, _, _ = self._create_coordinate_selector(right_frame, self.p2_var, "↘영역", command=lambda: self.controller.start_coordinate_picker('p2'))
        p2_selector_frame.pack(expand=True, fill=tk.X)
        
        # Row 3: 색상, 완료 
        row3_container, (left_frame, right_frame) = self._create_split_container(basic_group, weights=[1, 1])
        self._create_value_button_row(left_frame, self.color_var, "색상", command=lambda: self.controller.start_color_picker('main_color')).pack(expand=True, fill=tk.X)
        self._create_value_button_row(right_frame, self.complete_coord_var, "완료", command=lambda: self.controller.start_coordinate_picker('complete')).pack(expand=True, fill=tk.X)
        
        # Row 4: 총 시도횟수, 딜레이, 탐색 방향
        # 더 나은 정렬을 위해 3개의 프레임으로 분할합니다.
        row4_container, (left_frame, right_frame) = self._create_split_container(basic_group, weights=[1, 1])
        
        # Part 1: 총 시도횟수
        self._create_labeled_entry(left_frame, "시도횟수:", self.total_tries_var).pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        # Part 2: 딜레이
        self._create_labeled_entry(left_frame, "딜레이:", self.complete_delay_var).pack(side=tk.RIGHT, expand=True, fill=tk.X)

        # Part 3: 탐색 방향
        direction_menu = tk.OptionMenu(right_frame, self.direction_var, *self.SEARCH_DIRECTION_MAP.values())
        direction_menu.config(bg="#555555", fg="white", activebackground="#666666", activeforeground="white", highlightthickness=0, borderwidth=1)
        direction_menu["menu"].config(bg="#555555", fg="white")
        direction_menu.pack(side=tk.RIGHT, padx=5)

        # Row 5: 구역 사용, 구역 딜레이
        row5_container, (left_frame, right_frame) = self._create_split_container(basic_group, weights=[1, 1])
        tk.Checkbutton(left_frame, text="구역탐색 사용", variable=self.use_sequence_var, bg="#2e2e2e", fg="white", selectcolor="#2e2e2e", activebackground="#2e2e2e", highlightthickness=0).pack(side=tk.LEFT)
        self._create_labeled_entry(right_frame, "구역 딜레이:", self.area_delay_var).pack(expand=True, fill=tk.X)

        # --- 상태 메시지 ---
        status_label = tk.Label(main_frame, textvariable=self.status_var, fg="lightblue", bg="#2e2e2e", anchor='w')
        status_label.pack(fill=tk.X, pady=(0, 10))

        # --- 구역 설정 그룹 ---
        # 이 프레임은 모든 구역(구역1, 구역2 등)을 감싸는 컨테이너 역할을 합니다.
        areas_container_group = self._create_labeled_frame(main_frame, "구역 설정")
        areas_container_group.pack(fill=tk.X, pady=(0, 10))

        # 재사용 가능한 헬퍼 메서드를 사용하여 구역 그룹 생성
        self._create_area_group(areas_container_group, 1)
        self._create_area_group(areas_container_group, 2)

        # --- 액션 버튼 ---
        action_frame = tk.Frame(main_frame, bg="#2e2e2e")
        action_frame.pack(fill=tk.X, side=tk.BOTTOM)
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(1, weight=1)
        self.area_button = tk.Button(action_frame, text="영역확인", command=self.controller.show_area)
        self.area_button.grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))
        
        self.find_button = tk.Button(action_frame, text="찾기(Shift+s)", command=self.controller.toggle_search)
        self.find_button.grid(row=0, column=1, sticky=tk.EW, padx=(5, 0))

    def _create_area_group(self, parent, area_number: int):
        """
        지정된 번호의 구역 설정 UI 그룹을 생성하고 배치합니다.
        재사용성을 위해 헬퍼 메서드로 분리했습니다.
        나중에 구역 2, 3, 4를 추가할 때 이 메서드를 호출하기만 하면 됩니다.

        :param parent: 이 그룹이 속할 부모 위젯
        :param area_number: 생성할 구역의 번호 (예: 1)
        """
        area_group = tk.LabelFrame(parent, text=f"구역{area_number}", fg="white", bg="#2e2e2e", padx=10, pady=5)
        area_group.pack(fill=tk.X, pady=2, padx=5, ipady=5)

        # 이 구역에 해당하는 변수들을 가져옵니다.
        vars = self.area_vars[area_number]

        # UI를 좌우로 나누기 위한 컨테이너 생성
        row1_container, (left_frame, right_frame) = self._create_split_container(area_group, weights=[2, 1])

        # --- Row 1 위젯 생성 (pack은 나중에) ---
        coord_label = tk.Label(left_frame, textvariable=vars['coord_var'], relief="sunken", bg="#555555", width=10, anchor='w')
        coord_button = tk.Button(left_frame, text=f"구역 {area_number}", width=3, command=lambda: self.controller.start_coordinate_picker(f'area_{area_number}_click_coord'))
        
        right_inner_frame = tk.Frame(right_frame, bg="#2e2e2e")
        clicks_frame = self._create_labeled_entry(right_inner_frame, "횟수:", vars['clicks_var'])
        offset_frame = self._create_labeled_entry(right_inner_frame, "오차:", vars['offset_var'])

        def toggle_search_state():
            """'탐색' 체크박스 상태에 따라 관련 위젯들을 활성화/비활성화합니다."""
            is_enabled = vars['use_var'].get()
            state = 'normal' if is_enabled else 'disabled'
            label_bg = '#555555'
            label_fg = 'white' if is_enabled else '#2e2e2e'
            entry_bg = '#444444' if is_enabled else '#555555'

            coord_label.config(state=state, bg=label_bg, fg=label_fg)
            coord_button.config(state=state)

            for frame in [clicks_frame, offset_frame]:
                for widget in frame.winfo_children():
                    if isinstance(widget, tk.Entry):
                        widget.config(state=state, disabledbackground=entry_bg)
                    else: # Label
                        widget.config(state=state)

        # --- Row 1 왼쪽: 탐색 활성화, 클릭 좌표 설정 ---
        tk.Checkbutton(left_frame, text="탐색", variable=vars['use_var'], bg="#2e2e2e", fg="white", selectcolor="#2e2e2e", activebackground="#2e2e2e", highlightthickness=0, command=toggle_search_state).pack(side=tk.LEFT)
        coord_label.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5,0))
        coord_button.pack(side=tk.LEFT)

        # --- Row 1 오른쪽: 선택 횟수, 오차 설정 ---
        right_inner_frame.pack(fill=tk.X)
        clicks_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
        offset_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # --- Row 2: 구역별 탐색 영역 설정 ---
        row2_container, (left_frame2, right_frame2) = self._create_split_container(area_group, weights=[1, 1])
        
        p1_selector_frame, p1_label, p1_button = self._create_coordinate_selector(left_frame2, vars['p1_var'], "↖영역", command=lambda: self.controller.start_coordinate_picker(f'area_{area_number}_p1'))
        p2_selector_frame, p2_label, p2_button = self._create_coordinate_selector(right_frame2, vars['p2_var'], "↘영역", command=lambda: self.controller.start_coordinate_picker(f'area_{area_number}_p2'))

        def toggle_area_bounds_state():
            """'기본' 체크박스 상태에 따라 영역 선택 위젯들을 활성화/비활성화하고 값을 동기화합니다."""
            # 체크 시(True) 비활성화, 언체크 시(False) 활성화되도록 논리 반전
            use_default_bounds = vars['use_area_bounds_var'].get()
            is_enabled = not use_default_bounds
            state = 'normal' if is_enabled else 'disabled'
            label_bg = '#555555'
            label_fg = 'white' if is_enabled else '#2e2e2e'
            
            p1_label.config(state=state, bg=label_bg, fg=label_fg)
            p1_button.config(state=state)
            p2_label.config(state=state, bg=label_bg, fg=label_fg)
            p2_button.config(state=state)

            if use_default_bounds:
                # '기본'이 체크되면, 전역 p1, p2 값을 해당 구역의 변수에 설정합니다.
                vars['p1_var'].set(self.p1_var.get())
                vars['p2_var'].set(self.p2_var.get())

        tk.Checkbutton(left_frame2, text="기본", variable=vars['use_area_bounds_var'], bg="#2e2e2e", fg="white", selectcolor="#2e2e2e", activebackground="#2e2e2e", highlightthickness=0, command=toggle_area_bounds_state).pack(side=tk.LEFT)
        p1_selector_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5,0))
        p2_selector_frame.pack(expand=True, fill=tk.X)

        # --- Row 3: 구역별 색상 및 탐색 방향 설정 ---
        row3_container, (left_frame3, right_frame3) = self._create_split_container(area_group, weights=[1, 1])

        # --- Row 3 왼쪽: 색상 사용, 색상 값, 색상 선택 버튼 ---
        color_label = tk.Label(left_frame3, textvariable=vars['color_var'], relief="sunken", bg="white", anchor='w')
        color_button = tk.Button(left_frame3, text="색상", width=3, command=lambda: self.controller.start_color_picker(f'area_{area_number}_color'))

        def toggle_color_state():
            """'기본' 체크박스 상태에 따라 색상 위젯들을 활성화/비활성화하고 값을 동기화합니다."""
            # '기본'이 체크되면(True), 개별 설정 위젯은 비활성화됩니다.
            use_default_color = vars['use_color_var'].get()
            is_enabled = not use_default_color
            state = 'normal' if is_enabled else 'disabled'
            # ... (UI 상태 변경 코드) ...
            color_button.config(state=state)

            if use_default_color:
                # '기본'이 체크되면, 전역 색상 값을 해당 구역의 변수에 설정합니다.
                vars['color_var'].set(self.color_var.get())
            is_enabled = not use_default_color
            state = 'normal' if is_enabled else 'disabled'
            bg_color = '#555555'
            label_fg = 'white' if is_enabled else '#2e2e2e'
            color_label.config(state=state, bg=bg_color, fg=label_fg)
            color_button.config(state=state)

            if use_default_color:
                # '기본'이 체크되면, 전역 색상 값을 해당 구역의 변수에 설정합니다.
                vars['color_var'].set(self.color_var.get())

        tk.Checkbutton(left_frame3, text="기본", variable=vars['use_color_var'], bg="#2e2e2e", fg="white", selectcolor="#2e2e2e", activebackground="#2e2e2e", highlightthickness=0, command=toggle_color_state).pack(side=tk.LEFT)
        color_label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        color_button.pack(side=tk.LEFT)

        # --- Row 3 오른쪽: 탐색 방향 ---
        direction_menu = tk.OptionMenu(right_frame3, vars['direction_var'], *self.SEARCH_DIRECTION_MAP.values())
        direction_menu.config(bg="#555555", fg="white", activebackground="#666666", activeforeground="white", highlightthickness=0, borderwidth=1)
        direction_menu["menu"].config(bg="#555555", fg="white")

        def toggle_direction_state():
            """'기본' 체크박스 상태에 따라 탐색 방향 메뉴를 활성화/비활성화하고 값을 동기화합니다."""
            use_default_direction = vars['use_direction_var'].get()
            is_enabled = not use_default_direction
            state = 'normal' if is_enabled else 'disabled'
            
            direction_menu.config(state=state)

            if use_default_direction:
                # '기본'이 체크되면, 전역 탐색 방향 값을 해당 구역의 변수에 설정합니다.
                vars['direction_var'].set(self.direction_var.get())

        tk.Checkbutton(right_frame3, text="기본", variable=vars['use_direction_var'], bg="#2e2e2e", fg="white", selectcolor="#2e2e2e", activebackground="#2e2e2e", highlightthickness=0, command=toggle_direction_state).pack(side=tk.LEFT)
        direction_menu.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(5,0))
        
        # --- 전역 변수 변경 감지 및 동기화 ---
        # 전역(기본) 설정이 변경될 때, '기본'이 체크된 구역의 값도 함께 업데이트합니다.
        def update_area_p1_from_global(*args):
            if vars['use_area_bounds_var'].get():
                vars['p1_var'].set(self.p1_var.get())
        def update_area_p2_from_global(*args):
            if vars['use_area_bounds_var'].get():
                vars['p2_var'].set(self.p2_var.get())
        def update_area_color_from_global(*args):
            if vars['use_color_var'].get():
                vars['color_var'].set(self.color_var.get())
        def update_area_direction_from_global(*args):
            if vars['use_direction_var'].get():
                vars['direction_var'].set(self.direction_var.get())

        self.p1_var.trace_add('write', update_area_p1_from_global)
        self.p2_var.trace_add('write', update_area_p2_from_global)
        self.color_var.trace_add('write', update_area_color_from_global)
        self.direction_var.trace_add('write', update_area_direction_from_global)

        toggle_search_state() # 초기 상태 설정
        toggle_color_state() # 초기 상태 설정을 위해 호출
        toggle_area_bounds_state() # 초기 상태 설정
        toggle_direction_state() # 초기 상태 설정

        return area_group

    def queue_task(self, task):
        """다른 스레드에서 UI 업데이트 작업을 큐에 추가합니다."""
        self.ui_queue.put(task)

    def _process_ui_queue(self):
        """메인 스레드에서 UI 업데이트 큐를 주기적으로 확인하고 처리합니다."""
        try:
            while True:
                task = self.ui_queue.get_nowait()
                task()
        except queue.Empty:
            pass
        finally:
            # 100ms 마다 큐를 다시 확인하도록 예약합니다.
            self.root.after(100, self._process_ui_queue)

    def update_button_text(self, text: str):
        """'찾기' 버튼의 텍스트를 변경합니다."""
        if self.find_button:
            self.find_button.config(text=text)

    def update_status(self, text: str):
        """상태 메시지 레이블의 텍스트를 업데이트합니다."""
        self.status_var.set(text)

    def display_visual_aids(self, areas=None, points=None):
        """화면에 영역과 좌표 마커들을 표시합니다."""
        # 기존 마커 창들 제거
        for marker in self.area_marker_windows:
            if marker and marker.winfo_exists():
                marker.destroy()
        self.area_marker_windows.clear()

        for marker in self.point_marker_windows:
            if marker and marker.winfo_exists():
                marker.destroy()
        self.point_marker_windows.clear()

        # 여러 영역 마커 표시
        if areas:
            for area_info in areas:
                x, y, width, height = area_info.get('rect', (0,0,0,0))
                color = area_info.get('color', 'red')
                alpha = area_info.get('alpha', 0.4)

                if width > 0 and height > 0:
                    area_marker = tk.Toplevel(self.root)
                    area_marker.overrideredirect(True)
                    area_marker.geometry(f"{width}x{height}+{x}+{y}")
                    area_marker.configure(bg=color)
                    area_marker.attributes('-alpha', alpha)
                    area_marker.attributes('-topmost', True)
                    area_marker.after(3000, area_marker.destroy)
                    self.area_marker_windows.append(area_marker)

        # 좌표 마커들 표시
        if points:
            marker_size = 20
            for point_info in points:
                text = point_info.get('text', '')
                pos = point_info.get('pos')
                marker_color = point_info.get('color', '#FFFFFF') # 기본값 흰색

                if not pos or (pos[0] == 0 and pos[1] == 0): continue
                px, py = pos
                
                marker = tk.Toplevel(self.root)
                marker.overrideredirect(True)
                marker.geometry(f"{marker_size}x{marker_size}+{px - marker_size//2}+{py - marker_size//2}")
                marker.configure(bg=marker_color, highlightthickness=1, highlightbackground="white")
                marker.attributes('-alpha', 0.7)
                marker.attributes('-topmost', True)
                # 텍스트 색상을 마커 색상에 따라 흑/백으로 자동 조절
                try:
                    r, g, b = self.root.winfo_rgb(marker_color)
                    # YIQ 공식으로 밝기 계산 (0-255000 범위)
                    brightness = ((r * 299) + (g * 587) + (b * 114)) / 1000
                    text_color = "black" if brightness > 128000 else "white"
                except tk.TclError:
                    text_color = "black" # 색상 이름이 잘못된 경우 기본값

                tk.Label(marker, text=text, bg=marker_color, fg=text_color, font=("Helvetica", 8, "bold")).pack(expand=True, fill='both')
                marker.after(3000, marker.destroy)
                self.point_marker_windows.append(marker)

        self.update_status(f"영역 및 좌표 표시 중...")

    def _create_labeled_frame(self, parent, text):
        """제목이 있는 프레임을 생성합니다."""
        frame = tk.LabelFrame(parent, text=text, fg="white", bg="#2e2e2e", padx=10, pady=5, relief=tk.SOLID, borderwidth=1)
        return frame

    def _create_split_container(self, parent, weights=[1, 1], **pack_options):
        """
        지정된 가중치에 따라 여러 열로 나뉘는 컨테이너 프레임을 생성합니다.
        
        :param parent: 부모 위젯
        :param weights: 각 열의 가중치를 담은 리스트. 예: [2, 1] -> 왼쪽이 오른쪽보다 2배 넓음
        :param pack_options: 컨테이너의 pack() 메서드에 전달할 추가 옵션 (예: ipady, pady)
        :return: (컨테이너 프레임, [각 열의 프레임 리스트])
        """
        container = tk.Frame(parent, bg="#2e2e2e")
        
        default_options = {'fill': tk.X, 'pady': 2}
        default_options.update(pack_options)
        container.pack(**default_options)

        frames = []
        num_columns = len(weights)
        for i, weight in enumerate(weights):
            # 각 열에 지정된 가중치(weight)를 설정합니다.
            container.grid_columnconfigure(i, weight=weight)
            frame = tk.Frame(container, bg="#2e2e2e")
            frame.grid(row=0, column=i, sticky=tk.EW, padx=(5 if i > 0 else 0, 0))
            frames.append(frame)
            
        return container, frames

    def _create_labeled_entry(self, parent, label_text, var):
        """레이블과 입력창으로 구성된 위젯 그룹을 생성합니다."""
        frame = tk.Frame(parent, bg="#2e2e2e")
        tk.Label(frame, text=label_text, fg="white", bg="#2e2e2e").pack(
            side=tk.LEFT)
        tk.Entry(frame, textvariable=var, width=2, bg="#444444", fg="white", insertbackground='white', borderwidth=0, highlightthickness=0).pack(
            side=tk.LEFT, expand=True, fill=tk.X)
        return frame

    def _create_coordinate_selector(self, parent, var, button_text, command=None):
        """좌표값 표시 레이블과 선택 버튼으로 구성된 위젯 그룹을 생성하고, 위젯들을 반환합니다."""
        frame = tk.Frame(parent, bg="#2e2e2e")
        label = tk.Label(frame, textvariable=var, relief="sunken", bg="#555555", width=8, anchor='w')
        label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        button = tk.Button(frame, text=button_text, width=3, command=command)
        button.pack(side=tk.LEFT)
        return frame, label, button

    def _create_value_button_row(self, parent, var, button_text, command=None):
        """값 표시 레이블과 선택 버튼으로 구성된 위젯 그룹을 생성합니다."""
        frame = tk.Frame(parent, bg="#2e2e2e")
        tk.Label(frame, textvariable=var, relief="sunken", bg="#555555", width=10, anchor='w').pack(
            side=tk.LEFT, expand=True, fill=tk.X)
        tk.Button(frame, text=button_text, width=3, command=command).pack(
            side=tk.LEFT)
        return frame
