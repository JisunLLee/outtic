import tkinter as tk
from tkinter import ttk

from .color_finder import SearchDirection

class AutwaiUI:
    """
    Autwai 애플리케이션의 UI를 생성하고 관리하는 클래스입니다.
    """
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self.WINDOW_COLORS = {
            'default': root.cget('bg'), # 시스템 기본 배경색 저장
            'flash': "#d8e6ff",  # 좌표/색상 지정 시 사용할 밝은 파란색
            'searching': 'LemonChiffon' # 실행 중 배경색
        }
        self._initialize_vars()
        self._setup_ui()

    def _initialize_vars(self):
        """UI에 사용될 Tkinter 변수들을 초기화합니다."""
        self.color_var = tk.StringVar(value="(124, 104, 238)")
        self.p1_var = tk.StringVar(value="(267, 195)")
        self.p2_var = tk.StringVar(value="(313, 274)")
        self.color_tolerance_var = tk.StringVar(value="35")
        
        self.SEARCH_DIRECTION_MAP = {
            "→↓": SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT,
            "←↓": SearchDirection.TOP_RIGHT_TO_BOTTOM_LEFT,
            "→↑": SearchDirection.BOTTOM_LEFT_TO_TOP_RIGHT,
            "←↑": SearchDirection.BOTTOM_RIGHT_TO_TOP_LEFT,
        }
        self.direction_var = tk.StringVar(value="←↓") # 기본값
        
        self.button_delay_var = tk.StringVar(value="10")
        
        self.quantity_option_var = tk.StringVar(value="direct") # "1", "2", "direct"
        self.use_area_var = tk.BooleanVar(value=True)
        self.area_coord_var = tk.StringVar(value="(315, 391)")
        self.apply_coord_var = tk.StringVar(value="(770, 403)")
        
        self.status_var = tk.StringVar(value="대기 중...")

    def _setup_ui(self):
        """메인 UI를 생성하고 배치합니다."""
        self.root.title("Autwai")

        window_width = 500
        window_height = 230 # UI 재배치에 따라 높이 조정

        # 화면 크기를 정확히 가져오기 위해 update_idletasks()를 호출합니다.
        self.root.update_idletasks()
        screen_height = self.root.winfo_screenheight()

        # 창을 모니터 왼쪽 하단에 위치시킵니다.
        x_pos = 0 # 왼쪽 여백
        y_pos = screen_height - window_height - 40 # 작업표시줄 등을 고려한 하단 여백
        self.root.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")

        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 상단 컨테이너 (설정 그룹과 동작 순서 그룹을 담을 프레임) ---
        top_container = tk.Frame(main_frame)
        top_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # --- 설정 그룹 (왼쪽) ---
        settings_group = tk.LabelFrame(top_container, text="탐색 설정", padx=10, pady=10)
        settings_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # --- 동작 순서 그룹 (오른쪽) ---
        actions_group = tk.LabelFrame(top_container, text="동작 순서", padx=10, pady=10)
        actions_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- 설정 그룹 위젯 배치 ---
        # Row 1: 색상
        self._create_value_button_row(
            settings_group, 
            self.color_var, 
            "색상", 
            command=lambda: self.controller.start_color_picker('main_color')
        ).pack(fill=tk.X, pady=2)

        # Row 2 & 3: 영역
        self._create_coordinate_selector(
            settings_group, 
            self.p1_var, 
            "↖영역", 
            command=lambda: self.controller.start_coordinate_picker('p1')
        ).pack(fill=tk.X, pady=2)
        self._create_coordinate_selector(
            settings_group, 
            self.p2_var, 
            "↘영역", 
            command=lambda: self.controller.start_coordinate_picker('p2')
        ).pack(fill=tk.X, pady=2)

        # Row 4: 색상오차, 탐색방향
        options_frame1 = tk.Frame(settings_group)
        options_frame1.pack(fill=tk.X)
        
        self._create_labeled_entry(options_frame1, "색상오차:", self.color_tolerance_var, 3).pack(side=tk.LEFT, padx=(0, 5))        
        tk.Label(options_frame1, text="탐색방향:").pack(side=tk.LEFT)
        direction_menu = tk.OptionMenu(options_frame1, self.direction_var, *self.SEARCH_DIRECTION_MAP.keys())
        direction_menu.pack(side=tk.LEFT, padx=(0, 5))

        # --- 동작 순서 그룹 위젯 배치 ---
        # 수량 선택
        quantity_frame = tk.Frame(actions_group)
        quantity_frame.pack(fill=tk.X, pady=2, anchor='w')
        tk.Radiobutton(quantity_frame, text="수량1", variable=self.quantity_option_var, value="1").pack(side=tk.LEFT)
        tk.Radiobutton(quantity_frame, text="수량2", variable=self.quantity_option_var, value="2").pack(side=tk.LEFT)
        tk.Radiobutton(quantity_frame, text="직접입력", variable=self.quantity_option_var, value="direct").pack(side=tk.LEFT)

        # 구역
        area_frame = tk.Frame(actions_group)
        area_frame.pack(fill=tk.X, pady=2)
        tk.Checkbutton(area_frame, variable=self.use_area_var).pack(side=tk.LEFT)
        self._create_coordinate_selector(
            area_frame,
            self.area_coord_var,
            "구역",
            command=lambda: self.controller.start_coordinate_picker('area')
        ).pack(expand=True, fill=tk.X)

        # 신청
        self._create_coordinate_selector(
            actions_group, 
            self.apply_coord_var, 
            "신청", 
            command=lambda: self.controller.start_coordinate_picker('apply')
        ).pack(fill=tk.X, pady=(0, 2), padx=(5, 0))

        # 버튼 딜레이
        self._create_labeled_entry(actions_group, "버튼딜레이:", self.button_delay_var, 3).pack(side=tk.LEFT, padx=(5, 0))
        
        # --- 상태 및 실행 버튼 ---
        bottom_frame = tk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X)
        bottom_frame.grid_columnconfigure(0, weight=2) # 상태 메시지가 2/3 공간 차지
        bottom_frame.grid_columnconfigure(1, weight=1) # 버튼들이 1/3 공간 차지

        # 상태 메시지 레이블 (왼쪽)
        status_label = tk.Label(bottom_frame, textvariable=self.status_var, fg="lightblue", anchor='w')
        status_label.grid(row=0, column=0, sticky=tk.EW, padx=(0, 10))

        # 액션 버튼들을 담을 프레임 (오른쪽)
        action_buttons_frame = tk.Frame(bottom_frame)
        action_buttons_frame.grid(row=0, column=1, sticky=tk.EW)
        action_buttons_frame.grid_columnconfigure(0, weight=1)
        action_buttons_frame.grid_columnconfigure(1, weight=1)

        self.area_button = tk.Button(action_buttons_frame, text="영역확인", command=None) # self.controller.show_area
        self.area_button.grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))
        
        self.run_button = tk.Button(action_buttons_frame, text="실행(Shift x2)", command=None) # self.controller.toggle_run
        self.run_button.grid(row=0, column=1, sticky=tk.EW)

    def _create_labeled_entry(self, parent, label_text, var, entry_width=5):
        frame = tk.Frame(parent)
        tk.Label(frame, text=label_text).pack(side=tk.LEFT)
        tk.Entry(frame, textvariable=var, width=entry_width).pack(side=tk.LEFT, expand=True, fill=tk.X)
        return frame

    def _create_coordinate_selector(self, parent, var, button_text, command=None):
        frame = tk.Frame(parent)
        label = tk.Label(frame, textvariable=var, relief="sunken", width=10, anchor='w')
        label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        button = tk.Button(frame, text=button_text, width=5, command=command)
        button.pack(side=tk.LEFT, padx=(5,0))

        return frame

    def _create_value_button_row(self, parent, var, button_text, command=None):
        frame = tk.Frame(parent)
        tk.Label(frame, textvariable=var, relief="sunken", width=12, anchor='w').pack(
            side=tk.LEFT, expand=True, fill=tk.X)
        tk.Button(frame, text=button_text, width=5, command=command).pack(side=tk.LEFT, padx=(5,0))
        return frame

    def update_window_bg(self, state: str):
        """창과 모든 자식 위젯의 배경색을 상태에 따라 업데이트합니다."""
        color = self.WINDOW_COLORS.get(state, self.WINDOW_COLORS['default'])
        self._set_bg_recursively(self.root, color)

    def flash_window(self, duration_ms=150):
        """설정 변경 시 창 배경색을 잠시 변경하여 시각적 피드백을 줍니다."""
        original_color = self.WINDOW_COLORS['default']
        flash_color = self.WINDOW_COLORS['flash']
        
        self._set_bg_recursively(self.root, flash_color)
        self.root.after(duration_ms, lambda: self._set_bg_recursively(self.root, original_color))

    def _set_bg_recursively(self, widget, color):
        """지정된 위젯과 그 자식들의 배경색을 재귀적으로 설정합니다."""
        # 배경색을 변경할 위젯 타입들
        target_widgets = (tk.Frame, tk.LabelFrame, tk.Label, tk.Checkbutton)

        try:
            if isinstance(widget, target_widgets):
                # 체크박스는 배경과 관련된 여러 속성을 함께 변경해야 자연스럽습니다.
                if isinstance(widget, tk.Checkbutton):
                    widget.configure(bg=color, activebackground=color)
                else:
                    widget.configure(bg=color)
        except tk.TclError:
            # 'bg' 속성이 없는 위젯(예: ttk 위젯)은 무시합니다.
            pass

        # 모든 자식 위젯에 대해 재귀적으로 함수를 호출합니다.
        for child in widget.winfo_children():
            self._set_bg_recursively(child, color)