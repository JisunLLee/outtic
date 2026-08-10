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
        self.initial_area_widgets = {} # 기본 탐색 영역별 위젯을 저장하기 위한 딕셔너리
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
        self.color_var = tk.StringVar(value=str(c.color))
        self.use_secondary_color_var = tk.BooleanVar(value=c.use_secondary_color)
        self.secondary_color_var = tk.StringVar(value=str(c.secondary_color))
        self.use_search_delay_var = tk.BooleanVar(value=c.use_search_delay)
        self.area_delay_var = tk.StringVar(value=str(int(c.area_delay * 100)))
        self.search_delay_var = tk.StringVar(value=str(int(c.search_delay * 100)))
        self.complete_coord_var = tk.StringVar(value=str(c.complete_coord))
        self.use_initial_search_var = tk.BooleanVar(value=c.use_initial_search)
        self.continuous_search_var = tk.BooleanVar(value=c.continuous_search)
        self.research_delay_var = tk.StringVar(value=str(int(c.research_delay * 1000)))
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
        self.total_duration_var = tk.StringVar(value=str(c.total_duration_sec))
        self.active_search_duration_var = tk.StringVar(value=str(c.active_search_duration_sec))
        self.wait_duration_var = tk.StringVar(value=str(c.wait_duration_sec))
        self.search_time_tolerance_var = tk.StringVar(value=str(c.search_time_tolerance_sec))
        self.status_var = tk.StringVar(value="대기 중...")

        # 전역 색상 변경 시 '기본' 체크된 구역 색상을 동기화하기 위한 트레이스 등록 (중복 방지를 위해 여기에서 한 번만 설정)
        self.color_var.trace_add('write', self._sync_global_to_areas)

        # --- 창 색상 관리 ---
        self.WINDOW_COLORS = {
            'default': "#252525",
            'searching': "medium turquoise",
            'waiting': "orange",
            'global_setting_change': "#40E0D0",
            'area_setting_change': "LemonChiffon",
        }
        
        # --- 기본 탐색 영역 목록 변수 초기화 ---
        self.initial_area_vars = {}
        for area_id in c.initial_area_order:
            self._initialize_initial_area_vars(area_id)

        # --- 구역별 변수 초기화 ---
        for i in range(1, 6):
            self._initialize_area_vars(i)

    def _initialize_initial_area_vars(self, area_id: int):
        """기본 탐색 영역 목록의 영역 하나에 대한 Tkinter 변수들을 초기화하고 저장합니다."""
        defaults = self.controller.initial_areas[area_id]
        self.initial_area_vars[area_id] = {
            'order_var': tk.StringVar(),
            'p1_var': tk.StringVar(value=str(defaults['p1'])),
            'p2_var': tk.StringVar(value=str(defaults['p2'])),
            'direction_var': tk.StringVar(value=self.SEARCH_DIRECTION_MAP[defaults['direction']]),
        }

    def _initialize_area_vars(self, area_number: int):
        """지정된 번호의 구역에 대한 Tkinter 변수들을 초기화하고 저장합니다."""
        # 컨트롤러에 미리 정의된 구역별 기본값을 가져옵니다.
        area_defaults = self.controller.areas[area_number]

        self.area_vars[area_number] = {
            'order_var': tk.StringVar(),
            'name_var': tk.StringVar(value=area_defaults.get('name', f"구역{area_number}")),
            'use_var': tk.BooleanVar(value=area_defaults['use']),
            'coord_var': tk.StringVar(value=str(area_defaults['click_coord'])),
            'clicks_var': tk.StringVar(value=str(area_defaults['clicks'])),
            'offset_var': tk.StringVar(value=str(area_defaults['offset'])),
            'color_var': tk.StringVar(value=str(area_defaults['color'])),
            # '기본' 체크박스는 컨트롤러 값과 논리가 반대입니다. (UI 체크 True == 컨트롤러 use_color False)
            'use_color_var': tk.BooleanVar(value=not area_defaults['use_color']),
            'sub_area_vars': {},
            'sub_area_widgets': {},
        }
        for sub_id in area_defaults['sub_area_order']:
            self._initialize_subarea_vars(area_number, sub_id)

    def _initialize_subarea_vars(self, area_number: int, sub_id: int):
        """지정된 구역의 영역(sub-area) 하나에 대한 Tkinter 변수들을 초기화하고 저장합니다."""
        sub_defaults = self.controller.areas[area_number]['sub_areas'][sub_id]
        self.area_vars[area_number]['sub_area_vars'][sub_id] = {
            'order_var': tk.StringVar(),
            'p1_var': tk.StringVar(value=str(sub_defaults['p1'])),
            'p2_var': tk.StringVar(value=str(sub_defaults['p2'])),
            'direction_var': tk.StringVar(value=self.SEARCH_DIRECTION_MAP[sub_defaults['direction']]),
        }

    def _setup_ui(self):
        """메인 UI를 생성하고 배치합니다."""
        self.root.title("루오틱 For 유리지연 v.3.2.0")

        window_width = 400
        # 4개의 구역이 모두 보이도록 창 높이 설정합니다.
        window_height = 940

        # 화면의 너비를 가져옵니다.
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 창을 모니터 오른쪽 상단에 위치시킵니다.
        x_pos = screen_width - window_width
        y_pos = 0 # 상단 여백

        self.root.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")
        self.root.resizable(True, True)

        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 기본 설정 그룹 ---
        basic_group = self._create_labeled_frame(main_frame, "기본", name="basic_group")
        basic_group.pack(fill=tk.X, pady=(0, 10))

        # Row 1: 기본 탐색 영역 목록 (순서대로 탐색, 못 찾으면 다음 영역으로)
        self._create_initial_area_list(basic_group)

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
      
        # Part 2: 완료 선택 딜레이
        self._create_labeled_entry(right_frame, "완료 딜레이:", self.complete_delay_var).pack(expand=True, fill=tk.X, side=tk.LEFT)

        # --- 상태 메시지 및 구역/기본 탐색 토글 ---
        status_and_toggle_container = tk.Frame(main_frame)
        status_and_toggle_container.pack(fill=tk.X, pady=2)

        # --- 구역, 기본 탐색 사용 여부 ---
        toggle_frame = tk.Frame(status_and_toggle_container)
        toggle_frame.pack(fill=tk.X)

        toggle_row1 = tk.Frame(toggle_frame)
        toggle_row1.pack(fill=tk.X)
        tk.Checkbutton(toggle_row1, text="기본 탐색 사용", variable=self.use_initial_search_var, fg="white", selectcolor="#2e2e2e", activebackground="#2e2e2e", highlightthickness=0).pack(side=tk.LEFT)
        tk.Checkbutton(toggle_row1, text="스페이스완료", variable=self.use_space_complete_var, fg="white", selectcolor="#2e2e2e", activebackground="#2e2e2e", highlightthickness=0).pack(side=tk.LEFT, padx=(10,0))

        toggle_row2 = tk.Frame(toggle_frame)
        toggle_row2.pack(fill=tk.X, pady=(2,0))
        tk.Checkbutton(toggle_row2, text="연속 찾기 모드", variable=self.continuous_search_var, fg="white", selectcolor="#2e2e2e", activebackground="#2e2e2e", highlightthickness=0).pack(side=tk.LEFT)
        tk.Label(toggle_row2, text="재탐색:", fg="white").pack(side=tk.LEFT, padx=(10,2))
        tk.Entry(toggle_row2, textvariable=self.research_delay_var, width=5, justify='center', bg="#444444", fg="white", insertbackground="white", borderwidth=0, highlightthickness=0).pack(side=tk.LEFT)
        tk.Label(toggle_row2, text="ms", fg="gray").pack(side=tk.LEFT, padx=(2,0))
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
        self.operation_check_group.pack(fill=tk.X, pady=12, ipady=5)

        # Row 1: 화면 정상 여부 확인: 화면 확인 좌표, 화면 확인 색상
        operation_check_container, (left_frame, right_frame) = self._create_split_container(self.operation_check_group, weights=[1, 1])
        
        # 좌표 입력창 (통합 버튼 사용을 위해 버튼 없는 Entry 배치)
        tk.Entry(left_frame, textvariable=self.op_check_coord_var, bg="#444444", fg="white", 
                 insertbackground='white', borderwidth=0, highlightthickness=0, width=12,
                 validate="key", validatecommand=self.tuple_vcmd).pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        # 색상 입력창 + 통합 버튼
        self._create_color_preview(right_frame, self.op_check_color_var).pack(side=tk.LEFT, padx=(0, 5))

        tk.Entry(right_frame, textvariable=self.op_check_color_var, bg="#444444", fg="white", 
                 insertbackground='white', borderwidth=0, highlightthickness=0, width=12,
                 validate="key", validatecommand=self.tuple_vcmd).pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.op_check_combined_btn = tk.Button(right_frame, text="좌표&색상", 
                                               activeforeground="white", activebackground="#555555",
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
            # 캔버스 너비가 변하면 내부 프레임 너비도 동적으로 조절 (스크롤바 간섭 방지 여유 4px 제외)
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
        self.add_area_btn = tk.Button(self.scrollable_content_frame, text="+ 구역 추가", command=self.controller.add_area)
        self.add_area_btn.pack(fill=tk.X, pady=10, padx=50)

        # --- 액션 버튼 ---
        action_frame = tk.Frame(main_frame)
        action_frame.pack(fill=tk.X)
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(1, weight=1)
        action_frame.grid_columnconfigure(2, weight=1)
        action_frame.grid_columnconfigure(3, weight=1)

        self.load_button = tk.Button(action_frame, text="불러오기", 
                                     activeforeground="white", activebackground="#555555",
                                     command=self.controller.load_settings)
        self.load_button.grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))
        self.save_button = tk.Button(action_frame, text="저장하기", 
                                     activeforeground="white", activebackground="#555555",
                                     command=self.controller.save_settings)
        self.save_button.grid(row=0, column=1, sticky=tk.EW, padx=(0, 5))

        self.area_button = tk.Button(action_frame, text="영역확인", 
                                     activeforeground="white", activebackground="#555555",
                                     command=self.controller.show_area)
        self.area_button.grid(row=0, column=2, sticky=tk.EW, padx=(0, 5))
        
        self.find_button = tk.Button(action_frame, text="찾기(Shift x2 / ESC)", 
                                     activeforeground="white", activebackground="#555555",
                                     command=self.controller.toggle_search)
        self.find_button.grid(row=0, column=3, sticky=tk.EW)

        # UI가 모두 생성된 후, 오버레이의 초기 상태를 설정합니다.
        self.refresh_area_order()

        # 모든 위젯이 생성된 뒤에 배경색을 적용해야 전체 화면이 처음부터 어둡게 표시됩니다.
        # (위젯 생성 전에 호출하면 그 시점에 존재하는 위젯이 없어 아무 효과가 없습니다.)
        self.update_window_bg('default')

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

        # 드래그 핸들 (☰)
        drag_handle = tk.Label(header_frame, text="☰", fg="white", font=(None, 10), cursor="fleur")
        drag_handle.pack(side=tk.LEFT, padx=(2, 0), pady=(0,3))  
        drag_handle.bind("<Button-1>", lambda e: self._on_area_drag_start(e, area_number))
        drag_handle.bind("<B1-Motion>", lambda e: self._on_area_drag_motion(e, area_number))
        drag_handle.bind("<ButtonRelease-1>", lambda e: self._on_area_drag_release(e, area_number))

        # 순서 번호를 선택 가능한 OptionMenu로 변경
        order_var = self.area_vars[area_number]['order_var']
        order_var.set(str(order_idx))
        
        # 초기 메뉴 생성 (옵션은 refresh_area_order에서 채워짐)
        order_menu = tk.OptionMenu(header_frame, order_var, str(order_idx))
        order_menu.config(fg="#005A9E", bg="white", 
                          font=(None, 8, "bold"), borderwidth=1, highlightthickness=0, 
                          indicatoron=False, padx=2, pady=0, width=2, relief=tk.FLAT)
        order_menu["menu"].config(bg="white", fg="black") 
        order_menu.pack(side=tk.LEFT, padx=(2, 0))

        tk.Label(header_frame, text=".", fg="white", font=(None, 9, "bold")).pack(side=tk.LEFT)

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
        delete_button = tk.Button(header_frame, text="삭제", fg="#f58585", activeforeground="red", 
                                  font=(None, 8), pady=0,
                                  command=lambda: self.controller.remove_area(area_number))
        delete_button.pack(side=tk.LEFT)

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
        right_inner_frame.pack(padx=5)
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

        coord_button.pack(side=tk.RIGHT)
        coord_label.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

        # --- Row 1 오른쪽: 선택 횟수, 오차 설정 ---
        right_inner_frame.pack(fill=tk.X)
        clicks_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
        offset_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # --- Row 2: 구역 내 영역(sub-area) 목록 ---
        # 위에서부터 순서대로 탐색하며, 앞 영역에서 색을 못 찾으면 다음 영역으로 넘어갑니다.
        subareas_frame = self._create_subarea_list(area_group, area_number)

        # --- Row 3: 구역 색상 설정 ---
        color_row = tk.Frame(area_group)
        color_row.pack(fill=tk.X, expand=True, pady=(4, 0))

        # --- 색상 사용, 색상 값, 색상 선택 버튼 ---
        color_label = tk.Entry(color_row,
                               textvariable=vars['color_var'], 
                               insertbackground='white', 
                               borderwidth=0, 
                               highlightthickness=0, 
                               validate="key",
                               validatecommand=self.tuple_vcmd)
        color_button = tk.Button(color_row, text="색상",
                                 activeforeground="white",
                                 activebackground="#555555",
                                 command=lambda: self.controller.start_color_picker(f'area_{area_number}_color'))

        def toggle_color_state():
            """'기본' 체크박스 상태에 따라 색상 위젯들을 활성화/비활성화하고 값을 동기화합니다."""
            # '기본'이 체크되면(True), 개별 설정 위젯은 비활성화됩니다.
            use_default_color = vars['use_color_var'].get()
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

        use_color_checkbutton = tk.Checkbutton(color_row,
                                               text="기본",
                                               variable=vars['use_color_var'],
                                               fg="white",
                                               selectcolor="#2e2e2e",
                                               activebackground="#2e2e2e",
                                               highlightthickness=0,
                                               command=toggle_color_state)
        use_color_checkbutton.pack(side=tk.LEFT)
        self._create_color_preview(color_row, vars['color_var']).pack(side=tk.LEFT, padx=(0, 5))
        color_button.pack(side=tk.RIGHT)
        color_label.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # 나중에 전체 활성/비활성화를 위해 위젯들을 저장합니다.
        widgets['group'] = area_group
        widgets['use_search_check'] = use_search_checkbutton
        widgets['delete_button'] = delete_button
        widgets['drag_handle'] = drag_handle
        widgets['name_entry'] = name_entry
        widgets['order_menu'] = order_menu
        widgets['coord_label'] = coord_label
        widgets['coord_button'] = coord_button
        widgets['clicks_frame'] = clicks_frame
        widgets['offset_frame'] = offset_frame
        widgets['subareas_frame'] = subareas_frame
        widgets['use_color_check'] = use_color_checkbutton
        widgets['color_label'] = color_label
        widgets['color_button'] = color_button
        self.area_widgets[area_number] = widgets

        # --- 전역 변수 변경 감지 및 동기화 ---
        # 전역 색상이 변경될 때, '기본'이 체크된 구역의 색상도 함께 업데이트합니다.
        def update_area_color_from_global(*args):
            if vars['use_color_var'].get():
                vars['color_var'].set(self.color_var.get())

        self.color_var.trace_add('write', update_area_color_from_global)

        # 토글 함수들을 나중에 UI 업데이트 시 사용하기 위해 저장합니다.
        self.area_toggles[area_number] = {
            'search': toggle_search_state,
            'color': toggle_color_state,
        }

        toggle_search_state() # 초기 상태 설정
        toggle_color_state() # 초기 상태 설정을 위해 호출

        return area_group

    def _create_subarea_list(self, parent, area_number: int):
        """
        구역 내 영역(sub-area) 목록 UI를 생성합니다.
        위에서부터 순서대로 탐색하며, 앞 영역에서 색을 못 찾으면 다음 영역으로 넘어갑니다.
        """
        outer = tk.Frame(parent, highlightbackground="#4a4a4a", highlightthickness=1)
        outer.pack(fill=tk.X, expand=True, pady=(6, 0))

        tk.Label(outer, text="영역 목록 (순서대로 탐색)", fg="#999999", font=(None, 8)).pack(anchor=tk.W, padx=4, pady=(2, 0))

        rows_container = tk.Frame(outer)
        rows_container.pack(fill=tk.X, expand=True, padx=2)

        add_btn = tk.Button(outer, text="+ 영역 추가", font=(None, 8),
                            command=lambda: self.controller.add_sub_area(area_number))
        add_btn.pack(fill=tk.X, padx=4, pady=4)

        self.area_vars[area_number]['subarea_rows_container'] = rows_container
        self.area_vars[area_number]['add_subarea_btn'] = add_btn

        for sub_id in self.controller.areas[area_number]['sub_area_order']:
            self._create_subarea_row(rows_container, area_number, sub_id)

        self.refresh_subarea_order(area_number)
        return outer

    def _create_subarea_row(self, parent, area_number: int, sub_id: int):
        """구역 내 영역(sub-area) 하나를 나타내는 한 줄짜리 컴팩트 행을 생성합니다."""
        sub_vars = self.area_vars[area_number]['sub_area_vars'][sub_id]

        row = tk.Frame(parent)
        row.pack(fill=tk.X, expand=True, pady=1)

        drag_handle = tk.Label(row, text="☰", fg="white", font=(None, 8), cursor="fleur")
        drag_handle.pack(side=tk.LEFT, padx=(0, 2))
        drag_handle.bind("<Button-1>", lambda e: self._on_subarea_drag_start(e, area_number, sub_id))
        drag_handle.bind("<B1-Motion>", lambda e: self._on_subarea_drag_motion(e, area_number, sub_id))
        drag_handle.bind("<ButtonRelease-1>", lambda e: self._on_subarea_drag_release(e, area_number, sub_id))

        order_label = tk.Label(row, textvariable=sub_vars['order_var'], fg="#999999", font=(None, 8), width=2)
        order_label.pack(side=tk.LEFT)

        p1_frame, _, _ = self._create_compact_coord_button(
            row, sub_vars['p1_var'], "↖",
            command=lambda: self.controller.start_coordinate_picker(f'area_{area_number}_sub_{sub_id}_p1'))
        p1_frame.pack(side=tk.LEFT)

        p2_frame, _, _ = self._create_compact_coord_button(
            row, sub_vars['p2_var'], "↘",
            command=lambda: self.controller.start_coordinate_picker(f'area_{area_number}_sub_{sub_id}_p2'))
        p2_frame.pack(side=tk.LEFT, padx=(3, 0))

        # 가변 공백: 방향 선택을 행의 오른쪽 끝으로 밀어줍니다.
        tk.Frame(row).pack(side=tk.LEFT, expand=True, fill=tk.X)

        direction_menu = tk.OptionMenu(row, sub_vars['direction_var'], *self.SEARCH_DIRECTION_MAP.values())
        direction_menu.config(fg="white", bg="#555555", activebackground="#666666", activeforeground="white",
                              highlightthickness=0, borderwidth=1, font=(None, 8), padx=2, pady=0)
        direction_menu["menu"].config(bg="#555555", fg="white")
        direction_menu.pack(side=tk.LEFT) # expand/fill 없이 글자 폭에 맞춰서만 배치

        delete_button = tk.Button(row, text="×", fg="#f58585", activeforeground="red",
                                  font=(None, 9), padx=3, pady=0,
                                  command=lambda: self.controller.remove_sub_area(area_number, sub_id))
        delete_button.pack(side=tk.LEFT, padx=(3, 0))

        self.area_vars[area_number]['sub_area_widgets'][sub_id] = {
            'row': row,
            'drag_handle': drag_handle,
            'order_label': order_label,
            'delete_button': delete_button,
        }
        return row

    def _create_initial_area_list(self, parent):
        """
        기본 탐색 영역 목록 UI를 생성합니다.
        위에서부터 순서대로 탐색하며, 앞 영역에서 색을 못 찾으면 다음 영역으로 넘어갑니다.
        """
        outer = tk.Frame(parent, highlightbackground="#4a4a4a", highlightthickness=1)
        outer.pack(fill=tk.X, expand=True, pady=(0, 6))

        tk.Label(outer, text="탐색 영역 목록 (순서대로 탐색)", fg="#999999", font=(None, 8)).pack(anchor=tk.W, padx=4, pady=(2, 0))

        self.initial_area_rows_container = tk.Frame(outer)
        self.initial_area_rows_container.pack(fill=tk.X, expand=True, padx=2)

        self.add_initial_area_btn = tk.Button(outer, text="+ 영역 추가", font=(None, 8),
                                              command=lambda: self.controller.add_initial_area())
        self.add_initial_area_btn.pack(fill=tk.X, padx=4, pady=4)

        for area_id in self.controller.initial_area_order:
            self._create_initial_area_row(self.initial_area_rows_container, area_id)

        self.refresh_initial_area_order()
        return outer

    def _create_initial_area_row(self, parent, area_id: int):
        """기본 탐색 영역 하나를 나타내는 한 줄짜리 컴팩트 행을 생성합니다."""
        area_vars = self.initial_area_vars[area_id]

        row = tk.Frame(parent)
        row.pack(fill=tk.X, expand=True, pady=1)

        drag_handle = tk.Label(row, text="☰", fg="white", font=(None, 8), cursor="fleur")
        drag_handle.pack(side=tk.LEFT, padx=(0, 2))
        drag_handle.bind("<Button-1>", lambda e: self._on_initial_area_drag_start(e, area_id))
        drag_handle.bind("<B1-Motion>", lambda e: self._on_initial_area_drag_motion(e, area_id))
        drag_handle.bind("<ButtonRelease-1>", lambda e: self._on_initial_area_drag_release(e, area_id))

        order_label = tk.Label(row, textvariable=area_vars['order_var'], fg="#999999", font=(None, 8), width=2)
        order_label.pack(side=tk.LEFT)

        p1_frame, _, _ = self._create_compact_coord_button(
            row, area_vars['p1_var'], "↖",
            command=lambda: self.controller.start_coordinate_picker(f'initial_{area_id}_p1'))
        p1_frame.pack(side=tk.LEFT)

        p2_frame, _, _ = self._create_compact_coord_button(
            row, area_vars['p2_var'], "↘",
            command=lambda: self.controller.start_coordinate_picker(f'initial_{area_id}_p2'))
        p2_frame.pack(side=tk.LEFT, padx=(3, 0))

        # 가변 공백: 방향 선택을 행의 오른쪽 끝으로 밀어줍니다.
        tk.Frame(row).pack(side=tk.LEFT, expand=True, fill=tk.X)

        direction_menu = tk.OptionMenu(row, area_vars['direction_var'], *self.SEARCH_DIRECTION_MAP.values())
        direction_menu.config(fg="white", bg="#555555", activebackground="#666666", activeforeground="white",
                              highlightthickness=0, borderwidth=1, font=(None, 8), padx=2, pady=0)
        direction_menu["menu"].config(bg="#555555", fg="white")
        direction_menu.pack(side=tk.LEFT) # expand/fill 없이 글자 폭에 맞춰서만 배치

        delete_button = tk.Button(row, text="×", fg="#f58585", activeforeground="red",
                                  font=(None, 9), padx=3, pady=0,
                                  command=lambda: self.controller.remove_initial_area(area_id))
        delete_button.pack(side=tk.LEFT, padx=(3, 0))

        self.initial_area_widgets[area_id] = {
            'row': row,
            'drag_handle': drag_handle,
            'order_label': order_label,
            'delete_button': delete_button,
        }
        return row

    def _sync_global_to_areas(self, *args):
        """전역 색상이 변경될 때, '기본'이 체크된 모든 구역의 색상 값을 안전하게 동기화합니다."""
        if not self.area_vars:
            return
        for area_num, v in self.area_vars.items():
            try:
                if v['use_color_var'].get():
                    v['color_var'].set(self.color_var.get())
            except (tk.TclError, KeyError):
                continue

    def add_area_to_ui(self, area_number: int):
        """새로운 구역 위젯을 UI 리스트 끝에 추가합니다."""
        if area_number not in self.area_vars:
            self._initialize_area_vars(area_number)
        
        self.add_area_btn.pack_forget() # 버튼을 잠시 가리고 아래에 다시 추가
        new_group = self._create_area_group(self.scrollable_content_frame, area_number)
        self.add_area_btn.pack(fill=tk.X, pady=10, padx=50)

        # 새로 만들어진 위젯은 아직 어두운 배경이 적용되지 않은 상태이므로 칠해줍니다.
        self._set_bg_recursively(new_group, self.WINDOW_COLORS['default'])

        # 새로 추가된 구역의 활성화 상태 동기화
        self._toggle_area_settings_active()

    def refresh_area_order(self):
        """컨트롤러의 area_order에 맞춰 UI 구역 위젯들의 배치를 갱신합니다."""
        self.add_area_btn.pack_forget()

        # 현재 UI에 존재하는 구역들만 대상으로 순서 리스트 필터링
        present_ids = [aid for aid in self.controller.area_order if aid in self.area_widgets]
        total_count = len(present_ids)
        choices = [str(i + 1) for i in range(total_count)]

        display_idx = 1

        for area_num in present_ids:
            w_set = self.area_widgets[area_num]
            self.area_vars[area_num]['order_var'].set(str(display_idx))
            w_set['drag_handle'].config(fg="white")

            # OptionMenu 메뉴 아이템 재구성
            menu = w_set['order_menu']['menu']
            menu.delete(0, 'end')
            
            # 클로저 문제를 피하기 위해 내부 함수 정의
            def make_reorder_cmd(target_idx, an=area_num):
                return lambda: self.controller.reorder_area(an, target_idx)

            for i, choice in enumerate(choices):
                menu.add_command(label=choice, command=make_reorder_cmd(i))

            group = w_set['group']
            group.pack_forget()
            group.pack(fill=tk.BOTH, expand=True, pady=10)
            display_idx += 1
                
                
        self.add_area_btn.pack(fill=tk.X, pady=10, padx=50)

    def reset_areas_ui(self):
        """현재 생성된 모든 구역 UI 위젯을 제거하고 데이터를 초기화합니다."""
        for widgets in self.area_widgets.values():
            widgets['group'].destroy()
        
        self.area_widgets = {}
        self.area_vars = {}
        self.area_toggles = {}
        self.scrollable_canvas.yview_moveto(0)

    def _on_area_drag_start(self, event, area_num):
        """드래그 시작 시 시각적 피드백 제공."""
        if area_num in self.area_widgets:
            self.area_widgets[area_num]['drag_handle'].config(fg="#40E0D0") # 핸들 색상 변경

    def _on_area_drag_motion(self, event, area_num):
        """드래그 중 마우스 위치를 추적하여 삽입 위치 가이드 라인을 표시합니다."""
        y_cursor = event.y_root
        
        # 가이드 라인 생성 (처음 한 번만)
        if not hasattr(self, 'drag_guide'):
            self.drag_guide = tk.Frame(self.scrollable_content_frame, height=3, bg="#40E0D0", bd=0)

        # 각 구역의 위치 정보 수집
        y_positions = []
        for a_num in self.controller.area_order:
            if a_num in self.area_widgets:
                group = self.area_widgets[a_num]['group']
                y_top = group.winfo_rooty()
                y_bottom = y_top + group.winfo_height()
                y_positions.append((y_top, y_bottom))
        
        if not y_positions: return

        # 마우스 위치에 따른 삽입 좌표 결정 (가장 가까운 경계면)
        insert_y = y_positions[0][0] - self.scrollable_content_frame.winfo_rooty()
        for top, bottom in y_positions:
            if y_cursor > (top + bottom) // 2:
                insert_y = bottom - self.scrollable_content_frame.winfo_rooty() + 5 # 패딩 보정
        
        self.drag_guide.place(x=0, y=insert_y, relwidth=1)
        self.drag_guide.lift()

    def _on_area_drag_release(self, event, area_num):
        """드래그 종료 시 가이드 라인을 숨기고 새로운 순서를 결정합니다."""
        if hasattr(self, 'drag_guide'):
            self.drag_guide.place_forget()

        # 위젯들의 현재 화면 위치 정보를 정확히 가져오기 위해 레이아웃 갱신
        self.root.update_idletasks()

        y_cursor = event.y_root
        
        # 현재 드래그 중인 구역을 제외한 나머지 구역들의 중앙 Y 좌표 수집
        centers = []
        for a_num in self.controller.area_order:
            if a_num != area_num and a_num in self.area_widgets:
                group = self.area_widgets[a_num]['group']
                center_y = group.winfo_rooty() + (group.winfo_height() // 2)
                centers.append(center_y)
        
        # 마우스 위치가 몇 번째 '슬롯'에 있는지 계산
        new_index = 0
        for c_y in centers:
            if y_cursor > c_y:
                new_index += 1
        
        self.controller.reorder_area(area_num, new_index)

    def add_subarea_to_ui(self, area_number: int):
        """새로운 영역(sub-area) 위젯을 해당 구역의 영역 목록 끝에 추가합니다."""
        area_vars = self.area_vars[area_number]
        new_sub_ids = [sid for sid in self.controller.areas[area_number]['sub_area_order'] if sid not in area_vars['sub_area_vars']]
        for sub_id in new_sub_ids:
            self._initialize_subarea_vars(area_number, sub_id)

        add_btn = area_vars['add_subarea_btn']
        add_btn.pack_forget() # 버튼을 잠시 가리고 아래에 다시 추가
        for sub_id in new_sub_ids:
            new_row = self._create_subarea_row(area_vars['subarea_rows_container'], area_number, sub_id)
            # 새로 만들어진 위젯은 아직 어두운 배경이 적용되지 않은 상태이므로 칠해줍니다.
            self._set_bg_recursively(new_row, self.WINDOW_COLORS['default'])
        add_btn.pack(fill=tk.X, padx=4, pady=4)

        self.refresh_subarea_order(area_number)
        self._toggle_area_settings_active()

    def refresh_subarea_order(self, area_number: int):
        """컨트롤러의 sub_area_order에 맞춰 영역 행들의 배치와 순서 번호를 갱신합니다."""
        area_vars = self.area_vars[area_number]
        sub_widgets = area_vars['sub_area_widgets']
        present_ids = [sid for sid in self.controller.areas[area_number]['sub_area_order'] if sid in sub_widgets]

        for display_idx, sub_id in enumerate(present_ids, start=1):
            area_vars['sub_area_vars'][sub_id]['order_var'].set(str(display_idx))
            w_set = sub_widgets[sub_id]
            w_set['drag_handle'].config(fg="white")
            row = w_set['row']
            row.pack_forget()
            row.pack(fill=tk.X, expand=True, pady=1)

    def _on_subarea_drag_start(self, event, area_number, sub_id):
        """영역 행 드래그 시작 시 시각적 피드백 제공."""
        sub_widgets = self.area_vars[area_number]['sub_area_widgets']
        if sub_id in sub_widgets:
            sub_widgets[sub_id]['drag_handle'].config(fg="#40E0D0")

    def _on_subarea_drag_motion(self, event, area_number, sub_id):
        """영역 행 드래그 중 마우스 위치를 추적하여 삽입 위치 가이드 라인을 표시합니다."""
        rows_container = self.area_vars[area_number]['subarea_rows_container']
        y_cursor = event.y_root

        if not hasattr(self, 'subarea_drag_guide'):
            self.subarea_drag_guide = tk.Frame(rows_container, height=2, bg="#40E0D0", bd=0)

        sub_widgets = self.area_vars[area_number]['sub_area_widgets']
        y_positions = []
        for sid in self.controller.areas[area_number]['sub_area_order']:
            if sid in sub_widgets:
                row = sub_widgets[sid]['row']
                y_top = row.winfo_rooty()
                y_bottom = y_top + row.winfo_height()
                y_positions.append((y_top, y_bottom))

        if not y_positions: return

        insert_y = y_positions[0][0] - rows_container.winfo_rooty()
        for top, bottom in y_positions:
            if y_cursor > (top + bottom) // 2:
                insert_y = bottom - rows_container.winfo_rooty()

        self.subarea_drag_guide.place(in_=rows_container, x=0, y=insert_y, relwidth=1)
        self.subarea_drag_guide.lift()

    def _on_subarea_drag_release(self, event, area_number, sub_id):
        """영역 행 드래그 종료 시 가이드 라인을 숨기고 새로운 순서를 결정합니다."""
        if hasattr(self, 'subarea_drag_guide'):
            self.subarea_drag_guide.place_forget()

        self.root.update_idletasks()

        y_cursor = event.y_root
        sub_widgets = self.area_vars[area_number]['sub_area_widgets']

        centers = []
        for sid in self.controller.areas[area_number]['sub_area_order']:
            if sid != sub_id and sid in sub_widgets:
                row = sub_widgets[sid]['row']
                center_y = row.winfo_rooty() + (row.winfo_height() // 2)
                centers.append(center_y)

        new_index = 0
        for c_y in centers:
            if y_cursor > c_y:
                new_index += 1

        self.controller.reorder_sub_area(area_number, sub_id, new_index)

    def remove_subarea_from_ui(self, area_number: int, sub_id: int):
        """UI에서 특정 구역의 영역(sub-area) 행을 제거합니다."""
        area_vars = self.area_vars[area_number]
        if sub_id in area_vars['sub_area_widgets']:
            area_vars['sub_area_widgets'][sub_id]['row'].destroy()
            del area_vars['sub_area_widgets'][sub_id]
            del area_vars['sub_area_vars'][sub_id]
            self.refresh_subarea_order(area_number)

    def add_initial_area_to_ui(self):
        """새로운 기본 탐색 영역 위젯을 목록 끝에 추가합니다."""
        new_area_ids = [aid for aid in self.controller.initial_area_order if aid not in self.initial_area_vars]
        for area_id in new_area_ids:
            self._initialize_initial_area_vars(area_id)

        self.add_initial_area_btn.pack_forget() # 버튼을 잠시 가리고 아래에 다시 추가
        for area_id in new_area_ids:
            new_row = self._create_initial_area_row(self.initial_area_rows_container, area_id)
            # 새로 만들어진 위젯은 아직 어두운 배경이 적용되지 않은 상태이므로 칠해줍니다.
            self._set_bg_recursively(new_row, self.WINDOW_COLORS['default'])
        self.add_initial_area_btn.pack(fill=tk.X, padx=4, pady=4)

        self.refresh_initial_area_order()

    def refresh_initial_area_order(self):
        """컨트롤러의 initial_area_order에 맞춰 영역 행들의 배치와 순서 번호를 갱신합니다."""
        present_ids = [aid for aid in self.controller.initial_area_order if aid in self.initial_area_widgets]

        for display_idx, area_id in enumerate(present_ids, start=1):
            self.initial_area_vars[area_id]['order_var'].set(str(display_idx))
            w_set = self.initial_area_widgets[area_id]
            w_set['drag_handle'].config(fg="white")
            row = w_set['row']
            row.pack_forget()
            row.pack(fill=tk.X, expand=True, pady=1)

    def _on_initial_area_drag_start(self, event, area_id):
        """기본 탐색 영역 행 드래그 시작 시 시각적 피드백 제공."""
        if area_id in self.initial_area_widgets:
            self.initial_area_widgets[area_id]['drag_handle'].config(fg="#40E0D0")

    def _on_initial_area_drag_motion(self, event, area_id):
        """기본 탐색 영역 행 드래그 중 마우스 위치를 추적하여 삽입 위치 가이드 라인을 표시합니다."""
        rows_container = self.initial_area_rows_container
        y_cursor = event.y_root

        if not hasattr(self, 'initial_area_drag_guide'):
            self.initial_area_drag_guide = tk.Frame(rows_container, height=2, bg="#40E0D0", bd=0)

        y_positions = []
        for aid in self.controller.initial_area_order:
            if aid in self.initial_area_widgets:
                row = self.initial_area_widgets[aid]['row']
                y_top = row.winfo_rooty()
                y_bottom = y_top + row.winfo_height()
                y_positions.append((y_top, y_bottom))

        if not y_positions: return

        insert_y = y_positions[0][0] - rows_container.winfo_rooty()
        for top, bottom in y_positions:
            if y_cursor > (top + bottom) // 2:
                insert_y = bottom - rows_container.winfo_rooty()

        self.initial_area_drag_guide.place(in_=rows_container, x=0, y=insert_y, relwidth=1)
        self.initial_area_drag_guide.lift()

    def _on_initial_area_drag_release(self, event, area_id):
        """기본 탐색 영역 행 드래그 종료 시 가이드 라인을 숨기고 새로운 순서를 결정합니다."""
        if hasattr(self, 'initial_area_drag_guide'):
            self.initial_area_drag_guide.place_forget()

        self.root.update_idletasks()

        y_cursor = event.y_root

        centers = []
        for aid in self.controller.initial_area_order:
            if aid != area_id and aid in self.initial_area_widgets:
                row = self.initial_area_widgets[aid]['row']
                center_y = row.winfo_rooty() + (row.winfo_height() // 2)
                centers.append(center_y)

        new_index = 0
        for c_y in centers:
            if y_cursor > c_y:
                new_index += 1

        self.controller.reorder_initial_area(area_id, new_index)

    def remove_initial_area_from_ui(self, area_id: int):
        """UI에서 특정 기본 탐색 영역 행을 제거합니다."""
        if area_id in self.initial_area_widgets:
            self.initial_area_widgets[area_id]['row'].destroy()
            del self.initial_area_widgets[area_id]
            del self.initial_area_vars[area_id]
            self.refresh_initial_area_order()

    def reset_initial_areas_ui(self):
        """현재 생성된 모든 기본 탐색 영역 행 위젯을 제거하고 데이터를 초기화합니다."""
        for widgets in self.initial_area_widgets.values():
            widgets['row'].destroy()
        self.initial_area_widgets = {}
        self.initial_area_vars = {}

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
                    if sys.platform.startswith("win"):
                        # Windows: 배경색뿐 아니라 highlight 관련 속성도 함께 지정해야
                        # 체크박스 주변에 흰 테두리/배경이 남지 않습니다.
                        widget.configure(fg='white', bg=color, activebackground=color, selectcolor=color,
                                         highlightbackground=color, highlightcolor=color, highlightthickness=0)
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

    def show_temporary_status(self, text: str, duration_ms: int = 1500):
        """상태 메시지를 일시적으로 변경한 후 이전 상태로 복구합니다."""
        previous_status = self.status_var.get()
        self.status_var.set(text)
        
        def restore():
            # 메시지가 그 사이 다른 기능에 의해 변경되지 않은 경우에만 복구합니다.
            if self.status_var.get() == text:
                self.status_var.set(previous_status)
        
        self.root.after(duration_ms, restore)

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
        self.color_var.set(str(c.color))
        self.use_secondary_color_var.set(c.use_secondary_color)
        self.secondary_color_var.set(str(c.secondary_color))
        self.area_delay_var.set(str(int(c.area_delay * 100)))
        self.search_delay_var.set(str(int(c.search_delay * 100)))
        self.complete_coord_var.set(str(c.complete_coord))
        self.use_initial_search_var.set(c.use_initial_search)
        self.continuous_search_var.set(c.continuous_search)
        self.research_delay_var.set(str(int(c.research_delay * 1000)))
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
        self.total_duration_var.set(str(c.total_duration_sec))
        self.active_search_duration_var.set(str(c.active_search_duration_sec))
        self.wait_duration_var.set(str(c.wait_duration_sec))
        self.search_time_tolerance_var.set(str(c.search_time_tolerance_sec))

        # 로드된 데이터에 맞춰 기본 탐색 영역 목록을 처음부터 다시 생성
        for area_id in c.initial_area_order:
            if area_id not in self.initial_area_vars:
                self._initialize_initial_area_vars(area_id)
            self._create_initial_area_row(self.initial_area_rows_container, area_id)
        self.refresh_initial_area_order()

        # 로드된 데이터에 맞춰 UI 구역을 처음부터 다시 생성
        for area_num in c.area_order:
            if area_num not in self.area_vars:
                self._initialize_area_vars(area_num)
            self._create_area_group(self.scrollable_content_frame, area_num)

        self.refresh_area_order()
        
        # '기본' 체크박스 상태에 따라 비활성화된 위젯들의 상태를 올바르게 갱신합니다.
        for toggle_func in self.global_toggles.values():
            toggle_func()
        for area_number, toggles in self.area_toggles.items():
            for toggle_func in toggles.values():
                toggle_func()
        self._toggle_area_settings_active()

        # 구역 위젯들을 이 시점에 새로 만들었기 때문에, 아직 어두운 배경이 적용되지 않은 상태입니다.
        # 다시 칠해서 화면 전체가 처음부터 어둡게 보이도록 합니다.
        self.update_window_bg('default')

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

    def _clear_visual_markers(self):
        """표시된 모든 시각적 보조 마커를 제거합니다."""
        for marker in self.area_marker_windows:
            if marker and marker.winfo_exists():
                marker.destroy()
        self.area_marker_windows.clear()

        for marker in self.point_marker_windows:
            if marker and marker.winfo_exists():
                marker.destroy()
        self.point_marker_windows.clear()

    def display_visual_aids(self, steps):
        """화면에 영역과 좌표 마커들을 그룹화하여 순차적으로 표시합니다."""
        # 기존 마커 창들 제거
        self._clear_visual_markers()

        def run_sequential_display(index):
            if index >= len(steps):
                self.update_status("영역 및 좌표 표시 완료 (3초 후 사라짐)")
                # 모든 마커가 표시된 후 3초 뒤에 한꺼번에 사라지도록 예약합니다.
                self.root.after(3000, self._clear_visual_markers)
                return
            
            # 현재 단계의 모든 마커(영역과 좌표 등)를 동시에 표시
            for item in steps[index]:
                item_type = item.get('type')
                if item_type == 'area':
                    self._show_single_area_marker(item)
                elif item_type == 'point':
                    self._show_single_point_marker(item)
            
            # 400ms 간격으로 다음 그룹 표시
            self.root.after(400, lambda: run_sequential_display(index + 1))

        self.update_status("순서대로 영역 확인 중...")
        run_sequential_display(0)

    def _show_single_area_marker(self, info):
        x, y, w, h = info.get('rect', (0,0,0,0))
        if w <= 0 or h <= 0: return
        m = tk.Toplevel(self.root)
        m.overrideredirect(True); m.geometry(f"{w}x{h}+{x}+{y}"); m.configure(bg=info.get('color', 'red'))
        m.attributes('-alpha', info.get('alpha', 0.3), '-topmost', True)
        if info.get('text'):
            tk.Label(m, text=info['text'], bg=m['bg'], fg='white', font=("Helvetica", 10, "bold")).pack(side=tk.TOP, anchor=tk.NE, padx=5, pady=2)
        self.area_marker_windows.append(m)

    def _show_single_point_marker(self, info):
        pos = info.get('pos')
        if not pos or pos == (0,0): return
        size = 20; px, py = pos; color = info.get('color', 'white')
        m = tk.Toplevel(self.root)
        m.overrideredirect(True); m.geometry(f"{size}x{size}+{px-size//2}+{py-size//2}")
        m.configure(bg=color, highlightthickness=1, highlightbackground="white")
        m.attributes('-alpha', 0.7, '-topmost', True)
        try:
            r, g, b = self.root.winfo_rgb(color)
            brightness = ((r * 299) + (g * 587) + (b * 114)) / 1000
            fg = "black" if brightness > 128000 else "white"
        except: fg = "black"
        tk.Label(m, text=info.get('text', ''), bg=color, fg=fg, font=("Helvetica", 8, "bold")).pack(expand=True, fill='both')
        self.point_marker_windows.append(m)

    def _create_labeled_frame(self, parent, text, name=None):
        """제목이 있는 프레임을 생성합니다."""
        frame = tk.LabelFrame(parent, text=text, fg="white", padx=10, pady=5, relief=tk.SOLID, borderwidth=1, name=name)
        return frame

    def _create_split_container(self, parent, weights=[1, 1], min_widths=None, **pack_options):
        """
        지정된 가중치에 따라 여러 열로 나뉘는 컨테이너 프레임을 생성합니다.
        
        :param parent: 부모 위젯
        :param weights: 각 열의 가중치를 담은 리스트. 예: [2, 1] -> 왼쪽이 오른쪽보다 2배 넓음
        :param min_widths: 각 열의 최소 너비 리스트. 기본값 60px.
        :param pack_options: 컨테이너의 pack() 메서드에 전달할 추가 옵션 (예: ipady, pady)
        :return: (컨테이너 프레임, [각 열의 프레임 리스트])
        """
        container = tk.Frame(parent)
        
        default_options = {'fill': tk.X, 'pady': 2}
        default_options.update(pack_options)
        container.pack(**default_options)

        frames = []
        for i, weight in enumerate(weights):
            # 가중치와 최소 너비(minsize)를 설정하여 반응형 레이아웃 구현
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
        button = tk.Button(frame, 
                           text=button_text, 
                           activeforeground="white",
                           activebackground="#555555",
                           command=command)
        button.pack(side=tk.RIGHT)
        label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        return frame, label, button

    def _create_compact_coord_button(self, parent, var, icon_text, command=None):
        """아이콘 버튼 바로 오른쪽에 좁은 좌표 입력창을 붙인 컴팩트 위젯을 생성합니다.
        (영역 목록처럼 한 행에 여러 항목을 촘촘히 배치할 때 사용)"""
        frame = tk.Frame(parent)
        button = tk.Button(frame,
                           text=icon_text,
                           font=(None, 8),
                           padx=2, pady=0,
                           activeforeground="white",
                           activebackground="#555555",
                           command=command)
        entry = tk.Entry(frame,
                         bg="#444444",
                         fg="white",
                         insertbackground='white',
                         textvariable=var,
                         borderwidth=0,
                         highlightthickness=0,
                         font=(None, 8),
                         width=9,
                         validate="key",
                         validatecommand=self.tuple_vcmd)
        button.pack(side=tk.LEFT)
        entry.pack(side=tk.LEFT)
        return frame, button, entry

    def _create_value_button_row(self, parent, var, button_text, command=None, show_preview=False):
        """값 표시 레이블과 선택 버튼으로 구성된 위젯 그룹을 생성합니다."""
        frame = tk.Frame(parent)
        if show_preview:
            self._create_color_preview(frame, var).pack(side=tk.LEFT, padx=(0, 5))

        tk.Button(frame, 
                  text=button_text, 
                  bg="white", 
                  activeforeground="white", 
                  activebackground="#555555",
                  command=command).pack(side=tk.RIGHT)

        tk.Entry(frame, 
                 textvariable=var, 
                 bg="#444444", 
                 fg="white", 
                 insertbackground='white', 
                 borderwidth=0, 
                 highlightthickness=0, 
                 width=12, 
                 validate="key", 
                 validatecommand=self.tuple_vcmd
                 ).pack(side=tk.LEFT, expand=True, fill=tk.X)

        return frame

    def _create_color_preview(self, parent, var):
        """색상 변수의 값을 실시간으로 보여주는 정사각형 프리뷰를 생성합니다."""
        # Entry 높이보다 약간 작은 16x16 사이즈의 캔버스 생성
        preview = tk.Canvas(parent, width=16, height=16, highlightthickness=1, 
                           highlightbackground="#555555", bd=0, name="color_preview")
        
        def update_preview(*args):
            try:
                # 위젯 존재 여부 확인 (TclError 방지)
                if not preview or not preview.winfo_exists():
                    return
                rgb = ast.literal_eval(var.get())
                hex_color = '#%02x%02x%02x' % rgb[:3]
                preview.config(bg=hex_color)
            except (tk.TclError, ValueError, SyntaxError):
                try:
                    if preview and preview.winfo_exists():
                        preview.config(bg="black")
                except tk.TclError:
                    pass

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
        color_button = tk.Button(frame, text=button_text, 
                                 activeforeground="white", activebackground="#555555",
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
        
        color_button.pack(side=tk.RIGHT)
        color_label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
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
            widgets['use_color_check'].config(state=state, fg=check_fg)

            # '탐색' 체크박스가 꺼져있으면 개별 위젯 상태는 그대로 두되,
            # '구역 탐색 사용'이 꺼져있으면 강제로 비활성화
            if not is_enabled:
                for widget_key, widget in widgets.items():
                    if 'frame' in widget_key:
                        # 영역 목록처럼 여러 단계로 중첩된 프레임도 안전하게 재귀적으로 비활성화합니다.
                        set_state_recursive(widget, 'disabled', label_fg, entry_bg)
                    elif isinstance(widget, tk.Entry):
                        widget.config(state='disabled', bg=label_bg, fg=label_fg, disabledbackground=entry_bg)
                    elif isinstance(widget, (tk.Button, tk.OptionMenu)):
                        widget.config(state='disabled')
                    elif isinstance(widget, tk.Label):
                        widget.config(fg=label_fg)
            else:
                # '구역 탐색 사용'이 켜지면, 삭제 버튼은 항상 활성화하고 나머지 개별 상태를 다시 적용
                widgets['name_entry'].config(state='normal', bg='#444444', fg='white')
                widgets['order_menu'].config(state='normal')
                widgets['drag_handle'].config(fg='white')
                widgets['delete_button'].config(state='normal')
                set_state_recursive(widgets['subareas_frame'], 'normal', group_fg, entry_bg)
                self.area_toggles[area_number]['search']()
                self.area_toggles[area_number]['color']()
