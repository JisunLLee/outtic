import tkinter as tk
import threading
import time
from pynput import mouse, keyboard
from typing import Optional, TYPE_CHECKING
import ast
import random # 오차 적용을 위해 추가
from PIL import ImageGrab # 화면 캡처를 위해 import 합니다.
import json
from tkinter import filedialog
import itertools # 재시도 순환을 위해 추가

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
        self.tries_count = 0 # 현재 시도 횟수

        # --- 전역 단축키 설정 ---
        hotkey_map = {'<shift>+s': self.start_search, '<esc>': self.stop_search}
        self.global_hotkey_listener = GlobalHotkeyListener(hotkey_map)
        self.global_hotkey_listener.start()

        # --- 기본값 설정 ---
        # 이 값들은 UI의 초기값을 설정하는 데 사용됩니다.
        self.p1 = (165, 228)
        self.p2 = (344, 363)
        self.color = (124, 104, 238)
        self.complete_coord = (769, 648)
        self.color_tolerance = 15
        self.color_area_tolerance = 5
        self.search_direction = SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT
        self.complete_click_delay = 0.1 # 완료 클릭 전 딜레이 (초), UI 기본값 10 -> 100ms
        
        # 2순위 색상 추가
        self.use_secondary_color = False
        self.secondary_color = (28, 168, 20)

        # --- 구역값 설정 ---
        self.use_sequence = True # 구역 사용 여부 (UI 체크박스 기본값)
        self.area_delay = 0.30 # 구역 클릭 전 딜레이 (초), UI 기본값 30 -> 300ms
        self.search_delay = 0.15 # 탐색 대기 (초)
        self.total_tries = 178 # 총 시도 횟수

        # --- 구역별 설정 데이터 ---
        self.areas = {}
        self._initialize_area_settings(1) # 구역1 초기화
        self._initialize_area_settings(2) # 구역2 초기화
        self._initialize_area_settings(3) # 구역3 초기화
        self._initialize_area_settings(4) # 구역4 초기화

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
            # 구역별 기본값 설정
            default_use = False
            default_click_coord = (0, 0)
            default_clicks = 6
            default_offset = 2
            default_use_area_bounds = False 
            default_p1 = self.p1
            default_p2 = self.p2
            default_use_direction = False   # '기본' 방향 사용 (UI 체크박스 True)
            default_direction = self.search_direction # 기본 탐색 방향으로 초기화


            if area_number == 1:
                default_use = True
                default_click_coord = (734, 288)
                default_clicks = 2
                default_p1 = (263, 227)
                default_p2 = (389, 449)
                default_direction = SearchDirection.BOTTOM_RIGHT_TO_TOP_LEFT
            if area_number == 2:
                default_use = True
                default_click_coord = (727, 304)
                default_clicks = 2
                default_p1 = (90, 225)
                default_p2 = (245, 256)
            if area_number == 3:
                default_use = True
                default_click_coord = (732, 322)
                default_clicks = 1
                default_p1 = (263, 227)
                default_p2 = (389, 449)
                default_direction = SearchDirection.BOTTOM_RIGHT_TO_TOP_LEFT
            if area_number == 4:
                default_use = True
                default_click_coord = (731, 339)
                default_clicks = 1
                default_p1 = (98, 229)
                default_p2 = (225, 450)
                default_direction = SearchDirection.BOTTOM_LEFT_TO_TOP_RIGHT


            self.areas[area_number] = {
                'use': default_use, # UI의 '탐색' 체크박스는 기본적으로 꺼져있습니다.
                'click_coord': default_click_coord,
                'clicks': default_clicks, # 구역 클릭 횟수
                'offset': default_offset, # 구역 클릭 범위 오차
                'use_area_bounds': default_use_area_bounds, 
                'p1': default_p1,
                'p2': default_p2,
                'use_color': False, # '기본' 색상 사용 (UI 체크박스 True)
                'color': (0, 0, 0),
                'direction': default_direction,
                'use_direction': default_use_direction, 
                'search_area': (0, 0, 0, 0) # 계산된 탐색 영역
            }

    def _get_global_search_area(self):
        """기본 탐색 영역 좌표를 계산하여 반환합니다."""
        left = min(self.p1[0], self.p2[0])
        top = min(self.p1[1], self.p2[1])
        right = max(self.p1[0], self.p2[0])
        bottom = max(self.p1[1], self.p2[1])
        return (left, top, right, bottom)

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
            self.use_secondary_color = self.ui.use_secondary_color_var.get()
            self.secondary_color = ast.literal_eval(self.ui.secondary_color_var.get())
            self.color_tolerance = int(self.ui.color_tolerance_var.get())
            self.color_area_tolerance = int(self.ui.color_area_tolerance_var.get())
            # UI 입력값을 100으로 나누어 초 단위로 변환합니다. (예: 15 -> 0.15초)
            self.complete_click_delay = int(self.ui.complete_delay_var.get()) / 100.0
            self.area_delay = int(self.ui.area_delay_var.get()) / 100.0
            self.search_delay = int(self.ui.search_delay_var.get()) / 100.0

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
            self.total_tries = int(self.ui.total_tries_var.get())
            
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
                area_settings['use_color'] = not area_ui_vars['use_color_var'].get() # UI와 논리 반대. '기본' 체크 해제 시 개별 색상 사용
                area_settings['use_area_bounds'] = not area_ui_vars['use_area_bounds_var'].get() # UI와 논리 반대
                area_settings['use_direction'] = not area_ui_vars['use_direction_var'].get() # '기본' 체크 해제 시 개별 방향 사용
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
            'color': 'red', # 기본 영역은 빨간색
            'alpha': 0.3
        })

        # 구역별로 고유한 색상을 지정하기 위한 리스트
        area_overlay_colors = ['cyan', 'magenta', 'yellow', 'lime', 'orange', 'purple']

        # 활성화된 구역들의 탐색 영역도 함께 표시
        for area_number, settings in self.areas.items():
            # '기본' 영역 사용이 체크 해제된 경우(개별 영역 사용 시)에만 개별 영역을 표시
            if settings['use'] and settings['use_area_bounds']:
                x1, y1, x2, y2 = settings['search_area']
                # 구역 번호에 따라 색상 순환
                overlay_color = area_overlay_colors[(area_number - 1) % len(area_overlay_colors)]
                areas_to_display.append({
                    'rect': (x1, y1, x2 - x1, y2 - y1),
                    'color': overlay_color,
                    'alpha': 0.4,
                    'text': f'{area_number}구역' # 영역에 텍스트 추가
                })

        # 마커로 표시할 좌표들
        points_to_mark = [
            {'text': '완료', 'pos': self.complete_coord, 'color': '#50E3C2'}, # Teal
        ]
        # 활성화된 구역들의 클릭 좌표도 함께 표시
        for area_number, settings in self.areas.items():
            if settings['use']:
                marker_color = area_overlay_colors[(area_number - 1) % len(area_overlay_colors)]
                points_to_mark.append({
                    'text': f'{area_number}',
                    'pos': settings['click_coord'],
                    'color': marker_color
                })

        self.ui.display_visual_aids(areas=areas_to_display, points=points_to_mark)

    def save_settings(self):
        """현재 설정을 JSON 파일로 저장합니다."""
        if not self.ui: return
        if not self.apply_settings():
            self.ui.update_status("설정 저장 실패: 현재 설정에 오류가 있습니다.")
            return

        settings_data = {
            'p1': self.p1,
            'p2': self.p2,
            'color': self.color,
            'use_secondary_color': self.use_secondary_color,
            'secondary_color': self.secondary_color,
            'complete_coord': self.complete_coord,
            'color_tolerance': self.color_tolerance,
            'color_area_tolerance': self.color_area_tolerance,
            'search_direction': self.search_direction.value, # Enum을 문자열로 저장
            'complete_click_delay': self.complete_click_delay,
            'use_sequence': self.use_sequence,
            'area_delay': self.area_delay,
            'search_delay': self.search_delay,
            'total_tries': self.total_tries,
            'areas': {}
        }

        for area_number, area_settings in self.areas.items():
            settings_data['areas'][area_number] = {
                'use': area_settings['use'],
                'click_coord': area_settings['click_coord'],
                'clicks': area_settings['clicks'],
                'offset': area_settings['offset'],
                'use_area_bounds': area_settings['use_area_bounds'],
                'p1': area_settings['p1'],
                'p2': area_settings['p2'],
                'use_color': area_settings['use_color'],
                'color': area_settings['color'],
                'direction': area_settings['direction'].value, # Enum을 문자열로 저장
                'use_direction': area_settings['use_direction'],
            }

        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 설정 파일", "*.json"), ("모든 파일", "*.*")],
            title="설정 저장"
        )

        if not filepath:
            self.ui.update_status("설정 저장이 취소되었습니다.")
            return

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, ensure_ascii=False, indent=4)
            self.ui.update_status(f"설정이 '{filepath.split('/')[-1]}'에 저장되었습니다.")
        except Exception as e:
            self.ui.update_status(f"파일 저장 오류: {e}")

    def load_settings(self):
        """JSON 파일에서 설정을 불러옵니다."""
        if not self.ui: return

        filepath = filedialog.askopenfilename(
            filetypes=[("JSON 설정 파일", "*.json"), ("모든 파일", "*.*")],
            title="설정 불러오기"
        )

        if not filepath:
            self.ui.update_status("설정 불러오기가 취소되었습니다.")
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)

            # 컨트롤러 속성 업데이트 (get 메서드로 기본값 보장)
            self.p1 = tuple(settings_data.get('p1', self.p1))
            self.p2 = tuple(settings_data.get('p2', self.p2))
            self.color = tuple(settings_data.get('color', self.color))
            self.use_secondary_color = bool(settings_data.get('use_secondary_color', self.use_secondary_color))
            self.secondary_color = tuple(settings_data.get('secondary_color', self.secondary_color))
            self.complete_coord = tuple(settings_data.get('complete_coord', self.complete_coord))
            self.color_tolerance = int(settings_data.get('color_tolerance', self.color_tolerance))
            self.color_area_tolerance = int(settings_data.get('color_area_tolerance', self.color_area_tolerance))
            self.search_direction = SearchDirection(settings_data.get('search_direction', self.search_direction.value))
            self.complete_click_delay = float(settings_data.get('complete_click_delay', self.complete_click_delay))
            self.use_sequence = bool(settings_data.get('use_sequence', self.use_sequence))
            self.area_delay = float(settings_data.get('area_delay', self.area_delay))
            self.search_delay = float(settings_data.get('search_delay', self.search_delay))
            self.total_tries = int(settings_data.get('total_tries', self.total_tries))

            loaded_areas = settings_data.get('areas', {})
            for area_number_str, loaded in loaded_areas.items():
                area_number = int(area_number_str)
                if area_number in self.areas:
                    area = self.areas[area_number]
                    area['use'] = bool(loaded.get('use', area['use']))
                    area['click_coord'] = tuple(loaded.get('click_coord', area['click_coord']))
                    area['clicks'] = int(loaded.get('clicks', area['clicks']))
                    area['offset'] = int(loaded.get('offset', area['offset']))
                    area['use_area_bounds'] = bool(loaded.get('use_area_bounds', area['use_area_bounds']))
                    area['p1'] = tuple(loaded.get('p1', area['p1']))
                    area['p2'] = tuple(loaded.get('p2', area['p2']))
                    area['use_color'] = bool(loaded.get('use_color', area['use_color']))
                    area['color'] = tuple(loaded.get('color', area['color']))
                    area['direction'] = SearchDirection(loaded.get('direction', area['direction'].value))
                    area['use_direction'] = bool(loaded.get('use_direction', area['use_direction']))

            # UI에 변경된 설정값 반영
            self.ui.update_ui_from_controller()
            self.ui.update_status(f"'{filepath.split('/')[-1]}'에서 설정을 불러왔습니다.")

        except Exception as e:
            self.ui.update_status(f"파일 불러오기 오류: {e}")

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
        if coord_key == 'p1':
            self.ui.p1_var.set(str(new_pos))
            self.ui.queue_task(lambda: self.ui.flash_setting_change('global_setting_change'))
        elif coord_key == 'p2':
            self.ui.p2_var.set(str(new_pos))
            self.ui.queue_task(lambda: self.ui.flash_setting_change('global_setting_change'))
        elif coord_key == 'complete':
            self.ui.complete_coord_var.set(str(new_pos))
            self.ui.queue_task(lambda: self.ui.flash_setting_change('global_setting_change'))
        elif coord_key.startswith('area_'): # 예: 'area_1_p1', 'area_1_click_coord'
            try:
                parts = coord_key.split('_')
                area_number = int(parts[1])
                key_type = '_'.join(parts[2:]) # 'p1', 'p2', 'click_coord'
                var_key_map = {'p1': 'p1_var', 'p2': 'p2_var', 'click_coord': 'coord_var'}
                var_key = var_key_map[key_type]
                self.ui.area_vars[area_number][var_key].set(str(new_pos))
                # 구역의 '영역' 또는 '클릭' 좌표가 변경될 때 색상 플래시
                if key_type in ['p1', 'p2', 'click_coord']:
                    self.ui.queue_task(lambda: self.ui.flash_setting_change('area_setting_change'))
            except (IndexError, KeyError, ValueError) as e:
                print(f"잘못된 구역 좌표 키입니다: {coord_key}, 오류: {e}")

        self.ui.update_status(f"'{display_name}' 좌표 저장 완료: {new_pos}")
        # 좌표 저장 성공 시 소리 1번 재생
        self.ui.queue_task(lambda: self.ui.play_sound(1))
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
        elif color_key == 'secondary_color': display_name = '2순위 색상'
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

        if color_key == 'main_color':
            self.ui.color_var.set(str(new_color))
            # 기본 색상 설정 변경 시 색상 플래시
            self.ui.queue_task(lambda: self.ui.flash_setting_change('global_setting_change'))
        elif color_key == 'secondary_color':
            self.ui.secondary_color_var.set(str(new_color))
            self.ui.queue_task(lambda: self.ui.flash_setting_change('global_setting_change'))
        elif color_key.startswith('area_'): # 예: 'area_1_color'
            try:
                area_number = int(color_key.split('_')[1]) # '1'
                self.ui.area_vars[area_number]['color_var'].set(str(new_color))
                # 구역 색상 설정 변경 시 창 색상 플래시
                self.ui.queue_task(lambda: self.ui.flash_setting_change('area_setting_change'))
            except (IndexError, ValueError) as e:
                print(f"잘못된 구역 색상 키입니다: {color_key}, 오류: {e}")

        
        self.ui.update_status(f"'{display_name}' 저장 완료: {new_color}")
        # 색상 저장 성공 시 소리 1번 재생
        self.ui.queue_task(lambda: self.ui.play_sound(1))
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

        self.tries_count = 0 # 검색 시작 시 시도 횟수 초기화

        # --- 검색 계획 생성 ---
        # 찾기 버튼을 누르는 시점에 모든 검색 단계를 미리 정의합니다.
        search_plan = []
        # 1. 초기 탐색 계획
        search_plan.append({
            'type': 'initial',
            'search_color': self.color,
            'search_area': self._get_global_search_area(),
            'search_direction': self.search_direction,
            'description': '초기 탐색 (기본 색상)'
        })

        # 2. 재시도 탐색 계획
        if self.use_sequence:
            for area_number, settings in sorted(self.areas.items()):
                if settings['use']:
                    # 이 재시도 단계에서 사용할 탐색 영역과 방향을 결정합니다.
                    retry_search_area = settings['search_area'] if settings['use_area_bounds'] else self._get_global_search_area()
                    retry_search_direction = settings['direction'] if settings['use_direction'] else self.search_direction

                    search_plan.append({
                        'type': 'retry',
                        'area_number': area_number,
                        # 재시도 시 찾을 색상을 이 시점에 고정합니다.
                        'search_color': settings['color'] if settings['use_color'] else self.color,
                        'search_area': retry_search_area,
                        'search_direction': retry_search_direction,
                        'click_coord': settings['click_coord'],
                        'num_retries': settings['clicks'],
                        'offset': settings['offset'],
                        'description': f'구역{area_number} 재시도'
                    })

        self.is_searching = True
        self.ui.queue_task(lambda: self.ui.update_status("색상 검색 중... (ESC로 중지)"))
        self.ui.queue_task(lambda: self.ui.update_button_text("중지 (ESC)"))
        # 찾기 시작 시 소리 2번 재생
        self.ui.queue_task(lambda: self.ui.play_sound(2))
        self.ui.queue_task(lambda: self.ui.update_window_bg('searching'))
        print("--- 색상 검색 시작 ---")

        # 별도 스레드에서 검색 작업 실행 (생성된 계획 전달)
        self.search_thread = threading.Thread(target=self._search_worker, args=(search_plan,), daemon=True)
        self.search_thread.start()

    def stop_search(self, message=None):
        """색상 검색 프로세스를 중지합니다."""
        if not self.is_searching: return
        if not self.ui: return
        self.is_searching = False

        if message is None:
            message = f"검색 종료. 시도 횟수: ({self.tries_count}/{self.total_tries})"

        # 검색 종료와 관련된 모든 UI 업데이트를 하나의 작업으로 묶어 큐에 추가합니다.
        self.ui.queue_task(lambda msg=message: self.ui.set_final_status(msg))
        print(f"--- {message} ---")

    def _handle_found_color(self, found_pos: tuple, success_message: str):
        """색상을 찾았을 때의 공통 처리 로직입니다."""
        if not self.is_searching: return

        # 1. 찾은 위치 클릭
        self.color_finder.click_action(found_pos[0], found_pos[1])

        # 2. 완료 좌표 클릭 (설정된 경우)
        if self.complete_coord != (0, 0):
            final_x, final_y = self.complete_coord
            # '색영역오차'를 완료 클릭 오차로 재사용합니다.
            if self.color_area_tolerance > 0:
                final_x += random.randint(-self.color_area_tolerance, self.color_area_tolerance)
                final_y += random.randint(-self.color_area_tolerance, self.color_area_tolerance)
            
            if self.complete_click_delay > 0:
                time.sleep(self.complete_click_delay)
            
            self.color_finder.click_action(final_x, final_y)
            # 완료 클릭 성공 시 '삐삐삐' 소리를 내도록 UI에 요청합니다.
            if self.ui:
                self.ui.queue_task(lambda: self.ui.play_sound(3))
            status_message = f"{success_message} 후 완료 클릭 ({final_x},{final_y})"
        else:
            status_message = f"{success_message}"

        self.stop_search(message=status_message)

    def _search_worker(self, search_plan: list):
        """(스레드 워커) 전달받은 검색 계획(search_plan)을 순차적으로 실행합니다."""
        
        def execute_single_search(search_area: tuple, search_color: tuple, search_direction: SearchDirection, status_text: str) -> Optional[tuple]:
            """지정된 단일 영역을 탐색하고 결과를 반환합니다."""
            if not self.is_searching: return None

            if not (search_area[2] > search_area[0] and search_area[3] > search_area[1]):
                return None

            self.ui.queue_task(lambda text=status_text: self.ui.update_status(text))

            return self.color_finder.find_color_in_area(
                area=search_area,
                color=search_color,
                tolerance=self.color_tolerance,
                direction=search_direction
            )

        # --- 검색 계획 실행 ---
        if self.use_sequence:
            # [구역 사용 ON]: 초기 탐색 후, 시도 횟수만큼 재시도 순환
            initial_step = search_plan[0]
            
            # 1. 1순위 색상 탐색
            status_text = f"초기 탐색 (1순위): 기본 영역에서 탐색 중 ({initial_step['search_direction'].value})..."
            found_pos = execute_single_search(initial_step['search_area'], initial_step['search_color'], initial_step['search_direction'], status_text)
            if found_pos:
                self._handle_found_color(found_pos, "초기 탐색 중 1순위 색상 발견")
                return

            # 2. 2순위 색상 탐색 (조건부)
            if self.is_searching and self.use_secondary_color:
                status_text = f"초기 탐색 (2순위): 기본 영역에서 탐색 중 ({initial_step['search_direction'].value})..."
                found_pos_secondary = execute_single_search(initial_step['search_area'], self.secondary_color, initial_step['search_direction'], status_text)
                if found_pos_secondary:
                    self._handle_found_color(found_pos_secondary, "초기 탐색 중 2순위 색상 발견")
                    return

            retry_steps = [step for step in search_plan if step['type'] == 'retry']
            if not retry_steps:
                self.stop_search("활성화된 재시도 구역이 없어 중지합니다.")
                return

            retry_cycle = itertools.cycle(retry_steps)
            while self.is_searching and self.tries_count < self.total_tries:
                step = next(retry_cycle)
                final_x, final_y = step['click_coord']
                if step['offset'] > 0:
                    final_x += random.randint(-step['offset'], step['offset'])
                    final_y += random.randint(-step['offset'], step['offset'])

                for i in range(step['num_retries']):
                    if not self.is_searching or self.tries_count >= self.total_tries: break
                    self.tries_count += 1

                    if self.area_delay > 0:
                        # 기본 딜레이에 +-60ms(0.06초)의 랜덤 오차를 추가합니다.
                        random_offset = random.uniform(-0.06, 0.06)
                        final_delay = self.area_delay + random_offset
                        # 최종 딜레이가 음수가 되지 않도록 max(0, ...) 처리합니다.
                        time.sleep(max(0, final_delay))
                    
                    if not self.is_searching: break # 딜레이 후 다시 확인
                    self.color_finder.click_action(final_x, final_y)

                    time.sleep(0.1)
                    search_status_text = f"재탐색: 구역{step['area_number']} ({i+1}/{step['num_retries']}) | ({step['search_direction'].value}) | 총 ({self.tries_count}/{self.total_tries})"
                    found_pos = execute_single_search(step['search_area'], step['search_color'], step['search_direction'], search_status_text)
                    if found_pos:
                        self._handle_found_color(found_pos, f"재시도 중 구역{step['area_number']}에서 색상 발견")
                        return
            
            if self.is_searching:
                # 최대 시도 횟수 도달 시 소리 3번 재생
                self.ui.queue_task(lambda: self.ui.play_sound(3))
                self.stop_search(f"최대 시도 횟수({self.total_tries}) 도달, 검색 중지.")
        else:
            # [구역 사용 OFF]: 색상을 찾을 때까지 초기 탐색만 무한 반복
            initial_step = search_plan[0]
            while self.is_searching:
                # 1. 1순위 색상 탐색
                status_text = f"기본 영역 반복 탐색 (1순위) ({initial_step['search_direction'].value})..."
                found_pos = execute_single_search(initial_step['search_area'], initial_step['search_color'], initial_step['search_direction'], status_text)
                if found_pos:
                    self._handle_found_color(found_pos, "기본 영역에서 1순위 색상 발견")
                    return

                # 2. 2순위 색상 탐색 (조건부)
                if self.is_searching and self.use_secondary_color:
                    status_text = f"기본 영역 반복 탐색 (2순위) ({initial_step['search_direction'].value})..."
                    found_pos_secondary = execute_single_search(initial_step['search_area'], self.secondary_color, initial_step['search_direction'], status_text)
                    if found_pos_secondary:
                        self._handle_found_color(found_pos_secondary, "기본 영역에서 2순위 색상 발견")
                        return

                if self.search_delay > 0:
                    time.sleep(self.search_delay)
