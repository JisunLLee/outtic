import tkinter as tk
import threading
import time
from pynput import mouse, keyboard
from typing import Optional, TYPE_CHECKING
import ast
from PIL import ImageGrab # 화면 캡처를 위해 import 합니다.

from .color_finder import ColorFinder, SearchDirection
from .global_hotkey_listener import GlobalHotkeyListener

# 순환 참조를 피하면서 타입 힌팅을 하기 위한 Forward-declaration
if TYPE_CHECKING:
    from .ui import AppUI

class AppController:
    """
    애플리케이션의 모든 로직과 상태를 담당합니다.
    UI와 상호작용하며, 핵심 기능을 실행합니다.
    """
    def __init__(self):
        self.ui: Optional['AppUI'] = None
        self.mouse_controller = mouse.Controller()
        self.color_finder = ColorFinder()

        # --- 백그라운드 작업 관련 ---
        self.is_searching = False
        self.search_thread: Optional[threading.Thread] = None

        # --- 전역 단축키 설정 ---
        hotkey_map = {'shift+esc': self.start_search, keyboard.Key.esc: self.stop_search}
        self.global_hotkey_listener = GlobalHotkeyListener(hotkey_map)
        self.global_hotkey_listener.start()

        # --- 기본값 설정 ---
        # 이 값들은 UI의 초기값을 설정하는 데 사용됩니다.
        self.p1 = (88, 219)
        self.p2 = (398, 462)
        self.color = (0, 204, 204)
        self.complete_coord = (805, 704)
        self.color_tolerance = 15
        self.color_area_tolerance = 5
        self.search_direction = SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT
        self.complete_click_delay = 0.02 # 완료 클릭 전 딜레이 (초)

    def set_ui(self, ui: 'AppUI'):
        """
        컨트롤러에 UI 인스턴스를 연결합니다.
        이 메서드는 애플리케이션 시작 시 한 번 호출됩니다.
        """
        self.ui = ui
        self.ui.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """창을 닫을 때 리소스를 안전하게 정리합니다."""
        self.is_searching = False
        self.global_hotkey_listener.stop()
        self.ui.root.destroy()

    def apply_settings(self):
        """UI의 설정값들을 컨트롤러의 속성에 적용합니다."""
        if not self.ui: return False
        try:
            self.p1 = ast.literal_eval(self.ui.p1_var.get())
            self.p2 = ast.literal_eval(self.ui.p2_var.get())
            self.complete_coord = ast.literal_eval(self.ui.complete_coord_var.get())
            self.color = ast.literal_eval(self.ui.color_var.get())
            self.color_tolerance = int(self.ui.color_tolerance_var.get())
            self.color_area_tolerance = int(self.ui.color_area_tolerance_var.get())
            self.complete_click_delay = int(self.ui.complete_delay_var.get()) / 1000.0

            # UI의 문자열을 SearchDirection Enum으로 변환합니다.
            direction_map = {
                "→↓": SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT,
                "←↓": SearchDirection.TOP_RIGHT_TO_BOTTOM_LEFT,
                "→↑": SearchDirection.BOTTOM_LEFT_TO_TOP_RIGHT,
                "←↑": SearchDirection.BOTTOM_RIGHT_TO_TOP_LEFT,
            }
            selected_direction_str = self.ui.direction_var.get()
            self.search_direction = direction_map.get(selected_direction_str, SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT)
            
            self.ui.update_status("설정이 적용되었습니다.")
            print("설정이 적용되었습니다.")
            return True
        except (ValueError, SyntaxError) as e:
            error_msg = f"설정 오류: 입력값을 확인하세요. ({e})"
            self.ui.update_status(error_msg)
            print(error_msg)
            return False

    def show_area(self):
        """UI에 현재 설정된 탐색 영역과 주요 좌표를 표시하도록 요청합니다."""
        if not self.ui: return

        if not self.apply_settings():
            return

        # 표시할 영역들을 리스트로 구성합니다.
        # 나중에 구역 1, 2가 추가되면 이 리스트에 추가하기만 하면 됩니다.
        areas_to_display = []
        left = min(self.p1[0], self.p2[0])
        top = min(self.p1[1], self.p2[1])
        right = max(self.p1[0], self.p2[0])
        bottom = max(self.p1[1], self.p2[1])
        areas_to_display.append({
            'rect': (left, top, right - left, bottom - top),
            'color': 'red',
            'alpha': 0.4
        })

        # 마커로 표시할 좌표들
        points_to_mark = {
            '완료': self.complete_coord,
        }

        self.ui.display_visual_aids(areas=areas_to_display, points=points_to_mark)

    def start_coordinate_picker(self, coord_key: str):
        """
        지정된 키에 해당하는 좌표를 2초 후에 캡처하는 프로세스를 시작합니다.
        UI의 버튼과 연결되어 호출됩니다.

        :param coord_key: 'p1', 'p2', 'complete' 등 좌표를 식별하는 키
        """
        if not self.ui:
            print("UI가 연결되지 않았습니다.")
            return

        key_map = {'p1': '↖영역', 'p2': '↘영역', 'complete': '완료'}
        display_name = key_map.get(coord_key, coord_key)
        self.ui.update_status(f"'{display_name}' 좌표 지정: 2초 후 마우스 위치를 저장합니다...")

        # 2초 후에 _grab_coord_after_delay 함수를 실행
        self.ui.root.after(2000, lambda: self._grab_coord_after_delay(coord_key, display_name))

    def _grab_coord_after_delay(self, coord_key: str, display_name: str):
        """실제로 마우스 좌표를 가져와서 컨트롤러 상태와 UI를 업데이트합니다."""
        if not self.ui: return

        x, y = self.mouse_controller.position
        new_pos = (int(x), int(y))

        # 키에 따라 컨트롤러의 속성과 UI의 변수를 업데이트
        if coord_key == 'p1': self.ui.p1_var.set(str(new_pos))
        elif coord_key == 'p2': self.ui.p2_var.set(str(new_pos))
        elif coord_key == 'complete': self.ui.complete_coord_var.set(str(new_pos))
        
        self.ui.update_status(f"'{display_name}' 좌표 저장 완료: {new_pos}")
        print(f"좌표 저장 완료 ({coord_key}): {new_pos}")

    def start_color_picker(self, color_key: str):
        """
        지정된 키에 해당하는 색상을 2초 후에 캡처하는 프로세스를 시작합니다.
        UI의 버튼과 연결되어 호출됩니다.

        :param color_key: 'main_color' 등 색상을 식별하는 키
        """
        if not self.ui:
            print("UI가 연결되지 않았습니다.")
            return

        key_map = {'main_color': '기본 색상'}
        display_name = key_map.get(color_key, color_key)
        self.ui.update_status(f"'{display_name}' 지정: 2초 후 마우스 위치의 색상을 저장합니다...")

        # 2초 후에 _grab_color_after_delay 함수를 실행
        self.ui.root.after(2000, lambda: self._grab_color_after_delay(color_key, display_name))

    def _grab_color_after_delay(self, color_key: str, display_name: str):
        """실제로 마우스 위치의 색상을 가져와서 컨트롤러 상태와 UI를 업데이트합니다."""
        if not self.ui: return

        x, y = self.mouse_controller.position
        # 1x1 픽셀만 캡처하면 충분합니다.
        screenshot = ImageGrab.grab(bbox=(int(x), int(y), int(x) + 1, int(y) + 1))
        pixel_color = screenshot.getpixel((0, 0))
        
        new_color = pixel_color[:3] # RGB 값만 사용 (알파 채널 제외)

        if color_key == 'main_color': self.ui.color_var.set(str(new_color))
        
        self.ui.update_status(f"'{display_name}' 저장 완료: {new_color}")
        print(f"색상 저장 완료 ({color_key}): {new_color}")

    def toggle_search(self):
        """UI 버튼 클릭 시 검색 상태를 토글합니다."""
        if self.is_searching:
            self.stop_search()
        else:
            self.start_search()

    def start_search(self):
        """색상 검색 프로세스를 시작합니다."""
        if self.is_searching: return
        if not self.ui: return

        if not self.apply_settings():
            return

        self.is_searching = True
        self.ui.queue_task(lambda: self.ui.update_status("색상 검색 중... (ESC로 중지)"))
        self.ui.queue_task(lambda: self.ui.update_button_text("중지 (ESC)"))
        print("--- 색상 검색 시작 ---")

        # 별도 스레드에서 검색 작업 실행
        self.search_thread = threading.Thread(target=self._search_worker, daemon=True)
        self.search_thread.start()

    def stop_search(self, message="검색이 중지되었습니다."):
        """색상 검색 프로세스를 중지합니다."""
        if not self.is_searching: return
        if not self.ui: return

        self.is_searching = False
        self.ui.queue_task(lambda: self.ui.update_status(message))
        self.ui.queue_task(lambda: self.ui.update_button_text("찾기(Shift+ESC)"))
        print(f"--- {message} ---")

    def _search_worker(self):
        """(스레드 워커) 색상을 주기적으로 검색하고,"""
        # 검색 영역 계산
        left = min(self.p1[0], self.p2[0])
        top = min(self.p1[1], self.p2[1])
        right = max(self.p1[0], self.p2[0])
        bottom = max(self.p1[1], self.p2[1])
        search_area = (left, top, right, bottom)

        while self.is_searching:
            # 색상 찾기
            found_pos = self.color_finder.find_color_in_area(
                area=search_area,
                color=self.color,
                tolerance=self.color_tolerance,
                direction=self.search_direction
            )

            if found_pos:
                # 1. 색상을 찾으면 해당 위치를 클릭합니다.
                abs_x, abs_y = found_pos
                self.color_finder.click_action(abs_x, abs_y)
                
                # 2. '완료' 좌표가 설정되어 있으면, 잠시 후 해당 좌표를 클릭합니다.
                if self.complete_coord and self.complete_coord != (0, 0):
                    time.sleep(self.complete_click_delay) # 설정된 딜레이만큼 대기
                    comp_x, comp_y = self.complete_coord
                    self.color_finder.click_action(comp_x, comp_y)
                    status_message = f"색상 클릭 후 완료({comp_x},{comp_y}) 클릭"
                else:
                    status_message = f"색상 발견 및 클릭: ({abs_x}, {abs_y})"

                self.stop_search(message=status_message)
                return # 스레드 종료

            time.sleep(0.1) # CPU 과부하 방지를 위한 짧은 대기
