import tkinter as tk
from tkinter import ttk
import sys
import queue
import ast

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
        self.scrollable_canvas = None
        self.scrollable_content_frame = None
        self.global_toggles = {}
        self.area_widgets = {} # 구역별 위젯을 저장하기 위한 딕셔너리
        self.area_toggles = {}
        self.ui_queue = queue.Queue()
        self.area_vars = {}
        # 튜플 형식(숫자, 괄호, 콤마, 공백) 입력을 검증하기 위한 커맨드 등록
        self.tuple_vcmd = (self.root.register(self._validate_tuple_input), '%P')
        self._initialize_vars()
        self._setup_ui()
        self._process_ui_queue()

    def _initialize_vars(self):
        """UI에 사용될 Tkinter 변수들을 초기화합니다."""
        # 모든 기본값은 컨트롤러(c)에서 가져옵니다.
        c = self.controller
        self.color_tolerance_var = tk.StringVar(value=str(c.color_tolerance))
        self.color_area_tolerance_var = tk.StringVar(value=str(c.color_area_tolerance))
        self.complete_delay_var = tk.StringVar(value=str(int(c.complete_click_delay * 100)))
        self.p1_var = tk.StringVar(value=str(c.p1))
        self.p2_var = tk.StringVar(value=str(c.p2))
        self.color_var = tk.StringVar(value=str(c.color))
        self.use_secondary_color_var = tk.BooleanVar(value=c.use_secondary_color)
        self.secondary_color_var = tk.StringVar(value=str(c.secondary_color))
        self.use_search_delay_var = tk.BooleanVar(value=c.use_search_delay)
        self.area_delay_var = tk.StringVar(value=str(int(c.area_delay * 100)))
        self.search_delay_var = tk.StringVar(value=str(int(c.search_delay * 100)))
        self.complete_coord_var = tk.StringVar(value=str(c.complete_coord))
        self.use_initial_search_var = tk.BooleanVar(value=c.use_initial_search)
        self.use_space_complete_var = tk.BooleanVar(value=c.use_space_complete)
        self.use_screen_activation_var = tk.BooleanVar(value=c.use_screen_activation)
        self.use_operation_check_var = tk.BooleanVar(value=c.use_operation_check)
        self.op_check_coord_var = tk.StringVar(value=str(c.op_check_coord))
        self.op_check_color_var = tk.StringVar(value=str(c.op_check_color))
        self.op_check_max_retries_var = tk.StringVar(value=str(c.op_check_max_retries))
        self.op_check_retry_interval_var = tk.StringVar(value=str(int(c.op_check_retry_interval * 100)))
        self.empty_coord_var = tk.StringVar(value=str(c.empty_coord))

        self.use_sequence_var = tk.BooleanVar(value=c.use_sequence)
        # 탐색 방향 Enum과 UI 표시 문자열을 매핑합니다.
        self.SEARCH_DIRECTION_MAP = {
            SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT: "→↓ (q)",
            SearchDirection.TOP_RIGHT_TO_BOTTOM_LEFT: "←↓ (w)",
            SearchDirection.BOTTOM_LEFT_TO_TOP_RIGHT: "→↑ (a)",
            SearchDirection.BOTTOM_RIGHT_TO_TOP_LEFT: "←↑ (s)",
            SearchDirection.TOP_TO_BOTTOM_LEFT_TO_RIGHT: "↓→ (e)",
            SearchDirection.TOP_TO_BOTTOM_RIGHT_TO_LEFT: "↓← (r)",
            SearchDirection.BOTTOM_TO_TOP_LEFT_TO_RIGHT: "↑→ (d)",
            SearchDirection.BOTTOM_TO_TOP_RIGHT_TO_LEFT: "↑← (f)",
            SearchDirection.TOP_TO_BOTTOM_LEFT_TO_RIGHT: "↓→ (e)",
            SearchDirection.TOP_TO_BOTTOM_RIGHT_TO_LEFT: "↓← (r)",
            SearchDirection.BOTTOM_TO_TOP_LEFT_TO_RIGHT: "↑→ (d)",
            SearchDirection.BOTTOM_TO_TOP_RIGHT_TO_LEFT: "↑← (f)",
            SearchDirection.CENTER_TOP_TO_BOTTOM: "↓↔ (z)",
            SearchDirection.CENTER_BOTTOM_TO_TOP: "↑↔ (x)",
            SearchDirection.CENTER_LEFT_TO_RIGHT: "→↕ (c)",
            SearchDirection.CENTER_RIGHT_TO_LEFT: "←↕ (v)",
            SearchDirection.CENTER_TO_CENTER: "중앙 ☉ (g)",
        }
        self.direction_var = tk.StringVar(value=self.SEARCH_DIRECTION_MAP[c.search_direction])
        self.total_duration_var = tk.StringVar(value=str(c.total_duration_sec))
        self.active_search_duration_var = tk.StringVar(value=str(c.active_search_duration_sec))
        self.wait_duration_var = tk.StringVar(value=str(c.wait_duration_sec))
        self.search_time_tolerance_var = tk.StringVar(value=str(c.search_time_tolerance_sec))
        self.status_var = tk.StringVar(value="대기 중...")

        # --- 창 색상 관리 ---
        self.WINDOW_COLORS = {
            'default': "#252525",
            'searching': "medium turquoise",
            'waiting': "orange", # 가독성을 위해 LemonChiffon에서 orange로 변경
            'global_setting_change': "#40E0D0", # 기본 설정 변경 시 플래시 색상 (터콰이즈)
            'area_setting_change': "LemonChiffon",   # 구역 설정 변경 시 플래시 색상 (노랑)
        }
        
        # --- 구역별 변수 초기화 ---
        for i in range(1, 6):
            self._initialize_area_vars(i)

    def _initialize_area_vars(self, area_number: int):
        """지정된 번호의 구역에 대한 Tkinter 변수들을 초기화하고 저장합니다."""
        # 컨트롤러에 미리 정의된 구역별 기본값을 가져옵니다.
        area_defaults = self.controller.areas[area_number]

        self.area_vars[area_number] = {
            'name_var': tk.StringVar(value=area_defaults.get('name', f"구역{area_number}")),
            'use_var': tk.BooleanVar(value=area_defaults['use']),
            'coord_var': tk.StringVar(value=str(area_defaults['click_coord'])),
            'clicks_var': tk.StringVar(value=str(area_defaults['clicks'])),
            'offset_var': tk.StringVar(value=str(area_defaults['offset'])),
            'p1_var': tk.StringVar(value=str(area_defaults['p1'])),
            'p2_var': tk.StringVar(value=str(area_defaults['p2'])),
            'color_var': tk.StringVar(value=str(area_defaults['color'])),
            'direction_var': tk.StringVar(value=self.SEARCH_DIRECTION_MAP[area_defaults['direction']]),
            # '기본' 체크박스들은 컨트롤러 값과 논리가 반대입니다. (UI 체크 True == 컨트롤러 use_... False)
            'use_area_bounds_var': tk.BooleanVar(value=not area_defaults['use_area_bounds']),
            'use_color_var': tk.BooleanVar(value=not area_defaults['use_color']),
            'use_direction_var': tk.BooleanVar(value=not area_defaults['use_direction']),
        }

    def _setup_ui(self):
        """메인 UI를 생성하고 배치합니다."""
        self.root.title("LuAuttic For히기 v.2.3.1")

        window_width = 430
        # 4개의 구역이 모두 보이도록 창 높이 설정합니다.
        window_height = 940

        # 화면의 너비를 가져옵니다.
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 창을 모니터 오른쪽 상단에 위치시킵니다.
        x_pos = screen_width - window_width
        y_pos = 0 # 상단 여백

        self.root.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")
        self.update_window_bg('default')
        self.root.resizable(True, True)

        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 기본 설정 그룹 ---
        basic_group = self._create_labeled_frame(main_frame, "기본", name="basic_group")
        basic_group.pack(fill=tk.X, pady=(0, 10))

        # Row 1: 영역 설정
        row1_container, (left_frame, right_frame) = self._create_split_container(basic_group, weights=[1, 1])
        p1_selector_frame, _, _ = self._create_coordinate_selector(left_frame, self.p1_var, "↖영역", command=lambda: self.controller.start_coordinate_picker('p1'))
        p1_selector_frame.pack(expand=True, fill=tk.X)
        p2_selector_frame, _, _ = self._create_coordinate_selector(right_frame, self.p2_var, "↘영역", command=lambda: self.controller.start_coordinate_picker('p2'))
        p2_selector_frame.pack(expand=True, fill=tk.X)
        
        # Row 2: 1순위 색상, 2순위 색상
        row2_container, (left_frame, right_frame) = self._create_split_container(basic_group, weights=[1, 1])
        # Part 1: 1순위 색상 (기본 색상)
        self._create_value_button_row(left_frame, self.color_var, "색상 1", command=lambda: self.controller.start_color_picker('main_color'), show_preview=True).pack(expand=True, fill=tk.X)

        # Part 2: 2순위 색상 (토글 가능)
        secondary_color_selector, toggle_func = self._create_toggleable_color_selector(
            right_frame,
            use_var=self.use_secondary_color_var,
            color_var=self.secondary_color_var,
            check_text="",
            button_text="색상 2",
            command=lambda: self.controller.start_color_picker('secondary_color')
        )
        self.global_toggles['secondary_color'] = toggle_func
        secondary_color_selector.pack(expand=True, fill=tk.X)

        # Row 3: 색상오차, 색상영역 오차
        row3_container, (_, _, right_frame) = self._create_split_container(basic_group, weights=[1, 1, 1])
        self._create_labeled_entry(right_frame, "색영역오차:", self.color_area_tolerance_var).pack(side=tk.RIGHT)
        self._create_labeled_entry(right_frame, "색상오차:", self.color_tolerance_var).pack(side=tk.RIGHT)


        # Row 4: 완료 좌표, 완료 딜레이, 탐색 방향
        row4_container, (left_frame, right_frame) = self._create_split_container(basic_group, weights=[1, 1])
        
        # Part 1: 완료 좌표
        self._create_value_button_row(left_frame, self.complete_coord_var, "완료", command=lambda: self.controller.start_coordinate_picker('complete')).pack(side=tk.LEFT)
      
        # Part 2: 완료 선택 딜레이, 탐색 방향
        self._create_labeled_entry(right_frame, "완료 딜레이:", self.complete_delay_var).pack(expand=True, fill=tk.X, side=tk.LEFT)

        # Part 3: 탐색 방향
        direction_menu = tk.OptionMenu(right_frame, self.direction_var, *self.SEARCH_DIRECTION_MAP.values())
        direction_menu.config( fg="white", activebackground="#666666", activeforeground="white", highlightthickness=0, borderwidth=1)
        direction_menu["menu"].config(bg="#555555", fg="white")
        direction_menu.pack(side=tk.RIGHT, padx=(15,0))

        

        # --- 상태 메시지 및 구역/기본 탐색 토글 ---
        status_and_toggle_container = tk.Frame(main_frame)
        status_and_toggle_container.pack(fill=tk.X, pady=2)

        # --- 구역, 기본 탐색 사용 여부 ---
        toggle_frame = tk.Frame(status_and_toggle_container)
        toggle_frame.pack(fill=tk.X)
        tk.Checkbutton(toggle_frame, text="기본 탐색 사용", variable=self.use_initial_search_var, fg="white", selectcolor="#2e2e2e", activebackground="#2e2e2e", highlightthickness=0).pack(side=tk.LEFT)
        tk.Checkbutton(toggle_frame, text="스페이스완료", variable=self.use_space_complete_var, fg="white", selectcolor="#2e2e2e", activebackground="#2e2e2e", highlightthickness=0).pack(side=tk.LEFT, padx=(10,0))
        # --- 상태 메시지 ---
        status_label = tk.Label(status_and_toggle_container, bg="#555555", textvariable=self.status_var, fg="lightblue", anchor='w')
        status_label.pack(fill=tk.X, pady=(5,0))

        # --- 구역 설정 그룹 ---
        # LabelFrame의 헤더에 체크박스와 제목 배치 (기존 '구역 탐색 사용' 체크박스 이동)
        areas_header = tk.Frame(main_frame, bg=self.WINDOW_COLORS['default'])
        self.use_sequence_cb = tk.Checkbutton(areas_header, variable=self.use_sequence_var, 
                                              activebackground="#2e2e2e", highlightthickness=0,
                                              command=self._toggle_area_settings_active)
        self.use_sequence_cb.pack(side=tk.LEFT)
        self.areas_header_label = tk.Label(areas_header, text="구역 탐색", fg="white")
        self.areas_header_label.pack(side=tk.LEFT)

        self.areas_container_group = tk.LabelFrame(main_frame, labelwidget=areas_header, padx=10, pady=5, relief=tk.SOLID, borderwidth=1, name="areas_container_group")
        self.areas_container_group.pack(fill=tk.BOTH, expand=True, pady=(10))

        # 구역 세팅: 탐색/대기 시간
        time_set_container, (frame1, frame2, frame3) = self._create_split_container(self.areas_container_group, weights=[1, 1, 1])
        self.total_duration_frame = self._create_labeled_entry(frame1, "총 탐색(초):", self.total_duration_var)
        self.total_duration_frame.pack(expand=True, fill=tk.X)
        self.active_search_duration_frame = self._create_labeled_entry(frame2, "탐색(초):", self.active_search_duration_var)
        self.active_search_duration_frame.pack(expand=True, fill=tk.X)
        self.wait_duration_frame = self._create_labeled_entry(frame3, "대기(초):", self.wait_duration_var)
        self.wait_duration_frame.pack(expand=True, fill=tk.X)

        # 구역 세팅: 딜레이
        delay_set_container, (frame1, frame2, frame3) = self._create_split_container(self.areas_container_group, weights=[1, 1, 1])
        
        # 시간 오차를 딜레이 설정 왼쪽에 추가
        self.search_time_tolerance_frame = self._create_labeled_entry(frame1, "시간 오차(초):", self.search_time_tolerance_var)
        self.search_time_tolerance_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # 탐색 딜레이 사용 여부 체크박스
        self.search_delay_check = tk.Checkbutton(frame2, variable=self.use_search_delay_var, 
                                                 fg="white", selectcolor="#2e2e2e", activebackground="#2e2e2e", 
                                                 highlightthickness=0, command=self._toggle_search_delay_state)
        self.search_delay_check.pack(side=tk.LEFT)
        self.search_delay_frame = self._create_labeled_entry(frame2, "탐색 딜레이:", self.search_delay_var)
        self.search_delay_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.area_delay_frame = self._create_labeled_entry(frame3, "구역선택 딜레이:", self.area_delay_var)
        self.area_delay_frame.pack(side=tk.RIGHT,expand=True, fill=tk.X)


        # 색상 선택 전 화면 클릭
        area_active_container, (left_frame, right_frame) = self._create_split_container(self.areas_container_group, weights=[1, 1])
        # 빈공간 좌표
        self.screen_activation_check = tk.Checkbutton(left_frame, text="화면활성화", variable=self.use_screen_activation_var, fg="white", selectcolor="#2e2e2e", activebackground="#2e2e2e", highlightthickness=0)
        self.screen_activation_check.pack(side=tk.LEFT)
        self.empty_coord_frame = self._create_value_button_row(left_frame, self.empty_coord_var, "빈공간", command=lambda: self.controller.start_coordinate_picker('empty_coord'))
        self.empty_coord_frame.pack(side=tk.LEFT)
  
        # --- 탐색 화면 정상 여부 확인용 그룹 ---
        op_check_header = tk.Frame(self.areas_container_group)
        self.op_check_cb = tk.Checkbutton(op_check_header, variable=self.use_operation_check_var, 
                                          selectcolor="#2e2e2e", 
                                          activebackground="#2e2e2e", highlightthickness=0,
                                          command=self._toggle_operation_check_state)
        self.op_check_cb.pack(side=tk.LEFT)
        self.op_check_label = tk.Label(op_check_header, text="탐색 화면 정상 여부 확인", fg="white")
        self.op_check_label.pack(side=tk.LEFT)

        self.operation_check_group = tk.LabelFrame(self.areas_container_group, labelwidget=op_check_header, padx=10, pady=5)
        self.operation_check_group.pack(fill=tk.X, pady=12, padx=5, ipady=5)

        # Row 1: 화면 정상 여부 확인: 화면 확인 좌표, 화면 확인 색상
        operation_check_container, (left_frame, right_frame) = self._create_split_container(self.operation_check_group, weights=[1, 1])
        
        # 좌표 입력창 (통합 버튼 사용을 위해 버튼 없는 Entry 배치)
        tk.Entry(left_frame, textvariable=self.op_check_coord_var, bg="#555555", fg="white", 
                 insertbackground='white', borderwidth=0, highlightthickness=0, width=12,
                 validate="key", validatecommand=self.tuple_vcmd).pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        # 색상 입력창 + 통합 버튼
        self._create_color_preview(right_frame, self.op_check_color_var).pack(side=tk.LEFT, padx=(0, 5))

        tk.Entry(right_frame, 
                 textvariable=self.op_check_color_var, 
                 bg="#555555", 
                 fg="white", 
                 insertbackground='white', 
                 borderwidth=0, 
                 highlightthickness=0, 
                 width=12,
                 validate="key", 
                 validatecommand=self.tuple_vcmd
                 ).pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.op_check_combined_btn = tk.Button(right_frame, 
                                               text="좌표&색상", 
                                               activeforeground="white", 
                                               activebackground="#555555",
                                               command=lambda: self.controller.start_combined_picker('op_check'))
        self.op_check_combined_btn.pack(side=tk.LEFT, padx=(5,0))

        # Row 2: 재시도 설정 (횟수, 간격)
        op_retry_container, (left_frame_r, right_frame_r) = self._create_split_container(self.operation_check_group, weights=[1, 1])
        self._create_labeled_entry(left_frame_r, "재시도 횟수:", self.op_check_max_retries_var).pack(side=tk.LEFT, expand=True, fill=tk.X)
        self._create_labeled_entry(right_frame_r, "간격(10ms):", self.op_check_retry_interval_var).pack(side=tk.LEFT, expand=True, fill=tk.X)

        # 위젯 상태 관리를 위해 내부 프레임 저장
        self.op_check_inner_widgets = [left_frame, right_frame, left_frame_r, right_frame_r]
        scroll_container = tk.Frame(self.areas_container_group)
        scroll_container.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.scrollable_canvas = tk.Canvas(scroll_container, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=self.scrollable_canvas.yview)
        self.scrollable_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.scrollable_canvas.pack(side="left", fill=tk.BOTH, expand=True)

        self.scrollable_content_frame = tk.Frame(self.scrollable_canvas)
        self.canvas_window = self.scrollable_canvas.create_window((0, 0), window=self.scrollable_content_frame, anchor="nw")

        def on_canvas_configure(event):
            # 캔버스 너비에서 미세한 여유(4px)를 빼서 가로 스크롤바가 생기는 것을 방지하고 
            # 수직 스크롤바와의 겹침 현상을 해결합니다.
            canvas_width = max(0, event.width - 4)
            self.scrollable_canvas.itemconfig(self.canvas_window, width=canvas_width)

        self.scrollable_canvas.bind('<Configure>', on_canvas_configure)

        def on_frame_configure(event):
            self.scrollable_canvas.configure(scrollregion=self.scrollable_canvas.bbox("all"))

        self.scrollable_content_frame.bind("<Configure>", on_frame_configure)

        def on_mouse_wheel(event):
            # 플랫폼에 따라 스크롤 처리
            if sys.platform.startswith("win"):
                self.scrollable_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif sys.platform == "darwin": # macOS
                self.scrollable_canvas.yview_scroll(int(-1 * event.delta), "units")
            else: # Linux
                if event.num == 4: self.scrollable_canvas.yview_scroll(-1, "units")
                elif event.num == 5: self.scrollable_canvas.yview_scroll(1, "units")

        # 캔버스 및 그 자식 위젯들에서 마우스 휠 이벤트가 발생할 때 스크롤되도록 바인딩
        self.root.bind_all("<MouseWheel>", on_mouse_wheel)
        self.root.bind_all("<Button-4>", on_mouse_wheel)
        self.root.bind_all("<Button-5>", on_mouse_wheel)

        # 기본 5개 구역 UI 생성 (컨트롤러 설정과 동기화)
        for i in range(1, 6):
            self._create_area_group(self.scrollable_content_frame, i)

        # 구역 추가 버튼 생성 (상태 변경 메서드 호출 전에 생성되어야 함)
        self.add_area_btn = tk.Button(self.scrollable_content_frame, 
                                      text="+ 구역 추가", 
                                      command=self.controller.add_area)
        self.add_area_btn.pack(fill=tk.X, pady=10, padx=50)

        # --- 액션 버튼 ---
        action_frame = tk.Frame(main_frame)
        action_frame.pack(fill=tk.X)
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(1, weight=1)
        action_frame.grid_columnconfigure(2, weight=1)
        action_frame.grid_columnconfigure(3, weight=1)

        self.load_button = tk.Button(action_frame, 
                                     text="불러오기", 
                                     activeforeground="white", 
                                     activebackground="#555555",
                                     command=self.controller.load_settings)
        self.load_button.grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))
        self.save_button = tk.Button(action_frame, 
                                     text="저장하기", 
                                     activeforeground="white", 
                                     activebackground="#555555",
                                     command=self.controller.save_settings)
        self.save_button.grid(row=0, column=1, sticky=tk.EW, padx=(0, 5))

        self.area_button = tk.Button(action_frame, text="영역확인", 
                                     activeforeground="white", 
                                     activebackground="#555555",
                                     command=self.controller.show_area)
        self.area_button.grid(row=0, column=2, sticky=tk.EW, padx=(0, 5))
        
        self.find_button = tk.Button(action_frame, text="찾기(Shift x2 / ESC)", 
                                     activeforeground="white", 
                                     activebackground="#555555",
                                     command=self.controller.toggle_search)
        self.find_button.grid(row=0, column=3, sticky=tk.EW)

        # UI가 모두 생성된 후, 오버레이의 초기 상태를 설정합니다.
        self._toggle_area_settings_active()

    def _create_area_group(self, parent, area_number: int):
        """
        지정된 번호의 구역 설정 UI 그룹을 생성하고 배치합니다.
        재사용성을 위해 ₩헬퍼 메서드로 분리했습니다.

        :param parent: 이 그룹이 속할 부모 위젯
        :param area_number: 생성할 구역의 번호 (예: 1)
        """
        # LabelFrame의 헤더(제목) 영역에 들어갈 프레임 생성
        header_frame = tk.Frame(parent)

        # 탐색 순서 표시 레이블 (예: 1., 2. ...)
        try:
            order_idx = self.controller.area_order.index(area_number) + 1
        except (ValueError, AttributeError):
            order_idx = area_number

        order_label = tk.Label(header_frame, text=f"{order_idx}.", fg="white",  font=(None, 9, "bold"))
        order_label.pack(side=tk.LEFT, padx=(2, 0))

        name_entry = tk.Entry(header_frame, 
                              textvariable=self.area_vars[area_number]['name_var'],
                              fg="white", 
                              bg="#444444", 
                              font=(None, 9, "bold"),
                              borderwidth=0, 
                              highlightthickness=0, 
                              width=12)
        name_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        # 헤더에 들어갈 삭제 버튼 
        delete_button = tk.Button(header_frame, text="삭제", 
                                  fg="#f58585", 
                                  activeforeground="red", 
                                  activebackground="#444444",
                                  font=(None, 8), 
                                  command=lambda: self.controller.remove_area(area_number))
        delete_button.pack(side=tk.LEFT, padx=(5, 0))

        # 순서 변경 버튼
        up_button = tk.Button(header_frame, 
                              text="↑",
                              fg="black", 
                              activeforeground="white", 
                              activebackground="#555555",
                              font=(None, 8), 
                              command=lambda: self.controller.move_area(area_number, -1))
        up_button.pack(side=tk.LEFT)
        
        down_button = tk.Button(header_frame, text="↓", 
                                fg="black", 
                                activeforeground="white", 
                                activebackground="#555555",
                                font=(None, 8), 
                                command=lambda: self.controller.move_area(area_number, 1))
        down_button.pack(side=tk.LEFT)

        area_group = tk.LabelFrame(parent, labelwidget=header_frame)
        area_group.pack(fill=tk.BOTH, expand=True, pady=(10))
        # 이 구역에 해당하는 변수들을 가져옵니다.
        vars = self.area_vars[area_number]

        widgets = {} # 이 구역의 위젯들을 저장할 딕셔너리

        # UI를 좌우로 나누기 위한 컨테이너 생성
        row1_container, (left_frame, right_frame) = self._create_split_container(area_group, weights=[1, 1])

        # N 구역 탐색
        coord_label = tk.Entry(left_frame, 
                               textvariable=vars['coord_var'], 
                               bg="#444444", 
                               fg="white", 
                               insertbackground='white', 
                               borderwidth=0, 
                               highlightthickness=0, 
                               width=3, 
                               validate="key", 
                               validatecommand=self.tuple_vcmd)
        coord_button = tk.Button(left_frame, 
                                 text=f"구역 {area_number}", 
                                 activeforeground="white",

                                 activebackground="#555555",
                                 command=lambda: self.controller.start_coordinate_picker(f'area_{area_number}_click_coord'))
        

        right_inner_frame = tk.Frame(right_frame)
        clicks_frame = self._create_labeled_entry(right_inner_frame, "횟수:", vars['clicks_var'])
        offset_frame = self._create_labeled_entry(right_inner_frame, "오차:", vars['offset_var'])

        def toggle_search_state():
            """'탐색' 체크박스 상태에 따라 관련 위젯들을 활성화/비활성화합니다."""
            is_enabled = vars['use_var'].get()
            state = 'normal' if is_enabled else 'disabled'
            label_fg = 'white' if is_enabled else '#2e2e2e'
            entry_bg = '#444444' if is_enabled else '#555555'

            coord_label.config(state=state, fg=label_fg, disabledbackground=entry_bg)
            coord_button.config(state=state)

            for frame in [clicks_frame, offset_frame]:
                for widget in frame.winfo_children():
                    if isinstance(widget, tk.Entry):
                        widget.config(state=state, disabledbackground=entry_bg)
                    else: # Label
                        widget.config(state=state)

        # --- Row 1 왼쪽: 탐색 활성화, 클릭 좌표 설정 ---
        use_search_checkbutton = tk.Checkbutton(left_frame, 
                                                text="탐색", 
                                                variable=vars['use_var'], 
                                                selectcolor="#2e2e2e", 
                                                activebackground="#2e2e2e", 
                                                highlightthickness=0, 
                                                command=toggle_search_state)
        use_search_checkbutton.pack(side=tk.LEFT)

        coord_label.pack(side=tk.LEFT, expand=True, fill=tk.X)
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
            entry_bg = '#444444' if is_enabled else '#555555'
            
            p1_label.config(state=state, bg=label_bg, disabledbackground=entry_bg, fg=label_fg)
            p1_button.config(state=state)
            p2_label.config(state=state, bg=label_bg, disabledbackground=entry_bg, fg=label_fg)
            p2_button.config(state=state)

            if use_default_bounds:
                # '기본'이 체크되면, 전역 p1, p2 값을 해당 구역의 변수에 설정합니다.
                vars['p1_var'].set(self.p1_var.get())
                vars['p2_var'].set(self.p2_var.get())

        use_bounds_checkbutton = tk.Checkbutton(left_frame2, text="기본", variable=vars['use_area_bounds_var'], fg="white", selectcolor="#2e2e2e", activebackground="#2e2e2e", highlightthickness=0, command=toggle_area_bounds_state)
        use_bounds_checkbutton.pack(side=tk.LEFT)

        p1_selector_frame.pack(expand=True, fill=tk.X)
        p2_selector_frame.pack(expand=True, fill=tk.X)

        # --- Row 3: 구역별 색상 및 탐색 방향 설정 ---
        row3_container, (left_frame3, right_frame3) = self._create_split_container(area_group, weights=[1, 1])

        # --- Row 3 왼쪽: 색상 사용, 색상 값, 색상 선택 버튼 ---
        color_label = tk.Entry(left_frame3, 
                               textvariable=vars['color_var'], 
                               insertbackground='white', 
                               borderwidth=0, 
                               highlightthickness=0, 
                               validate="key",
                               validatecommand=self.tuple_vcmd)
        color_button = tk.Button(left_frame3, text="색상", 
                                 activeforeground="white",
                                 activebackground="#555555",
                                 command=lambda: self.controller.start_color_picker(f'area_{area_number}_color'))

        def toggle_color_state():
            """'기본' 체크박스 상태에 따라 색상 위젯들을 활성화/비활성화하고 값을 동기화합니다."""
            # '기본'이 체크되면(True), 개별 설정 위젯은 비활성화됩니다.
            use_default_color = vars['use_color_var'].get()
            is_enabled = not use_default_color
            state = 'normal' if is_enabled else 'disabled'
            bg_color = '#444444' if is_enabled else '#555555'
            label_fg = 'white' if is_enabled else '#2e2e2e'
            
            color_label.config(state=state, bg=bg_color, fg=label_fg, disabledbackground=bg_color, width=12)
            color_button.config(state=state)
            
            if use_default_color:
                # '기본'이 체크되면, 전역 색상 값을 해당 구역의 변수에 설정합니다.
                vars['color_var'].set(self.color_var.get())
            is_enabled = not use_default_color
            state = 'normal' if is_enabled else 'disabled'
            bg_color = '#555555'
            label_fg = 'white' if is_enabled else '#2e2e2e'
            entry_bg = '#444444' if is_enabled else '#555555'
            color_label.config(state=state, bg=bg_color, fg=label_fg, disabledbackground=entry_bg, width=12)
            color_button.config(state=state)

            if use_default_color:
                # '기본'이 체크되면, 전역 색상 값을 해당 구역의 변수에 설정합니다.
                vars['color_var'].set(self.color_var.get())

        use_color_checkbutton = tk.Checkbutton(left_frame3, 
                                               text="기본", 
                                               variable=vars['use_color_var'], 
                                               fg="white", 
                                               selectcolor="#2e2e2e", 
                                               activebackground="#2e2e2e", 
                                               highlightthickness=0, 
                                               command=toggle_color_state)
        use_color_checkbutton.pack(side=tk.LEFT)
        self._create_color_preview(left_frame3, vars['color_var']).pack(side=tk.LEFT, padx=(0, 5))
        color_label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        color_button.pack(side=tk.RIGHT)

        # --- Row 3 오른쪽: 탐색 방향 ---
        direction_menu = tk.OptionMenu(right_frame3, vars['direction_var'], *self.SEARCH_DIRECTION_MAP.values())
        direction_menu.config(fg="white", activebackground="#666666", activeforeground="white", highlightthickness=0, borderwidth=1)
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

        use_direction_checkbutton = tk.Checkbutton(right_frame3, text="기본", variable=vars['use_direction_var'], fg="white", selectcolor="#2e2e2e", activebackground="#2e2e2e", highlightthickness=0, command=toggle_direction_state)
        use_direction_checkbutton.pack(side=tk.LEFT)
        direction_menu.pack(fill=tk.X, expand=True, side=tk.LEFT)
        
        # 나중에 전체 활성/비활성화를 위해 위젯들을 저장합니다.
        widgets['group'] = area_group
        widgets['use_search_check'] = use_search_checkbutton
        widgets['delete_button'] = delete_button
        widgets['name_entry'] = name_entry
        widgets['order_label'] = order_label
        widgets['up_button'] = up_button
        widgets['down_button'] = down_button
        widgets['coord_label'] = coord_label
        widgets['coord_button'] = coord_button
        widgets['clicks_frame'] = clicks_frame
        widgets['offset_frame'] = offset_frame
        widgets['use_bounds_check'] = use_bounds_checkbutton
        widgets['p1_label'] = p1_label
        widgets['p1_button'] = p1_button
        widgets['p2_label'] = p2_label
        widgets['p2_button'] = p2_button
        widgets['use_color_check'] = use_color_checkbutton
        widgets['color_label'] = color_label
        widgets['color_button'] = color_button
        widgets['use_direction_check'] = use_direction_checkbutton
        widgets['direction_menu'] = direction_menu
        self.area_widgets[area_number] = widgets

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

        # 토글 함수들을 나중에 UI 업데이트 시 사용하기 위해 저장합니다.
        self.area_toggles[area_number] = {
            'search': toggle_search_state,
            'bounds': toggle_area_bounds_state,
            'color': toggle_color_state,
            'direction': toggle_direction_state,
        }

        toggle_search_state() # 초기 상태 설정
        toggle_color_state() # 초기 상태 설정을 위해 호출
        toggle_area_bounds_state() # 초기 상태 설정
        toggle_direction_state() # 초기 상태 설정


        return area_group   
    def add_area_to_ui(self, area_number: int):
        """새로운 구역 위젯을 UI 리스트 끝에 추가합니다."""
        if area_number not in self.area_vars:
            self._initialize_area_vars(area_number)
        
        self.add_area_btn.pack_forget() # 버튼을 잠시 가리고 아래에 다시 추가
        self._create_area_group(self.scrollable_content_frame, area_number)
        self.add_area_btn.pack(fill=tk.X)
        
        # 새로 추가된 구역의 활성화 상태 동기화
        self._toggle_area_settings_active()

    def refresh_area_order(self):
        """컨트롤러의 area_order에 맞춰 UI 구역 위젯들의 배치를 갱신합니다."""
        self.add_area_btn.pack_forget()
        for i, area_num in enumerate(self.controller.area_order):
            if area_num in self.area_widgets:
                widgets = self.area_widgets[area_num]
                # 순서 번호 레이블 텍스트 갱신
                widgets['order_label'].config(text=f"{i+1}.")
                
                group = widgets['group']
                group.pack_forget()
                group.pack(fill=tk.BOTH, expand=True, pady=10)
        self.add_area_btn.pack(fill=tk.X, pady=10, padx=50)

    def remove_area_from_ui(self, area_number: int):
        """UI에서 특정 구역 위젯을 제거합니다."""
        if area_number in self.area_widgets:
            widgets = self.area_widgets[area_number]
            # 위젯 파괴
            widgets['group'].destroy()
            
            # 관리용 데이터 정리
            del self.area_widgets[area_number]
            del self.area_vars[area_number]
            if area_number in self.area_toggles:
                del self.area_toggles[area_number]
            
            # 스크롤 영역 갱신 (지연 실행하여 파괴된 위젯이 반영되도록 함)
            self.root.after(10, lambda: self.scrollable_canvas.configure(scrollregion=self.scrollable_canvas.bbox("all")))
            
            # 구역 삭제 후 나머지 구역들의 순서 번호 재정렬
            self.refresh_area_order()

    def flash_setting_change(self, state: str, duration_ms=150):
        """설정 변경 시 창 배경색을 잠시 변경하여 시각적 피드백을 줍니다."""
        self.update_window_bg(state)
        self.root.after(duration_ms, lambda: self.update_window_bg('default'))

    def update_window_bg(self, state: str):
        """창과 모든 자식 위젯의 배경색을 상태에 따라 업데이트합니다."""
        color = self.WINDOW_COLORS.get(state, self.WINDOW_COLORS['default'])
        self._set_bg_recursively(self.root, color)
        # 캔버스 내부에 있는 프레임은 일반적인 자식 위젯이 아니므로 별도 처리
        if self.scrollable_content_frame:
            self._set_bg_recursively(self.scrollable_content_frame, color)

    def _set_bg_recursively(self, widget, color):
        """지정된 위젯과 그 자식들의 배경색을 재귀적으로 설정합니다."""
        # 배경색을 변경할 위젯 타입들
        target_widgets = (tk.Frame, tk.LabelFrame, tk.Label, tk.Checkbutton, tk.Canvas, tk.Entry)

        try:
            if isinstance(widget, target_widgets):
                # 체크박스는 배경과 관련된 여러 속성을 함께 변경해야 자연스럽습니다.
                if isinstance(widget, tk.Checkbutton):
                    # Windows에서는 체크박스 배경색이 잘 적용되지 않는 문제가 있어 OS별로 다르게 처리합니다.
                    if sys.platform.startswith("win"):
                        # Windows: 시스템 기본 배경을 유지하고 글자색만 흰색으로 설정
                        widget.configure(fg='white')
                    else:
                        # macOS/Linux: 배경색을 테마에 맞게 설정
                        widget.configure(bg=color, activebackground=color, selectcolor=color)
                elif isinstance(widget, tk.Entry):
                    widget.configure(bg=color, disabledbackground=color)
                elif isinstance(widget, tk.Canvas):
                    # 색상 프리뷰 캔버스는 배경색 변경에서 제외합니다.
                    if "color_preview" not in str(widget):
                        widget.configure(bg=color, highlightthickness=0)
                else:
                    widget.configure(bg=color)
        except tk.TclError:
            # 'bg' 속성이 없는 위젯은 무시합니다.
            pass

        # 모든 자식 위젯에 대해 재귀적으로 함수를 호출합니다.
        for child in widget.winfo_children():
            self._set_bg_recursively(child, color)

    def _validate_tuple_input(self, P):
        """숫자, 괄호, 콤마, 공백만 허용하는 검증 함수"""
        return all(c in "0123456789(), " for c in P)

    def play_sound(self, count=1, interval_ms=150):
        """지정된 횟수만큼 시스템 비프음을 재생합니다."""
        for i in range(count):
            self.root.after(i * interval_ms, self.root.bell)

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

    def set_final_status(self, message: str):
        """검색 종료 시 최종 상태를 UI에 한 번에 업데이트합니다."""
        self.update_status(message)
        self.update_button_text("찾기(Shift x2 / ESC)")
        self.update_window_bg('default')

    def update_ui_from_controller(self):
        """컨트롤러의 현재 설정값으로 UI의 모든 변수를 업데이트합니다."""
        c = self.controller
        self.color_tolerance_var.set(str(c.color_tolerance))
        self.color_area_tolerance_var.set(str(c.color_area_tolerance))
        self.complete_delay_var.set(str(int(c.complete_click_delay * 100)))
        self.p1_var.set(str(c.p1))
        self.p2_var.set(str(c.p2))
        self.color_var.set(str(c.color))
        self.use_secondary_color_var.set(c.use_secondary_color)
        self.secondary_color_var.set(str(c.secondary_color))
        self.area_delay_var.set(str(int(c.area_delay * 100)))
        self.search_delay_var.set(str(int(c.search_delay * 100)))
        self.complete_coord_var.set(str(c.complete_coord))
        self.use_initial_search_var.set(c.use_initial_search)
        self.use_space_complete_var.set(c.use_space_complete)
        self.use_screen_activation_var.set(c.use_screen_activation)
        self.use_operation_check_var.set(c.use_operation_check)
        self.op_check_coord_var.set(str(c.op_check_coord))
        self.op_check_color_var.set(str(c.op_check_color))
        self.op_check_max_retries_var.set(str(c.op_check_max_retries))
        self.op_check_retry_interval_var.set(str(int(c.op_check_retry_interval * 100)))
        self.empty_coord_var.set(str(c.empty_coord))
        self.use_search_delay_var.set(c.use_search_delay)
        self.use_sequence_var.set(c.use_sequence)
        self.direction_var.set(self.SEARCH_DIRECTION_MAP[c.search_direction])
        self.total_duration_var.set(str(c.total_duration_sec))
        self.active_search_duration_var.set(str(c.active_search_duration_sec))
        self.wait_duration_var.set(str(c.wait_duration_sec))
        self.search_time_tolerance_var.set(str(c.search_time_tolerance_sec))

        for area_number, area_settings in c.areas.items():
            if area_number in self.area_vars:
                vars = self.area_vars[area_number]
                vars['name_var'].set(area_settings.get('name', f"구역 {area_number}"))
                vars['use_var'].set(area_settings['use'])
                vars['coord_var'].set(str(area_settings['click_coord']))
                vars['clicks_var'].set(str(area_settings['clicks']))
                vars['offset_var'].set(str(area_settings['offset']))
                vars['p1_var'].set(str(area_settings['p1']))
                vars['p2_var'].set(str(area_settings['p2']))
                vars['color_var'].set(str(area_settings['color']))
                vars['direction_var'].set(self.SEARCH_DIRECTION_MAP[area_settings['direction']])
                # UI 체크박스(True)는 컨트롤러 값(False)과 반대입니다.
                vars['use_area_bounds_var'].set(not area_settings['use_area_bounds'])
                vars['use_color_var'].set(not area_settings['use_color'])
                vars['use_direction_var'].   set(not area_settings['use_direction'])
        
        # '기본' 체크박스 상태에 따라 비활성화된 위젯들의 상태를 올바르게 갱신합니다.
        for toggle_func in self.global_toggles.values():
            toggle_func()
        for area_number, toggles in self.area_toggles.items():
            for toggle_func in toggles.values():
                toggle_func()
        self._toggle_area_settings_active()

    def _toggle_operation_check_state(self):
        """탐색 화면 정상 여부 확인 그룹 내의 위젯 상태를 체크박스에 따라 토글합니다."""
        # 글로벌 '구역 탐색'과 로컬 '정상 여부 확인'이 모두 활성화되어야 내부 위젯 활성화
        is_enabled = self.use_sequence_var.get() and self.use_operation_check_var.get()
        
        state = 'normal' if is_enabled else 'disabled'
        entry_bg = '#444444' if is_enabled else '#555555'
        fg_color = 'white' if is_enabled else '#666666'

        def set_state_inner(w):
            """내부 위젯의 상태를 재귀적으로 변경하는 헬퍼 함수"""
            try:
                if isinstance(w, (tk.Entry, tk.Button, tk.Checkbutton, tk.OptionMenu)):
                    w.config(state=state)
                if isinstance(w, tk.Entry):
                    w.config(disabledbackground=entry_bg)
                if isinstance(w, (tk.Label, tk.Checkbutton)):
                    w.config(fg=fg_color)
                for child in w.winfo_children():
                    set_state_inner(child)
            except tk.TclError:
                pass

        for parent in self.op_check_inner_widgets:
            set_state_inner(parent)

    def _toggle_search_delay_state(self):
        """탐색 딜레이 체크박스 상태에 따라 입력창의 활성화 여부를 토글합니다."""
        is_active = self.use_search_delay_var.get() and self.use_sequence_var.get()
        state = 'normal' if is_active else 'disabled'
        entry_bg = '#444444' if is_active else '#555555'
        fg_color = 'white' if is_active else '#666666'

        try:
            for child in self.search_delay_frame.winfo_children():
                if isinstance(child, tk.Entry):
                    child.config(state=state, disabledbackground=entry_bg)
                elif isinstance(child, tk.Label):
                    child.config(fg=fg_color)
        except tk.TclError:
            pass

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
                alpha = area_info.get('alpha', 0.9)
                text = area_info.get('text') # 영역에 표시할 텍스트

                if width > 0 and height > 0:
                    area_marker = tk.Toplevel(self.root)
                    area_marker.overrideredirect(True)
                    area_marker.geometry(f"{width}x{height}+{x}+{y}")
                    area_marker.configure(bg=color)
                    area_marker.attributes('-alpha', alpha)
                    area_marker.attributes('-topmost', True)

                    # 영역에 텍스트가 있으면, 우측 상단에 레이블 추가
                    if text:
                        label = tk.Label(area_marker, text=text, bg=color, fg='white', font=("Helvetica", 10, "bold"))
                        label.pack(side=tk.TOP, anchor=tk.NE, padx=5, pady=2)

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

    def _create_labeled_frame(self, parent, text, name=None):
        """제목이 있는 프레임을 생성합니다."""
        frame = tk.LabelFrame(parent, text=text, fg="white", padx=10, pady=5, relief=tk.SOLID, borderwidth=1, name=name)
        return frame

    def _create_split_container(self, parent, weights=[1, 1], min_widths=None, **pack_options):
        """
        지정된 가중치에 따라 여러 열로 나뉘는 컨테이너 프레임을 생성합니다.
        
        :param parent: 부모 위젯
        :param weights: 각 열의 가중치를 담은 리스트. 예: [2, 1] -> 왼쪽이 오른쪽보다 2배 넓음
        :param min_widths: 각 열의 최소 너비 리스트 (픽셀 단위). 기본값 80px.
        :param pack_options: 컨테이너의 pack() 메서드에 전달할 추가 옵션 (예: ipady, pady)
        :return: (컨테이너 프레임, [각 열의 프레임 리스트])
        """
        container = tk.Frame(parent)
        
        default_options = {'fill': tk.X, 'pady': 2, 'padx': 10}
        default_options.update(pack_options)
        container.pack(**default_options)

        frames = []
        for i, weight in enumerate(weights):
            # 최소 너비를 80에서 60으로 하향 조정하여 좁은 창에서도 유연하게 대응합니다.
            # 가로 폭이 좁아질 때 스크롤바 공간을 확보하기 위함입니다.
            mw = min_widths[i] if min_widths and i < len(min_widths) else 60
            container.grid_columnconfigure(i, weight=weight, minsize=mw)
            frame = tk.Frame(container)
            frame.grid(row=0, column=i, sticky=tk.EW, padx=(5 if i > 0 else 0, 0))
            frames.append(frame)
            
        return container, frames

    def _create_labeled_entry(self, parent, label_text, var):
        """레이블과 입력창으로 구성된 위젯 그룹을 생성합니다. (횟수, 오차 등)"""
        frame = tk.Frame(parent)
        tk.Label(frame, 
                 text=label_text, 
                 fg="white"
                 ).pack(side=tk.LEFT)
        tk.Entry(frame, 
                 textvariable=var, 
                 width=2, 
                 bg="#444444", 
                 fg="white", 
                 insertbackground='white', 
                 borderwidth=0, 
                 highlightthickness=0
                 ).pack(side=tk.LEFT, expand=True, fill=tk.X)
        return frame

    def _create_coordinate_selector(self, parent, var, button_text, command=None):
        """좌표값 표시 레이블과 선택 버튼으로 구성된 위젯 그룹을 생성하고, 위젯들을 반환합니다."""
        frame = tk.Frame(parent)
        label = tk.Entry(frame, 
                         bg="#444444", 
                         fg="white", 
                         insertbackground='white', 
                         textvariable=var, 
                         borderwidth=0, 
                         highlightthickness=0, 
                         width=2, 
                         validate="key", 
                         validatecommand=self.tuple_vcmd)
        label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        button = tk.Button(frame, 
                           text=button_text, 
                           activeforeground="white",
                           activebackground="#555555",
                           command=command)
        button.pack(side=tk.LEFT)
        return frame, label, button

    def _create_value_button_row(self, parent, var, button_text, command=None, show_preview=False):
        """값 표시 레이블과 선택 버튼으로 구성된 위젯 그룹을 생성합니다."""
        frame = tk.Frame(parent)
        if show_preview:
            self._create_color_preview(frame, var).pack(side=tk.LEFT, padx=(0, 5))

        tk.Entry(frame, 
                 textvariable=var, 
                 bg="#555555", 
                 fg="white", 
                 insertbackground='white', 
                 borderwidth=0, 
                 highlightthickness=0, 
                 width=12, 
                 validate="key", 
                 validatecommand=self.tuple_vcmd
                 ).pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Button(frame, 
                  text=button_text, 
                  bg="white", 
                  activeforeground="white", 
                  activebackground="#555555",
                  command=command).pack(side=tk.LEFT)
        return frame

    def _create_color_preview(self, parent, var):
        """색상 변수의 값을 실시간으로 보여주는 정사각형 프리뷰를 생성합니다."""
        # Entry 높이보다 약간 작은 16x16 사이즈의 캔버스 생성
        preview = tk.Canvas(parent, width=16, height=16, highlightthickness=1, 
                           highlightbackground="#555555", bd=0, name="color_preview")
        
        def update_preview(*args):
            try:
                rgb = ast.literal_eval(var.get())
                hex_color = '#%02x%02x%02x' % rgb[:3]
                preview.config(bg=hex_color)
            except:
                preview.config(bg="black")

        var.trace_add("write", update_preview)
        update_preview() # 초기화 시점 반영
        return preview

    def _create_toggleable_color_selector(self, parent, use_var, color_var, check_text, button_text, command):
        """체크박스로 활성화/비활성화되는 2순위 색상 선택 위젯 그룹을 생성합니다."""
        frame = tk.Frame(parent)
        
        color_label = tk.Entry(frame, 
                               textvariable=color_var, 
                               bg="#444444", 
                               fg="white", 
                               insertbackground='white', 
                               borderwidth=0, 
                               highlightthickness=0,
                               width=12, 
                               validate="key", 
                               validatecommand=self.tuple_vcmd)
        color_button = tk.Button(frame, 
                                 text=button_text,  
                                 activeforeground="white", 
                                 activebackground="#555555",
                                 command=command)
        
        def toggle_state():
            is_enabled = use_var.get()
            state = 'normal' if is_enabled else 'disabled'
            label_bg = '#555555'
            label_fg = 'white' if is_enabled else '#2e2e2e'

            entry_bg = '#444444' if is_enabled else '#555555'

            color_label.config(state=state, bg=label_bg, fg=label_fg, disabledbackground=entry_bg)
            color_button.config(state=state)
        
        checkbox = tk.Checkbutton(frame, 
                                  text=check_text, 
                                  variable=use_var, 
                                  fg="white", 
                                  selectcolor="#2e2e2e", 
                                  activebackground="#2e2e2e", 
                                  highlightthickness=0, 
                                  command=toggle_state)
        checkbox.pack(side=tk.LEFT)
        self._create_color_preview(frame, color_var).pack(side=tk.LEFT, padx=(0, 5))
        
        color_label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        color_button.pack(side=tk.LEFT)
        
        toggle_state() # 위젯 생성 후 초기 상태를 설정하기 위해 호출합니다.
        
        return frame, toggle_state

    def _toggle_area_settings_active(self):
        """'구역 탐색 사용' 체크박스 상태에 따라 모든 구역 설정 UI의 활성화/비활성화 상태를 변경합니다."""
        is_enabled = self.use_sequence_var.get()
        state = 'normal' if is_enabled else 'disabled'
        group_fg = 'white' if is_enabled else '#666666'
        check_fg = 'white' if is_enabled else '#444444'
        entry_bg = '#444444' if is_enabled else '#2e2e2e'
        label_bg = '#555555' if is_enabled else '#2e2e2e'
        label_fg = 'white' if is_enabled else '#444444'


        # '구역 설정' 그룹 전체의 스타일 변경
        # 이 그룹에 속한 모든 위젯을 재귀적으로 탐색하며 상태를 변경하는 함수
        def set_state_recursive(widget, state, fg_color, entry_bg_color):
            try:
                if isinstance(widget, (tk.Button, tk.Entry, tk.OptionMenu, tk.Checkbutton)):
                    widget.config(state=state)
                if isinstance(widget, tk.Entry):
                    widget.config(disabledbackground=entry_bg_color)
                if isinstance(widget, (tk.Label, tk.Checkbutton, tk.LabelFrame)):
                    widget.config(fg=fg_color)
                
                for child in widget.winfo_children():
                    set_state_recursive(child, state, fg_color, entry_bg_color)
            except tk.TclError:
                pass # 위젯이 파괴된 경우 등 예외 처리

        self.areas_header_label.config(fg='white')

        # '구역 설정' 그룹 내의 공통 위젯들 상태 변경
        set_state_recursive(self.total_duration_frame, state, group_fg, entry_bg)
        set_state_recursive(self.active_search_duration_frame, state, group_fg, entry_bg)
        set_state_recursive(self.wait_duration_frame, state, group_fg, entry_bg)
        set_state_recursive(self.search_time_tolerance_frame, state, group_fg, entry_bg)
        set_state_recursive(self.search_delay_frame, state, group_fg, entry_bg)
        self.search_delay_check.config(state=state)
        self._toggle_search_delay_state()
        set_state_recursive(self.area_delay_frame, state, group_fg, entry_bg)
        set_state_recursive(self.empty_coord_frame, state, group_fg, entry_bg)
        self.screen_activation_check.config(state=state, fg=check_fg)
        
        # '탐색 화면 정상 여부 확인' 그룹 상태 변경
        set_state_recursive(self.operation_check_group, state, group_fg, entry_bg)
        self.op_check_cb.config(state=state)
        self.op_check_label.config(fg=group_fg)
        self.add_area_btn.config(state=state)

        # 각 구역의 모든 위젯 상태 변경
        for area_number, widgets in self.area_widgets.items():
            widgets['group'].config(fg=group_fg)
            widgets['use_search_check'].config(state=state, fg=check_fg)
            widgets['use_bounds_check'].config(state=state, fg=check_fg)
            widgets['use_color_check'].config(state=state, fg=check_fg)
            widgets['use_direction_check'].config(state=state, fg=check_fg)
            widgets['direction_menu'].config(state=state)

            # '탐색' 체크박스가 꺼져있으면 개별 위젯 상태는 그대로 두되,
            # '구역 탐색 사용'이 꺼져있으면 강제로 비활성화
            if not is_enabled:
                for widget_key, widget in widgets.items():
                    if 'frame' in widget_key:
                        for sub_widget in widget.winfo_children():
                            if isinstance(sub_widget, tk.Entry): sub_widget.config(state='disabled', disabledbackground=entry_bg)
                            else: sub_widget.config(state='disabled')
                    elif isinstance(widget, tk.Entry):
                        widget.config(state='disabled', bg=label_bg, fg=label_fg, disabledbackground=entry_bg)
                    elif isinstance(widget, (tk.Button, tk.OptionMenu)):
                        widget.config(state='disabled')
                    elif isinstance(widget, tk.Label):
                        widget.config(fg=label_fg)
            else:
                # '구역 탐색 사용'이 켜지면, 삭제 버튼은 항상 활성화하고 나머지 개별 상태를 다시 적용
                widgets['name_entry'].config(state='normal', bg='#444444', fg='white')
                widgets['order_label'].config(fg='white')
                widgets['delete_button'].config(state='normal')
                widgets['up_button'].config(state='normal')
                widgets['down_button'].config(state='normal')
                self.area_toggles[area_number]['search']()
                self.area_toggles[area_number]['bounds']()
                self.area_toggles[area_number]['color']()
                self.area_toggles[area_number]['direction']()
