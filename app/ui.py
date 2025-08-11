import tkinter as tk
from tkinter import ttk

class AppUI:
    """
    애플리케이션의 모든 UI 요소 생성과 배치를 담당하는 클래스입니다.
    """
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self.area_marker_windows = []
        self.point_marker_windows = []
        self._initialize_vars()
        self._setup_ui()

    def _initialize_vars(self):
        """UI에 사용될 Tkinter 변수들을 초기화합니다."""
        c = self.controller
        self.color_tolerance_var = tk.StringVar(value="15") # 색상 오차
        self.color_area_tolerance_var = tk.StringVar(value="5") # 색영역 오차
        self.complete_delay_var = tk.StringVar(value="2") # 완료 딜레이
        self.p1_var = tk.StringVar(value=str(c.p1))
        self.p2_var = tk.StringVar(value=str(c.p2))
        self.color_var = tk.StringVar(value=str(c.color))
        self.complete_coord_var = tk.StringVar(value=str(c.complete_coord)) # 완료 좌표
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

        # Row 1: 색상오차, 색상영역 오차
        # 예시: 왼쪽 프레임이 오른쪽 프레임보다 2배 더 넓게 설정 (2:1 비율)
        row1_container, (left_frame, right_frame) = self._create_split_container(basic_group, weights=[1, 1])
        self._create_labeled_entry(left_frame, "색상오차:", self.color_tolerance_var).pack(expand=True, fill=tk.X)
        self._create_labeled_entry(right_frame, "색영역오차:", self.color_area_tolerance_var).pack(expand=True, fill=tk.X)

        # Row 2: 영역 설정
        row2_container, (left_frame, right_frame) = self._create_split_container(
            basic_group, weights=[1, 1], expand=True)
        self._create_coordinate_selector(
            left_frame, self.p1_var, "↖영역", command=lambda: self.controller.start_coordinate_picker('p1')
        ).pack(expand=True, fill=tk.X)
        self._create_coordinate_selector(
            right_frame, self.p2_var, "↘영역", command=lambda: self.controller.start_coordinate_picker('p2')
        ).pack(expand=True, fill=tk.X)

        # Row 3: 색상, 완료 
        row3_container, (left_frame, right_frame) = self._create_split_container(basic_group, weights=[1, 1])
        self._create_value_button_row(left_frame, self.color_var, "색상", command=lambda: self.controller.start_color_picker('main_color')).pack(expand=True, fill=tk.X)
        self._create_value_button_row(right_frame, self.complete_coord_var, "선택완료", command=lambda: self.controller.start_coordinate_picker('complete')).pack(expand=True, fill=tk.X)

        
        # Row 4: 구역 사용, 총 시도횟수, 탐색 방향
  
        row4_container, (left_frame, right_frame) = self._create_split_container(basic_group, weights=[1, 1])
        tk.Checkbutton(left_frame, text="구역 사용  |", variable=self.use_sequence_var, bg="#2e2e2e", fg="white", selectcolor="#2e2e2e", activebackground="#2e2e2e", highlightthickness=0).pack(side=tk.LEFT)
        self._create_labeled_entry(left_frame, "총 시도횟수:", self.total_tries_var).pack(side=tk.LEFT, expand=True, fill=tk.X)
        self._create_labeled_entry(right_frame, "|  딜레이:", self.complete_delay_var).pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        # OptionMenu 스타일링
        direction_menu = tk.OptionMenu(right_frame, self.direction_var, "→↓", "←↓", "→↑", "←↑")
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
        tk.Button(action_frame, text="영역확인", command=self.controller.show_area).grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))
        tk.Button(action_frame, text="찾기(caps+ESC)").grid(row=0, column=1, sticky=tk.EW, padx=(5, 0))

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
            color_map = {
                '완료': '#50E3C2', # Teal
            }
            for text, pos in points.items():
                if not pos or (pos[0] == 0 and pos[1] == 0): continue
                
                px, py = pos
                marker_color = color_map.get(text, "#FFFFFF") # 기본값은 흰색
                marker = tk.Toplevel(self.root)
                marker.overrideredirect(True)
                marker.geometry(f"{marker_size}x{marker_size}+{px - marker_size//2}+{py - marker_size//2}")
                marker.configure(bg=marker_color, highlightthickness=1, highlightbackground="white")
                marker.attributes('-alpha', 0.7)
                marker.attributes('-topmost', True)
                tk.Label(marker, text=text, bg=marker_color, fg="white", font=("Helvetica", 8, "bold")).pack(expand=True, fill='both')
                marker.after(3000, marker.destroy)
                self.point_marker_windows.append(marker)

        self.update_status(f"영역 및 좌표 표시 중...")

    # --- UI 생성을 위한 헬퍼 메서드 ---
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

        # grid를 사용하여 레이블이 잘리지 않도록 합니다.
        frame.grid_columnconfigure(1, weight=1) # 입력창이 확장되도록 설정

        label = tk.Label(frame, text=label_text, fg="white", bg="#2e2e2e")
        label.grid(row=0, column=0, sticky="w", padx=(0, 5))

        entry = tk.Entry(frame, textvariable=var, width=5, bg="#444444", fg="white", insertbackground='white', borderwidth=0, highlightthickness=0)
        entry.grid(row=0, column=1, sticky="ew")
        return frame

    def _create_coordinate_selector(self, parent, var, button_text, command=None):
        """좌표값 표시 레이블과 선택 버튼으로 구성된 위젯 그룹을 생성합니다."""
        frame = tk.Frame(parent, bg="#2e2e2e")
        tk.Label(frame, textvariable=var, relief="sunken", bg="white", width=10,anchor='w').pack(
            side=tk.LEFT, expand=True, fill=tk.X)
        tk.Button(frame, text=button_text, width=3, command=command).pack(
            side=tk.LEFT)
        return frame

    def _create_value_button_row(self, parent, var, button_text, command=None):
        """값 표시 레이블과 선택 버튼으로 구성된 위젯 그룹을 생성합니다."""
        frame = tk.Frame(parent, bg="#2e2e2e")
        tk.Label(frame, textvariable=var, relief="sunken", bg="white", width=10, anchor='w').pack(
            side=tk.LEFT, expand=True, fill=tk.X)
        tk.Button(frame, text=button_text, width=3, command=command).pack(
            side=tk.LEFT)
        return frame
