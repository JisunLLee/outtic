import tkinter as tk
import threading
import time
import ast
from typing import Optional, TYPE_CHECKING

from pynput import mouse, keyboard
from PIL import ImageGrab

from .color_finder import ColorFinder, SearchDirection

if TYPE_CHECKING:
    from .autwai_ui import AutwaiUI

class AutwaiController:
    """
    Autwai 애플리케이션의 모든 로직과 상태를 관리합니다.
    UI와 상호작용하며, 핵심 기능을 실행합니다.
    """
    def __init__(self):
        self.ui: Optional['AutwaiUI'] = None
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()
        self.color_finder = ColorFinder()

        # --- 상태 변수 ---
        self.is_running = False
        self.run_thread: Optional[threading.Thread] = None
        self.area_markers = []
        self.shift_press_count = 0
        self.shift_press_timer: Optional[threading.Timer] = None

        # --- 전역 단축키 설정 ---
        # Shift 키의 연속 입력을 감지하기 위해 pynput의 일반 Listener를 사용합니다.
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
        self.keyboard_listener.start()

        # --- 설정값 (apply_settings에서 UI로부터 값을 받아 채워짐) ---
        self.color = (0, 0, 0)
        self.p1 = (0, 0)
        self.p2 = (0, 0)
        self.color_tolerance = 0
        self.search_direction = SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT
        self.button_delay_ms = 0
        self.quantity_option = "1"
        self.use_area = True
        self.area_coord = (0, 0)
        self.apply_coord = (0, 0)

    def set_ui(self, ui: 'AutwaiUI'):
        """UI 인스턴스를 컨트롤러에 연결하고, UI 이벤트를 컨트롤러 메서드에 바인딩합니다."""
        self.ui = ui
        self.ui.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # UI의 버튼 커맨드를 컨트롤러의 메서드와 연결합니다.
        self.ui.run_button.config(command=self.toggle_run)
        self.ui.area_button.config(command=self.show_area)
        
        # 참고: 색상/좌표 선택 버튼의 command는 autwai_ui.py 파일 내에서
        # 주석 처리된 부분을 해제하여 직접 연결해야 합니다.
        # 예: command=lambda: self.controller.start_color_picker('main_color')

    def on_closing(self):
        """창을 닫을 때 리소스를 안전하게 정리합니다."""
        self.is_running = False
        self.keyboard_listener.stop()
        if self.ui:
            self.ui.root.destroy()

    def apply_settings(self) -> bool:
        """UI의 설정값들을 컨트롤러의 속성에 적용합니다."""
        if not self.ui: return False
        try:
            self.color = ast.literal_eval(self.ui.color_var.get())
            self.p1 = ast.literal_eval(self.ui.p1_var.get())
            self.p2 = ast.literal_eval(self.ui.p2_var.get())
            self.color_tolerance = int(self.ui.color_tolerance_var.get())
            
            direction_str = self.ui.direction_var.get()
            self.search_direction = self.ui.SEARCH_DIRECTION_MAP[direction_str]
            
            self.button_delay_ms = int(self.ui.button_delay_var.get())
            self.quantity_option = self.ui.quantity_option_var.get()
            self.use_area = self.ui.use_area_var.get()
            self.area_coord = ast.literal_eval(self.ui.area_coord_var.get())
            self.apply_coord = ast.literal_eval(self.ui.apply_coord_var.get())
            
            self.ui.status_var.set("설정 적용 완료.")
            return True
        except (ValueError, SyntaxError, KeyError) as e:
            error_msg = f"설정 오류: 입력값을 확인하세요. ({e})"
            self.ui.status_var.set(error_msg)
            return False

    def toggle_run(self):
        """실행/중지 상태를 토글합니다."""
        if self.is_running:
            self.stop_run()
        else:
            self.start_run()

    def _update_status_safe(self, message: str):
        """UI의 상태 메시지를 스레드에 안전한 방식으로 업데이트합니다."""
        if self.ui:
            self.ui.root.after(0, lambda: self.ui.status_var.set(message))

    def start_run(self):
        """메인 로직 실행을 시작합니다."""
        if self.is_running: return
        if not self.apply_settings(): return

        self.is_running = True
        
        if self.ui:
            def ui_update():
                self.ui.status_var.set("실행 중... (ESC로 중지)")
                self.ui.run_button.config(text="중지(Shift x2)")
                self.ui.update_window_bg('searching')
            self.ui.root.after(0, ui_update)
        
        self.run_thread = threading.Thread(target=self._run_worker, daemon=True)
        self.run_thread.start()

    def stop_run(self, message="실행이 중지되었습니다."):
        """메인 로직 실행을 중지하고, 다시 시작할 수 있도록 상태를 초기화합니다."""
        if not self.is_running: return

        self.is_running = False
        
        if self.ui:
            def ui_update():
                self.ui.status_var.set(message)
                self.ui.run_button.config(text="실행(Shift x2)")
                self.ui.update_window_bg('default')
            self.ui.root.after(0, ui_update)
        print(f"--- {message} ---")

    def on_key_press(self, key):
        """전역 키 입력을 감지하여 Shift 키를 두 번 눌렀는지 확인합니다."""
        # Shift 키만 감지합니다 (왼쪽, 오른쪽 모두).
        if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            if self.shift_press_timer:
                self.shift_press_timer.cancel()

            self.shift_press_count += 1

            if self.shift_press_count >= 2:
                # 두 번 눌림 감지, 실행/중지 토글
                self.shift_press_count = 0
                self.shift_press_timer = None
                self.toggle_run()
            else:
                # 첫 번째 눌림, 0.4초 타이머 시작
                self.shift_press_timer = threading.Timer(0.4, self._reset_shift_count)
                self.shift_press_timer.start()

    def _reset_shift_count(self):
        """시간이 초과되면 Shift 키 누름 횟수를 초기화합니다."""
        self.shift_press_count = 0
        self.shift_press_timer = None

    def _click_at(self, coord: tuple):
        """지정된 좌표로 이동하고, 설정된 딜레이 후 클릭합니다."""
        if not self.is_running: return
        
        self.mouse_controller.position = coord
        time.sleep(self.button_delay_ms / 1000.0)
        if not self.is_running: return # 딜레이 후 다시 한번 확인
        self.mouse_controller.click(mouse.Button.left, 1)
        time.sleep(0.05) # 클릭 후 안정화를 위한 짧은 대기

    def _run_worker(self):
        """메인 로직을 순서대로 실행하는 스레드 워커입니다."""
        try:
            # --- Part 1: 초기 시퀀스 (수량 -> 구역) ---
            # 1. 수량 입력
            if not self.is_running: return
            self._update_status_safe(f"수량 '{self.quantity_option}' 입력 중...")
            if self.quantity_option == "1":
                self.keyboard_controller.press('1')
                self.keyboard_controller.release('1')
            elif self.quantity_option == "2":
                self.keyboard_controller.press('2')
                self.keyboard_controller.release('2')
            # "direct"는 사용자가 직접 입력하므로 프로그램은 아무것도 하지 않습니다.
            time.sleep(0.1) # 키보드 입력 후 짧은 대기

            # 2. 구역 버튼 클릭 (체크된 경우)
            if self.use_area:
                if not self.is_running: return
                self._update_status_safe("구역 버튼 클릭 중...")
                self._click_at(self.area_coord)

            # --- Part 2: 색상 반복 탐색 ---
            self._update_status_safe("색상 탐색 대기 중...")
            search_area = (min(self.p1[0], self.p2[0]), min(self.p1[1], self.p2[1]),
                           max(self.p1[0], self.p2[0]), max(self.p1[1], self.p2[1]))

            while self.is_running:
                self._update_status_safe(f"색상 탐색 중...")

                found_pos = self.color_finder.find_color_in_area(
                    area=search_area, color=self.color,
                    tolerance=self.color_tolerance, direction=self.search_direction
                )

                if found_pos:
                    # --- Part 3: 성공 시퀀스 ---
                    self._update_status_safe(f"색상 발견! {found_pos} 클릭 중...")
                    self._click_at(found_pos)
                    
                    if not self.is_running: return
                    self._update_status_safe("신청 버튼 클릭 중...")
                    self._click_at(self.apply_coord)
                    
                    self.stop_run("작업 완료!")
                    return # 작업 완료 후 스레드 종료

                # 색상을 못 찾았을 경우, 짧은 대기 후 다시 시도 (CPU 과부하 방지)
                time.sleep(0.05)

        except Exception as e:
            self.stop_run(f"오류 발생: {e}")

    def show_area(self):
        """현재 설정된 탐색 영역과 클릭 좌표들을 화면에 시각적으로 표시합니다."""
        if not self.ui or not self.apply_settings(): return

        for marker in self.area_markers:
            if marker and marker.winfo_exists():
                marker.destroy()
        self.area_markers.clear()

        # 메인 탐색 영역 표시
        x1, y1, x2, y2 = (self.p1[0], self.p1[1], self.p2[0], self.p2[1])
        left, top, width, height = min(x1, x2), min(y1, y2), abs(x1 - x2), abs(y1 - y2)
        
        area_marker = tk.Toplevel(self.ui.root)
        area_marker.overrideredirect(True)
        area_marker.geometry(f"{width}x{height}+{left}+{top}")
        area_marker.configure(bg="red")
        area_marker.attributes('-alpha', 0.3, '-topmost', True)
        area_marker.after(2000, area_marker.destroy)
        self.area_markers.append(area_marker)
        
        # 주요 좌표들 표시
        points_to_show = {"구역": (self.area_coord, "blue"),
                          "신청": (self.apply_coord, "cyan")}
        
        for name, (pos, color) in points_to_show.items():
            if pos == (0,0): continue
            px, py = pos
            point_marker = tk.Toplevel(self.ui.root)
            point_marker.overrideredirect(True)
            point_marker.geometry(f"15x15+{px - 7}+{py - 7}")
            point_marker.configure(bg=color)
            point_marker.attributes('-alpha', 0.7, '-topmost', True)
            point_marker.after(2000, point_marker.destroy)
            self.area_markers.append(point_marker)

        self.ui.status_var.set("영역 및 좌표 표시 중...")

    def start_coordinate_picker(self, coord_key: str):
        """지정된 키에 해당하는 좌표를 2초 후에 캡처하는 프로세스를 시작합니다."""
        if not self.ui: return
        
        key_map = {'p1': '↖영역', 'p2': '↘영역', 'area': '구역', 'apply': '신청'}
        display_name = key_map.get(coord_key, coord_key)
        self.ui.status_var.set(f"'{display_name}' 좌표 지정: 2초 후 위치 저장...")
        self.ui.root.after(2000, lambda: self._grab_coordinate(coord_key, display_name))

    def _grab_coordinate(self, coord_key: str, display_name: str):
        if not self.ui: return
        x, y = self.mouse_controller.position
        new_pos = (int(x), int(y))
        
        var_map = {'p1': self.ui.p1_var, 'p2': self.ui.p2_var, 'area': self.ui.area_coord_var,
                   'apply': self.ui.apply_coord_var}
        
        if coord_key in var_map:
            var_map[coord_key].set(str(new_pos))
            self.ui.status_var.set(f"'{display_name}' 좌표 저장: {new_pos}")
            self.ui.flash_window() # 성공 피드백

    def start_color_picker(self, color_key: str):
        """지정된 키에 해당하는 색상을 2초 후에 캡처하는 프로세스를 시작합니다."""
        if not self.ui: return
        self.ui.status_var.set("'색상' 지정: 2초 후 위치의 색상 저장...")
        self.ui.root.after(2000, lambda: self._grab_color(color_key))

    def _grab_color(self, color_key: str):
        if not self.ui: return
        x, y = self.mouse_controller.position
        screenshot = ImageGrab.grab(bbox=(int(x), int(y), int(x) + 1, int(y) + 1))
        new_color = screenshot.getpixel((0, 0))[:3] # RGB

        if color_key == 'main_color':
            self.ui.color_var.set(str(new_color))
            self.ui.status_var.set(f"'색상' 저장 완료: {new_color}")
            self.ui.flash_window() # 성공 피드백