import tkinter as tk
from pynput import mouse
from typing import Optional, TYPE_CHECKING
import ast
from PIL import ImageGrab # 화면 캡처를 위해 import 합니다.

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

        # --- 기본값 설정 ---
        # 이 값들은 UI의 초기값을 설정하는 데 사용됩니다.
        self.p1 = (88, 219)
        self.p2 = (398, 462)
        self.color = (0, 204, 204)
        self.complete_coord = (805, 704)
        self.color_tolerance = 15
        self.color_area_tolerance = 5

    def set_ui(self, ui: 'AppUI'):
        """
        컨트롤러에 UI 인스턴스를 연결합니다.
        이 메서드는 애플리케이션 시작 시 한 번 호출됩니다.
        """
        self.ui = ui

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
