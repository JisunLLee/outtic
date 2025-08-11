import tkinter as tk
from tkinter import ttk

class AppUI:
    """
    애플리케이션의 모든 UI 요소 생성과 배치를 담당하는 클래스입니다.
    """
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self._initialize_vars()
        self._setup_ui()

    def _initialize_vars(self):
        """UI에 사용될 Tkinter 변수들을 초기화합니다."""
        # 임시 데이터로 변수 초기화
        self.color_tolerance_var = tk.StringVar(value="15") # 색상 오차
        self.color_area_tolerance_var = tk.StringVar(value="5") # 색상 영역 오차
        self.complete_delay_var = tk.StringVar(value="2") # 완료 딜레이
        self.p1_var = tk.StringVar(value="(88, 219)")
        self.p2_var = tk.StringVar(value="(398, 462)")
        self.color_var = tk.StringVar(value="(0, 204, 204)")
        self.complete_coord_var = tk.StringVar(value="(805, 704)") # 완료 좌표
        self.direction_var = tk.StringVar(value="→↓")
        self.use_sequence_var = tk.BooleanVar(value=True)
        self.total_tries_var = tk.StringVar(value="225")
        self.status_var = tk.StringVar(value="대기 중...")

    def _setup_ui(self):
        """메인 UI를 생성하고 배치합니다."""
        self.root.title("Auto Color Clicker")
        self.root.geometry("400x320")
        self.root.configure(bg="#2e2e2e")
        self.root.resizable(True, True)

        main_frame = tk.Frame(self.root, bg="#2e2e2e", padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 기본 설정 그룹 ---
        basic_group = self._create_labeled_frame(main_frame, "기본")
        basic_group.pack(fill=tk.X, pady=(0, 10))

        # Row 1: 색상오차, 완료 딜레이
        row1 = tk.Frame(basic_group, bg="#2e2e2e")
        row1.pack(fill=tk.X, pady=2)
        self._create_labeled_entry(row1, "색상오차:", self.color_tolerance_var).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        self._create_labeled_entry(row1, "색상영역 오차:", self.color_area_tolerance_var).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

        # Row 2: 영역 설정
        row2 = tk.Frame(basic_group, bg="#2e2e2e")
        row2.pack(fill=tk.X, pady=2)
        self._create_coordinate_selector(row2, self.p1_var, "↖영역").pack(side=tk.LEFT, expand=True, fill=tk.X)
        self._create_coordinate_selector(row2, self.p2_var, "↘영역").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(10, 0))

        # Row 3: 색상, 완료 
        row3 = tk.Frame(basic_group, bg="#2e2e2e")
        row3.pack(fill=tk.X, pady=2)
        self._create_value_button_row(row3, self.color_var, "색상").pack(side=tk.LEFT, expand=True, fill=tk.X)
        self._create_value_button_row(row3, self.color_var, "완료").pack(side=tk.LEFT, expand=True, fill=tk.X)

        
        # Row 4: 구역 사용, 총 시도횟수, 탐색 방향
        row4 = tk.Frame(basic_group, bg="#2e2e2e")
        row4.pack(fill=tk.X, pady=2)
        tk.Checkbutton(row4, text="구역", variable=self.use_sequence_var, bg="#2e2e2e", fg="white", selectcolor="#2e2e2e", activebackground="#2e2e2e", highlightthickness=0).pack(side=tk.LEFT)
        self._create_labeled_entry(row4, "총 시도횟수:", self.total_tries_var).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(10, 0))
        self._create_labeled_entry(row4, "딜레이:", self.complete_delay_var).pack(side=tk.LEFT, expand=True, fill=tk.X)
        # OptionMenu 스타일링
        direction_menu = tk.OptionMenu(row4, self.direction_var, "→↓", "←↓", "→↑", "←↑")
        direction_menu.config(bg="#555555", fg="white", activebackground="#666666", activeforeground="white", highlightthickness=0, borderwidth=1)
        direction_menu["menu"].config(bg="#555555", fg="white")
        direction_menu.pack(side=tk.LEFT, padx=(10, 0))

        # --- 상태 메시지 ---
        status_label = tk.Label(main_frame, textvariable=self.status_var, fg="lightblue", bg="#2e2e2e", anchor='w')
        status_label.pack(fill=tk.X, pady=5)

        # --- 액션 버튼 ---
        action_frame = tk.Frame(main_frame, bg="#2e2e2e")
        action_frame.pack(fill=tk.X, side=tk.BOTTOM)
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(1, weight=1)
        tk.Button(action_frame, text="영역확인").grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))
        tk.Button(action_frame, text="찾기(caps+ESC)").grid(row=0, column=1, sticky=tk.EW, padx=(5, 0))

    # --- UI 생성을 위한 헬퍼 메서드 ---
    def _create_labeled_frame(self, parent, text):
        """제목이 있는 프레임을 생성합니다."""
        frame = tk.LabelFrame(parent, text=text, fg="white", bg="#2e2e2e", padx=10, pady=5, relief=tk.SOLID, borderwidth=1)
        return frame

    def _create_labeled_entry(self, parent, label_text, var):
        """레이블과 입력창으로 구성된 위젯 그룹을 생성합니다."""
        frame = tk.Frame(parent, bg="#2e2e2e")
        tk.Label(frame, text=label_text, fg="white", bg="#2e2e2e").pack(side=tk.LEFT)
        tk.Entry(frame, textvariable=var, width=5, bg="#444444", fg="white", insertbackground='white', borderwidth=0, highlightthickness=0).pack(side=tk.LEFT, expand=True, fill=tk.X)
        return frame

    def _create_coordinate_selector(self, parent, var, button_text):
        """좌표값 표시 레이블과 선택 버튼으로 구성된 위젯 그룹을 생성합니다."""
        frame = tk.Frame(parent, bg="#2e2e2e")
        tk.Label(frame, textvariable=var, relief="sunken", bg="white", width=10, anchor='w').pack(side=tk.LEFT)
        tk.Button(frame, text=button_text).pack(side=tk.LEFT, padx=(5, 0))
        return frame

    def _create_value_button_row(self, parent, var, button_text):
        """값 표시 레이블과 선택 버튼으로 구성된 위젯 그룹을 생성합니다."""
        frame = tk.Frame(parent, bg="#2e2e2e")
        tk.Label(frame, textvariable=var, relief="sunken", bg="white", width=10, anchor='w').pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Button(frame, text=button_text).pack(side=tk.LEFT, padx=(5, 0))
        return frame
