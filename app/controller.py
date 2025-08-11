import tkinter as tk
import threading
import time
from pynput import mouse, keyboard
from typing import Optional, TYPE_CHECKING
import ast
import random # 오차 적용을 위해 추가
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
        hotkey_map = {'<shift>+s': self.start_search, '<esc>': self.stop_search}
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
        self.use_sequence = True # 구역 사용 여부

        # --- 구역별 설정 데이터 ---
        self.areas = {}
        self._initialize_area_settings(1) # 구역1 초기화

    def set_ui(self, ui: 'AppUI'):
        """
        컨트롤러에 UI 인스턴스를 연결합니다.
        이 메서드는 애플리케이션 시작 시 한 번 호출됩니다.
        """
        self.ui = ui
        self.ui.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _initialize_area_settings(self, area_number: int):
        """컨트롤러 내부에 지정된 구역의 기본 설정값을 생성합니다."""
        if area_number not in self.areas:
            self.areas[area_number] = {
                'use': True,
                'click_coord': (0, 0),
                'clicks': 1,
                'offset': 5,
                'p1': (0, 0),
                'p2': (0, 0),
                'use_color': False,
                'color': (0, 0, 0),
                'direction': self.search_direction,
                'use_area_bounds': True, # 개별 영역 사용 여부
                'search_area': (0, 0, 0, 0) # 계산된 탐색 영역
            }

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
            self.use_sequence = self.ui.use_sequence_var.get()
            
            # --- 구역 설정 적용 ---
            for area_number, area_ui_vars in self.ui.area_vars.items():
                if area_number not in self.areas:
                    self._initialize_area_settings(area_number)
                
                area_settings = self.areas[area_number]
                area_settings['use'] = area_ui_vars['use_var'].get()
                area_settings['click_coord'] = ast.literal_eval(area_ui_vars['coord_var'].get())
                area_settings['clicks'] = int(area_ui_vars['clicks_var'].get())
                area_settings['offset'] = int(area_ui_vars['offset_var'].get())
                area_settings['p1'] = ast.literal_eval(area_ui_vars['p1_var'].get())
                area_settings['p2'] = ast.literal_eval(area_ui_vars['p2_var'].get())
                area_settings['use_color'] = area_ui_vars['use_color_var'].get()
                area_settings['use_area_bounds'] = not area_ui_vars['use_area_bounds_var'].get() # UI와 논리 반대
                area_settings['color'] = ast.literal_eval(area_ui_vars['color_var'].get())
                area_settings['direction'] = direction_map.get(area_ui_vars['direction_var'].get(), self.search_direction)

                # 구역별 탐색 영역 미리 계산
                p1 = area_settings['p1']
                p2 = area_settings['p2']
                area_settings['search_area'] = (min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1]))


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
        areas_to_display = []
        left = min(self.p1[0], self.p2[0])
        top = min(self.p1[1], self.p2[1])
        right = max(self.p1[0], self.p2[0])
        bottom = max(self.p1[1], self.p2[1])
        areas_to_display.append({
            'rect': (left, top, right - left, bottom - top),
            'color': 'red',
            'alpha': 0.3
        })

        # 활성화된 구역들의 탐색 영역도 함께 표시
        for area_number, settings in self.areas.items():
            if settings['use']:
                x1, y1, x2, y2 = settings['search_area']
                areas_to_display.append({
                    'rect': (x1, y1, x2 - x1, y2 - y1),
                    'color': 'cyan',
                    'alpha': 0.4
                })

        # 마커로 표시할 좌표들
        points_to_mark = {
            '완료': self.complete_coord,
        }
        # 활성화된 구역들의 클릭 좌표도 함께 표시
        for area_number, settings in self.areas.items():
            if settings['use']:
                points_to_mark[f'구역{area_number}'] = settings['click_coord']

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

        # 표시 이름을 더 동적으로 생성
        display_name = coord_key
        if coord_key == 'p1': display_name = '기본 ↖영역'
        elif coord_key == 'p2': display_name = '기본 ↘영역'
        elif coord_key == 'complete': display_name = '완료'
        elif coord_key.startswith('area_'):
            parts = coord_key.split('_')
            area_num = parts[1]
            type_key = parts[2]
            type_map = {'p1': '↖영역', 'p2': '↘영역', 'click': '클릭 좌표'}
            display_name = f"구역{area_num} {type_map.get(type_key, type_key)}"

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
        elif coord_key.startswith('area_'): # 예: 'area_1_p1', 'area_1_click_coord'
            try:
                parts = coord_key.split('_')
                area_number = int(parts[1])
                key_type = '_'.join(parts[2:]) # 'p1', 'p2', 'click_coord'
                var_key_map = {'p1': 'p1_var', 'p2': 'p2_var', 'click_coord': 'coord_var'}
                var_key = var_key_map[key_type]
                self.ui.area_vars[area_number][var_key].set(str(new_pos))
            except (IndexError, KeyError, ValueError) as e:
                print(f"잘못된 구역 좌표 키입니다: {coord_key}, 오류: {e}")
        
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

        display_name = color_key
        if color_key == 'main_color': display_name = '기본 색상'
        elif color_key.startswith('area_'): # 예: 'area_1_color'
            area_num = color_key.split('_')[1] # '1'
            display_name = f'구역{area_num} 색상'

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
        elif color_key.startswith('area_'): # 예: 'area_1_color'
            try:
                area_number = int(color_key.split('_')[1]) # '1'
                self.ui.area_vars[area_number]['color_var'].set(str(new_color))
            except (IndexError, ValueError) as e:
                print(f"잘못된 구역 색상 키입니다: {color_key}, 오류: {e}")

        
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
        self.ui.queue_task(lambda: self.ui.update_button_text("찾기(Shift+s)"))
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

            # --- 색상을 찾지 못했을 때의 로직 ---
            if self.use_sequence:
                # 활성화된 첫 번째 구역을 찾아 클릭합니다.
                # 추후 순차적 구역 클릭 로직으로 확장될 수 있습니다.
                for area_number, settings in sorted(self.areas.items()):
                    if settings['use']:
                        click_coord = settings['click_coord']
                        num_clicks = settings['clicks']

                        # '횟수' 설정만큼 반복 클릭
                        for i in range(num_clicks):
                            # 검색이 중간에 중지되면 루프를 빠져나갑니다.
                            if not self.is_searching:
                                return

                            # TODO: offset_var를 사용하여 랜덤 위치에 클릭하는 로직 추가
                            self.color_finder.click_action(click_coord[0], click_coord[1])

                            # 마지막 클릭이 아니면 짧은 딜레이를 줍니다.
                            if i < num_clicks - 1:
                                time.sleep(0.05) # 클릭 사이의 간격
                        
                        # 상태 메시지 업데이트 및 검색 중지
                        status_message = f"색상 못찾음. 구역{area_number}({click_coord[0]},{click_coord[1]}) {num_clicks}회 클릭."
                        self.stop_search(message=status_message)
                        return # 스레드 종료
            
            # '구역 사용'이 비활성화되었거나, 활성화된 구역이 하나도 없는 경우
            self.stop_search(message="색상 못찾음. 활성화된 구역이 없어 중지합니다.")
            return # 스레드 종료
