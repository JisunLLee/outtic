import tkinter as tk
import threading
import time
import os
import sys
from pynput import mouse, keyboard
from typing import Optional, TYPE_CHECKING
import ast
import random # 오차 적용을 위해 추가
from PIL import ImageGrab # 화면 캡처를 위해 import 합니다.
import json
from tkinter import filedialog
import itertools # 재시도 순환을 위해 추가

from .color_finder import ColorFinder, SearchDirection

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
        self.shift_press_count = 0
        self.shift_press_timer: Optional[threading.Timer] = None
        self.up_press_count = 0
        self.up_press_timer: Optional[threading.Timer] = None
        self.tries_count = 0 # 현재 시도 횟수
        self.direction_change_pending = False

        # --- 전역 단축키 설정 ---
        # on_press 이벤트만 사용하여 Shift 연속 입력을 감지합니다.
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
        self.keyboard_listener.start()

        # --- 기본값 설정 ---
        # 이 값들은 UI의 초기값을 설정하는 데 사용됩니다.
        # 기본 탐색 영역 목록: 순서대로 탐색하며 못 찾으면 다음 영역으로 넘어갑니다.
        # (구역 내 sub_areas와 동일한 구조. 첫 번째 항목은 새 구역/영역을 만들 때 시드값으로도 쓰입니다.)
        self.initial_areas = {
            1: {
                'p1': (76, 233),
                'p2': (616, 707),
                'direction': SearchDirection.TOP_RIGHT_TO_BOTTOM_LEFT,
                'search_area': (0, 0, 0, 0),
            }
        }
        self.initial_area_order = [1]
        self.color = (190, 168, 134)
        self.complete_coord = (1314,905)
        self.color_tolerance = 15
        self.color_area_tolerance = 5
        self.complete_click_delay = 0.1 # 완료 클릭 전 딜레이 (초), UI 기본값 10 -> 100ms
        
        # 2순위 색상 추가
        self.use_secondary_color = False
        self.secondary_color = (255, 138, 180)

        # --- 구역값 설정 ---
        self.use_initial_search = True # '기본 탐색 사용' 체크박스 기본값
        self.continuous_search = False # '연속 찾기 모드' 체크박스 기본값 (미체크)
        self.research_delay = 0.7 # 재탐색 대기 (초), UI 기본값 700ms
        self.use_sequence = False # 구역 사용 여부 (UI 체크박스 기본값)
        self.use_space_complete = True # 스페이스 완료 사용 여부
        self.area_delay = 0.70 # 구역 클릭 전 딜레이 (초), UI 기본값 30 -> 300ms
        self.use_screen_activation = False # 화면 활성화 사용 여부
        self.use_operation_check = False # 탐색 화면 정상 여부 확인 사용 여부
        self.op_check_coord = (486, 1885)
        self.op_check_color = (0, 0, 0)
        self.op_check_max_retries = 3
        self.op_check_retry_interval = 0.5
        self.empty_coord = (0, 0) # 빈 공간 좌표
        self.use_search_delay = False # 탐색 딜레이 사용 여부
        self.search_delay = 0.20 # 탐색 대기 (초)
        self.total_duration_sec = 1800 # 총 탐색 시간 (초)
        self.active_search_duration_sec = 600 # 한 사이클의 탐색 시간 (초)
        self.wait_duration_sec = 180 # 사이클 간 대기 시간 (초)
        self.search_time_tolerance_sec = 5 # 탐색 시간 오차 (초)

        # --- 구역별 설정 데이터 ---
        self.areas = {}
        self.area_order = []
        # 기본적으로 5개의 구역을 초기화합니다.
        for i in range(1, 6):
            self._initialize_area_settings(i)

    def _sanitize_area_order(self):
        """area_order 리스트와 areas 데이터를 완벽하게 동기화합니다."""
        seen = set()
        clean_order = []
        
        # 1. 현재 순서 리스트에서 실제 존재하는 구역만 중복 없이 추출
        for aid in self.area_order:
            aid_int = int(aid)
            if aid_int in self.areas and aid_int not in seen:
                clean_order.append(aid_int)
                seen.add(aid_int)
        
        # 2. areas에는 있지만 순서 리스트에 누락된 구역들을 뒤에 추가
        for aid in sorted(self.areas.keys()):
            if aid not in seen:
                clean_order.append(aid)
        
        self.area_order = clean_order

    def add_area(self):
        """새로운 구역을 데이터 모델과 UI에 추가합니다."""
        # UI에 방금 입력했지만 아직 적용되지 않은 값(기본 탐색 영역 목록 등)이 새 구역의
        # 시드값으로 쓰이도록, 먼저 현재 UI 상태를 반영합니다.
        self.apply_settings()

        # 비어있는 번호 중 가장 작은 번호를 찾아 새 구역 번호로 사용합니다 (번호 점프 방지).
        new_area_num = 1
        while new_area_num in self.areas:
            new_area_num += 1

        self._initialize_area_settings(new_area_num)
        self.area_order.append(new_area_num)
        if self.ui:
            self.ui.add_area_to_ui(new_area_num)
        self.auto_save_settings() # 추가 즉시 저장
        return new_area_num
    
    def reorder_area(self, area_number, new_index):
        """구역의 탐색 순서를 새로운 위치로 변경합니다 (Drag & Drop)."""
        area_number = int(area_number)
        self._sanitize_area_order()
        
        if area_number in self.area_order:
            self.area_order.remove(area_number)
        
        # 새 위치로 삽입 (인덱스 범위 보정)
        target_idx = max(0, min(new_index, len(self.area_order)))
        self.area_order.insert(target_idx, area_number)
        
        if self.ui:
            self.ui.refresh_area_order()
        self.auto_save_settings()

    def remove_area(self, area_number):
        """지정된 구역을 데이터 모델과 UI에서 제거합니다."""
        if area_number in self.areas:
            del self.areas[area_number]
            if area_number in self.area_order:
                self.area_order.remove(area_number)
            if self.ui:
                self.ui.remove_area_from_ui(area_number)
            self.auto_save_settings() # 삭제 즉시 저장

    def _sanitize_sub_area_order(self, area_number: int):
        """지정된 구역의 sub_area_order 리스트와 sub_areas 데이터를 동기화합니다."""
        area = self.areas[area_number]
        sub_areas = area['sub_areas']
        seen = set()
        clean_order = []

        for sid in area['sub_area_order']:
            sid_int = int(sid)
            if sid_int in sub_areas and sid_int not in seen:
                clean_order.append(sid_int)
                seen.add(sid_int)

        for sid in sorted(sub_areas.keys()):
            if sid not in seen:
                clean_order.append(sid)

        area['sub_area_order'] = clean_order

    def _initialize_sub_area(self, area_number: int, sub_id: int):
        """지정된 구역에 새 영역(sub-area)의 기본 설정값을 생성합니다."""
        area = self.areas[area_number]
        if sub_id not in area['sub_areas']:
            # 기본 탐색 영역 목록의 첫 번째 영역 값을 시드로 사용합니다.
            seed = self.initial_areas[self.initial_area_order[0]]
            area['sub_areas'][sub_id] = {
                'p1': seed['p1'],
                'p2': seed['p2'],
                'direction': seed['direction'],
                'search_area': (0, 0, 0, 0),
            }

    def add_sub_area(self, area_number: int):
        """지정된 구역에 새로운 영역을 추가합니다."""
        # UI에 방금 입력했지만 아직 적용되지 않은 값(기본 탐색 영역 목록 등)이 새 영역의
        # 시드값으로 쓰이도록, 먼저 현재 UI 상태를 반영합니다.
        self.apply_settings()

        area = self.areas[area_number]
        new_sub_id = 1
        while new_sub_id in area['sub_areas']:
            new_sub_id += 1

        self._initialize_sub_area(area_number, new_sub_id)
        area['sub_area_order'].append(new_sub_id)
        if self.ui:
            self.ui.add_subarea_to_ui(area_number)
        self.auto_save_settings()
        return new_sub_id

    def remove_sub_area(self, area_number: int, sub_id: int):
        """지정된 구역의 영역을 제거합니다. 구역에는 최소 1개의 영역이 남아야 합니다."""
        area = self.areas[area_number]
        if len(area['sub_area_order']) <= 1:
            if self.ui:
                self.ui.update_status("구역에는 최소 1개의 영역이 필요합니다.")
            return

        if sub_id in area['sub_areas']:
            del area['sub_areas'][sub_id]
            if sub_id in area['sub_area_order']:
                area['sub_area_order'].remove(sub_id)
            if self.ui:
                self.ui.remove_subarea_from_ui(area_number, sub_id)
            self.auto_save_settings()

    def reorder_sub_area(self, area_number: int, sub_id: int, new_index: int):
        """구역 내 영역의 탐색 순서를 새로운 위치로 변경합니다 (Drag & Drop)."""
        sub_id = int(sub_id)
        area = self.areas[area_number]
        self._sanitize_sub_area_order(area_number)

        if sub_id in area['sub_area_order']:
            area['sub_area_order'].remove(sub_id)

        target_idx = max(0, min(new_index, len(area['sub_area_order'])))
        area['sub_area_order'].insert(target_idx, sub_id)

        if self.ui:
            self.ui.refresh_subarea_order(area_number)
        self.auto_save_settings()

    def _sanitize_initial_area_order(self):
        """initial_area_order 리스트와 initial_areas 데이터를 동기화합니다."""
        seen = set()
        clean_order = []

        for aid in self.initial_area_order:
            aid_int = int(aid)
            if aid_int in self.initial_areas and aid_int not in seen:
                clean_order.append(aid_int)
                seen.add(aid_int)

        for aid in sorted(self.initial_areas.keys()):
            if aid not in seen:
                clean_order.append(aid)

        self.initial_area_order = clean_order

    def _initialize_initial_area(self, area_id: int):
        """기본 탐색 영역 목록에 새 영역의 기본 설정값을 생성합니다."""
        if area_id not in self.initial_areas:
            seed = self.initial_areas[self.initial_area_order[0]]
            self.initial_areas[area_id] = {
                'p1': seed['p1'],
                'p2': seed['p2'],
                'direction': seed['direction'],
                'search_area': (0, 0, 0, 0),
            }

    def add_initial_area(self):
        """기본 탐색 영역 목록에 새로운 영역을 추가합니다."""
        # UI에 방금 입력했지만 아직 적용되지 않은 값이 새 영역의 시드값으로 쓰이도록,
        # 먼저 현재 UI 상태를 반영합니다.
        self.apply_settings()

        new_area_id = 1
        while new_area_id in self.initial_areas:
            new_area_id += 1

        self._initialize_initial_area(new_area_id)
        self.initial_area_order.append(new_area_id)
        if self.ui:
            self.ui.add_initial_area_to_ui()
        self.auto_save_settings()
        return new_area_id

    def remove_initial_area(self, area_id: int):
        """기본 탐색 영역 목록에서 영역을 제거합니다. 최소 1개는 남아야 합니다."""
        if len(self.initial_area_order) <= 1:
            if self.ui:
                self.ui.update_status("기본 탐색 영역은 최소 1개가 필요합니다.")
            return

        if area_id in self.initial_areas:
            del self.initial_areas[area_id]
            if area_id in self.initial_area_order:
                self.initial_area_order.remove(area_id)
            if self.ui:
                self.ui.remove_initial_area_from_ui(area_id)
            self.auto_save_settings()

    def reorder_initial_area(self, area_id: int, new_index: int):
        """기본 탐색 영역의 순서를 새로운 위치로 변경합니다 (Drag & Drop)."""
        area_id = int(area_id)
        self._sanitize_initial_area_order()

        if area_id in self.initial_area_order:
            self.initial_area_order.remove(area_id)

        target_idx = max(0, min(new_index, len(self.initial_area_order)))
        self.initial_area_order.insert(target_idx, area_id)

        if self.ui:
            self.ui.refresh_initial_area_order()
        self.auto_save_settings()

    def set_ui(self, ui: 'AppUI'):
        """
        컨트롤러에 UI 인스턴스를 연결합니다.
        이 메서드는 애플리케이션 시작 시 한 번 호출됩니다.
        """
        self.ui = ui
        self.ui.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.auto_load_settings() # 프로그램 시작 시 마지막 설정 자동 로드

    def _initialize_area_settings(self, area_number: int):
        """컨트롤러 내부에 지정된 구역의 기본 설정값을 생성합니다."""
        if area_number not in self.areas:
            # 구역별 기본값 설정
            default_use = (area_number == 1) # 구역 1만 기본 활성화, 나머지는 비활성화
            default_click_coord = (0, 0)
            default_clicks = 6
            default_offset = 2
            default_name = f"구역{area_number}"

            if area_number == 1:
                default_click_coord = (723, 301)
                default_clicks = 1
            if area_number == 2:
                default_click_coord = (734, 320)
                default_clicks = 1
            if area_number == 3:
                default_click_coord = (716, 304)
                default_clicks = 2
            if area_number == 4:
                default_click_coord = (737, 321)
                default_clicks = 1

            # 구역 내 영역(sub-area) 목록: 기본 탐색 영역 목록을 순서 그대로 복사해서 시작합니다.
            # 순서대로 탐색하며 못 찾으면 다음 영역으로 넘어갑니다.
            sub_areas = {}
            sub_area_order = []
            for sub_id, initial_id in enumerate(self.initial_area_order, start=1):
                seed = self.initial_areas[initial_id]
                sub_areas[sub_id] = {
                    'p1': seed['p1'],
                    'p2': seed['p2'],
                    'direction': seed['direction'],
                    'search_area': (0, 0, 0, 0), # 계산된 탐색 영역
                }
                sub_area_order.append(sub_id)

            self.areas[area_number] = {
                'name': default_name,
                'use': default_use, # UI의 '탐색' 체크박스는 기본적으로 꺼져있습니다.
                'click_coord': default_click_coord,
                'clicks': default_clicks, # 구역 클릭 횟수
                'offset': default_offset, # 구역 클릭 범위 오차
                'use_color': False, # '기본' 색상 사용 (UI 체크박스 True)
                'color': (0, 0, 0),
                'sub_areas': sub_areas,
                'sub_area_order': sub_area_order,
            }

    def on_closing(self):
        """창을 닫을 때 리소스를 안전하게 정리합니다."""
        self.is_searching = False
        # 종료 전 현재 설정을 'last_settings.json'에 자동 저장
        if self.ui:
            self.apply_settings()
            self.auto_save_settings()
        self.keyboard_listener.stop()
        self.ui.root.destroy()

    def apply_settings(self):
        """UI의 설정값들을 컨트롤러의 속성에 적용합니다."""
        if not self.ui: return False
        try:
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
                "→↓ (q)": SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT,
                "←↓ (w)": SearchDirection.TOP_RIGHT_TO_BOTTOM_LEFT,
                "→↑ (a)": SearchDirection.BOTTOM_LEFT_TO_TOP_RIGHT,
                "←↑ (s)": SearchDirection.BOTTOM_RIGHT_TO_TOP_LEFT,
                "↓→ (e)": SearchDirection.TOP_TO_BOTTOM_LEFT_TO_RIGHT,
                "↓← (r)": SearchDirection.TOP_TO_BOTTOM_RIGHT_TO_LEFT,
                "↑→ (d)": SearchDirection.BOTTOM_TO_TOP_LEFT_TO_RIGHT,
                "↑← (f)": SearchDirection.BOTTOM_TO_TOP_RIGHT_TO_LEFT,
                "↓↔ (z)": SearchDirection.CENTER_TOP_TO_BOTTOM,
                "↑↔ (x)": SearchDirection.CENTER_BOTTOM_TO_TOP,
                "→↕ (c)": SearchDirection.CENTER_LEFT_TO_RIGHT,
                "←↕ (v)": SearchDirection.CENTER_RIGHT_TO_LEFT,
                "중앙 ☉ (g)": SearchDirection.CENTER_TO_CENTER,
            }
            self.use_initial_search = self.ui.use_initial_search_var.get()
            self.continuous_search = self.ui.continuous_search_var.get()
            self.use_space_complete = self.ui.use_space_complete_var.get()
            self.use_sequence = self.ui.use_sequence_var.get()
            self.use_screen_activation = self.ui.use_screen_activation_var.get()
            self.use_operation_check = self.ui.use_operation_check_var.get()
            self.op_check_coord = ast.literal_eval(self.ui.op_check_coord_var.get())
            self.op_check_color = ast.literal_eval(self.ui.op_check_color_var.get())
            self.op_check_max_retries = int(self.ui.op_check_max_retries_var.get())
            self.op_check_retry_interval = int(self.ui.op_check_retry_interval_var.get()) / 100.0
            self.empty_coord = ast.literal_eval(self.ui.empty_coord_var.get())
            self.total_duration_sec = int(self.ui.total_duration_var.get())
            self.active_search_duration_sec = int(self.ui.active_search_duration_var.get())
            self.wait_duration_sec = int(self.ui.wait_duration_var.get())
            self.search_time_tolerance_sec = int(self.ui.search_time_tolerance_var.get())
            self.research_delay = int(self.ui.research_delay_var.get()) / 1000.0

            # --- 기본 탐색 영역 목록 적용 ---
            for area_id, initial_ui_vars in self.ui.initial_area_vars.items():
                if area_id not in self.initial_areas:
                    self._initialize_initial_area(area_id)
                initial_settings = self.initial_areas[area_id]
                initial_settings['p1'] = ast.literal_eval(initial_ui_vars['p1_var'].get())
                initial_settings['p2'] = ast.literal_eval(initial_ui_vars['p2_var'].get())
                initial_settings['direction'] = direction_map.get(initial_ui_vars['direction_var'].get(), SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT)

                p1 = initial_settings['p1']
                p2 = initial_settings['p2']
                initial_settings['search_area'] = (min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1]))

            # --- 구역 설정 적용 ---
            for area_number, area_ui_vars in self.ui.area_vars.items():
                if area_number not in self.areas:
                    self._initialize_area_settings(area_number)
                
                area_settings = self.areas[area_number]
                area_settings['name'] = area_ui_vars['name_var'].get()
                area_settings['use'] = area_ui_vars['use_var'].get()
                area_settings['click_coord'] = ast.literal_eval(area_ui_vars['coord_var'].get())
                area_settings['clicks'] = int(area_ui_vars['clicks_var'].get())
                area_settings['offset'] = int(area_ui_vars['offset_var'].get())
                area_settings['use_color'] = not area_ui_vars['use_color_var'].get() # UI와 논리 반대. '기본' 체크 해제 시 개별 색상 사용
                area_settings['color'] = ast.literal_eval(area_ui_vars['color_var'].get())

                # 구역 내 영역(sub-area)별 탐색 영역/방향을 UI 값으로 재계산합니다.
                for sub_id, sub_ui_vars in area_ui_vars['sub_area_vars'].items():
                    if sub_id not in area_settings['sub_areas']:
                        self._initialize_sub_area(area_number, sub_id)
                    sub_settings = area_settings['sub_areas'][sub_id]
                    sub_settings['p1'] = ast.literal_eval(sub_ui_vars['p1_var'].get())
                    sub_settings['p2'] = ast.literal_eval(sub_ui_vars['p2_var'].get())
                    sub_settings['direction'] = direction_map.get(sub_ui_vars['direction_var'].get(), SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT)

                    p1 = sub_settings['p1']
                    p2 = sub_settings['p2']
                    sub_settings['search_area'] = (min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1]))


            self.ui.update_status("설정이 적용되었습니다.")
            print("설정이 적용되었습니다.")
            
            # 설정이 성공적으로 적용되면 즉시 자동 저장 수행 (코드 수정 재시작 대응)
            self.auto_save_settings()
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

        visual_steps = []

        # 1. 기본 탐색 영역들 (순서대로 탐색하는 영역 목록을 한꺼번에 표시)
        initial_area_markers = []
        for idx, area_id in enumerate(self.initial_area_order):
            x1, y1, x2, y2 = self.initial_areas[area_id]['search_area']
            initial_area_markers.append({
                'type': 'area',
                'rect': (x1, y1, x2 - x1, y2 - y1),
                'color': 'red',
                'alpha': 0.3,
                'text': f'기본 영역{idx + 1}'
            })
        visual_steps.append(initial_area_markers)

        # 2. 완료 좌표
        visual_steps.append([{
            'type': 'point',
            'text': '완료',
            'pos': self.complete_coord,
            'color': '#50E3C2'
        }])

        # 3. 구역별 설정 (켜져 있을 때만)
        if self.use_sequence:
            area_overlay_colors = ['cyan', 'magenta', 'yellow', 'lime', 'orange', 'purple']
            for area_number in self.area_order:
                settings = self.areas.get(area_number)
                if settings and settings['use'] and settings['click_coord'] != (0, 0):
                    marker_color = area_overlay_colors[(area_number - 1) % len(area_overlay_colors)]
                    
                    step_markers = []
                    # 구역 내 영역(sub-area)들을 순서대로 모두 표시
                    area_name = settings.get('name', f'구역{area_number}')
                    for idx, sub_id in enumerate(settings['sub_area_order']):
                        sub_settings = settings['sub_areas'][sub_id]
                        sx1, sy1, sx2, sy2 = sub_settings['search_area']
                        step_markers.append({
                            'type': 'area',
                            'rect': (sx1, sy1, sx2 - sx1, sy2 - sy1),
                            'color': marker_color,
                            'alpha': 0.4,
                            'text': f"{area_name} 영역{idx + 1}"
                        })

                    # 구역 클릭 좌표
                    step_markers.append({
                        'type': 'point',
                        'text': settings.get('name', str(area_number)),
                        'pos': settings['click_coord'],
                        'color': marker_color
                    })
                    visual_steps.append(step_markers)

        self.ui.display_visual_aids(visual_steps)

    def _serialize_initial_areas(self) -> list:
        """기본 탐색 영역 목록을 JSON 직렬화 가능한 리스트로 변환합니다."""
        return [
            {
                'p1': self.initial_areas[aid]['p1'],
                'p2': self.initial_areas[aid]['p2'],
                'direction': self.initial_areas[aid]['direction'].value, # Enum을 문자열로 저장
            }
            for aid in self.initial_area_order
        ]

    def _deserialize_initial_areas(self, settings_data: dict):
        """JSON에서 불러온 기본 탐색 영역 목록을 컨트롤러 상태에 반영합니다 (구버전 형식 자동 변환 포함)."""
        loaded_initial_areas = settings_data.get('initial_areas')
        if loaded_initial_areas is None:
            # 구버전 형식(최상위 p1/p2/search_direction 단일값)을 영역 1개짜리 목록으로 변환합니다.
            loaded_initial_areas = [{
                'p1': settings_data.get('p1', (76, 233)),
                'p2': settings_data.get('p2', (616, 707)),
                'direction': settings_data.get('search_direction', SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT.value),
            }]

        self.initial_areas = {}
        self.initial_area_order = []
        for area_id, loaded in enumerate(loaded_initial_areas, start=1):
            p1 = tuple(loaded.get('p1', (76, 233)))
            p2 = tuple(loaded.get('p2', (616, 707)))
            self.initial_areas[area_id] = {
                'p1': p1,
                'p2': p2,
                'direction': SearchDirection(loaded.get('direction', SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT.value)),
                'search_area': (min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1])),
            }
            self.initial_area_order.append(area_id)

    def _serialize_area(self, area_settings: dict) -> dict:
        """구역 설정 하나를 JSON 직렬화 가능한 dict로 변환합니다."""
        return {
            'name': area_settings['name'],
            'use': area_settings['use'],
            'click_coord': area_settings['click_coord'],
            'clicks': area_settings['clicks'],
            'offset': area_settings['offset'],
            'use_color': area_settings['use_color'],
            'color': area_settings['color'],
            'sub_areas': [
                {
                    'p1': area_settings['sub_areas'][sid]['p1'],
                    'p2': area_settings['sub_areas'][sid]['p2'],
                    'direction': area_settings['sub_areas'][sid]['direction'].value, # Enum을 문자열로 저장
                }
                for sid in area_settings['sub_area_order']
            ],
        }

    def _deserialize_area(self, area_number: int, loaded: dict):
        """JSON에서 불러온 구역 설정 하나를 컨트롤러 상태에 반영합니다 (구버전 형식 자동 변환 포함)."""
        self._initialize_area_settings(area_number)
        area = self.areas[area_number]
        area['name'] = loaded.get('name', f"구역{area_number}")
        area['use'] = bool(loaded.get('use', area['use']))
        area['click_coord'] = tuple(loaded.get('click_coord', area['click_coord']))
        area['clicks'] = int(loaded.get('clicks', area['clicks']))
        area['offset'] = int(loaded.get('offset', area['offset']))
        area['use_color'] = bool(loaded.get('use_color', area['use_color']))
        area['color'] = tuple(loaded.get('color', area['color']))

        # 개별 필드가 누락됐을 때 쓸 기본값(이 구역이 처음 초기화될 때 시드된 값).
        default_sub = area['sub_areas'][area['sub_area_order'][0]]

        loaded_sub_areas = loaded.get('sub_areas')
        if loaded_sub_areas is None:
            # 구버전 형식(구역당 영역이 1개뿐이고 p1/p2/direction이 구역에 직접 있던 형식)을
            # 영역이 1개인 sub_areas 리스트로 변환합니다.
            loaded_sub_areas = [{
                'p1': loaded.get('p1', default_sub['p1']),
                'p2': loaded.get('p2', default_sub['p2']),
                'direction': loaded.get('direction', default_sub['direction'].value),
            }]

        area['sub_areas'] = {}
        area['sub_area_order'] = []
        for sub_id, sub_loaded in enumerate(loaded_sub_areas, start=1):
            p1 = tuple(sub_loaded.get('p1', default_sub['p1']))
            p2 = tuple(sub_loaded.get('p2', default_sub['p2']))
            area['sub_areas'][sub_id] = {
                'p1': p1,
                'p2': p2,
                'direction': SearchDirection(sub_loaded.get('direction', default_sub['direction'].value)),
                'search_area': (min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1])),
            }
            area['sub_area_order'].append(sub_id)

    def save_settings(self):
        """현재 설정을 JSON 파일로 저장합니다."""
        if not self.ui: return
        if not self.apply_settings():
            self.ui.update_status("설정 저장 실패: 현재 설정에 오류가 있습니다.")
            return

        settings_data = {
            'initial_areas': self._serialize_initial_areas(),
            'color': self.color,
            'use_secondary_color': self.use_secondary_color,
            'secondary_color': self.secondary_color,
            'complete_coord': self.complete_coord,
            'color_tolerance': self.color_tolerance,
            'color_area_tolerance': self.color_area_tolerance,
            'complete_click_delay': self.complete_click_delay,
            'use_sequence': self.use_sequence,
            'continuous_search': self.continuous_search,
            'use_space_complete': self.use_space_complete,
            'use_screen_activation': self.use_screen_activation,
            'use_operation_check': self.use_operation_check,
            'op_check_coord': self.op_check_coord,
            'op_check_color': self.op_check_color,
            'op_check_max_retries': self.op_check_max_retries,
            'op_check_retry_interval': self.op_check_retry_interval,
            'empty_coord': self.empty_coord,
            'use_search_delay': self.use_search_delay,
            'use_initial_search': self.use_initial_search,
            'research_delay': self.research_delay,
            'area_delay': self.area_delay,
            'search_delay': self.search_delay,
            'total_duration_sec': self.total_duration_sec,
            'active_search_duration_sec': self.active_search_duration_sec,
            'wait_duration_sec': self.wait_duration_sec,
            'search_time_tolerance_sec': self.search_time_tolerance_sec,
            'areas': {},
            'area_order': self.area_order
        }

        for area_number, area_settings in self.areas.items():
            settings_data['areas'][area_number] = self._serialize_area(area_settings)

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

    def _get_app_data_dir(self) -> str:
        """
        자동 저장/불러오기에 사용할 안정적인 폴더 경로를 반환합니다.
        PyInstaller `--onefile`로 빌드된 exe는 매 실행마다 새로운 임시 폴더에 압축을
        풀기 때문에, __file__ 기준 경로를 쓰면 'last_settings.json'이 실행할 때마다
        새 폴더에 저장되어 다음 실행 때 이전 설정을 찾지 못합니다(구역 탐색이 켜져 있어도
        구역이 모두 기본값으로 초기화되어 "활성화된 재시도 구역이 없어 중지합니다"가 뜨는 원인).
        따라서 빌드된 실행 파일(sys.frozen)일 때는 exe가 실제로 위치한 폴더를 사용합니다.
        """
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def auto_save_settings(self):
        """별도의 창 없이 'last_settings.json' 파일에 현재 설정을 저장합니다."""
        save_path = os.path.join(self._get_app_data_dir(), 'last_settings.json')
        
        settings_data = {
            'initial_areas': self._serialize_initial_areas(),
            'color': self.color,
            'use_secondary_color': self.use_secondary_color,
            'secondary_color': self.secondary_color,
            'complete_coord': self.complete_coord,
            'color_tolerance': self.color_tolerance,
            'color_area_tolerance': self.color_area_tolerance,
            'complete_click_delay': self.complete_click_delay,
            'use_sequence': self.use_sequence,
            'continuous_search': self.continuous_search,
            'use_space_complete': self.use_space_complete,
            'use_screen_activation': self.use_screen_activation,
            'use_operation_check': self.use_operation_check,
            'op_check_coord': self.op_check_coord,
            'op_check_color': self.op_check_color,
            'op_check_max_retries': self.op_check_max_retries,
            'op_check_retry_interval': self.op_check_retry_interval,
            'empty_coord': self.empty_coord,
            'use_search_delay': self.use_search_delay,
            'use_initial_search': self.use_initial_search,
            'research_delay': self.research_delay,
            'area_delay': self.area_delay,
            'search_delay': self.search_delay,
            'total_duration_sec': self.total_duration_sec,
            'active_search_duration_sec': self.active_search_duration_sec,
            'wait_duration_sec': self.wait_duration_sec,
            'search_time_tolerance_sec': self.search_time_tolerance_sec,
            'areas': {},
            'area_order': self.area_order
        }

        for area_number, area_settings in self.areas.items():
            settings_data['areas'][area_number] = self._serialize_area(area_settings)

        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, ensure_ascii=False, indent=4)
            print(f"자동 저장 완료: {save_path}")
        except Exception as e:
            print(f"자동 저장 실패: {e}")

    def auto_load_settings(self):
        """프로그램 시작 시 'last_settings.json' 파일이 있으면 자동으로 불러옵/니다."""
        load_path = os.path.join(self._get_app_data_dir(), 'last_settings.json')
        if not os.path.exists(load_path):
            return

        try:
            with open(load_path, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)

            # 불러오기 전 기존 데이터 및 UI 완전 초기화
            if self.ui:
                self.ui.reset_areas_ui()
                self.ui.reset_initial_areas_ui()
            self.areas = {}
            self.area_order = []

            # 기본 탐색 영역 목록은 구역들의 시드값으로도 쓰이므로 구역 로드보다 먼저 반영합니다.
            self._deserialize_initial_areas(settings_data)

            self.color = tuple(settings_data.get('color', self.color))
            self.use_secondary_color = bool(settings_data.get('use_secondary_color', self.use_secondary_color))
            self.secondary_color = tuple(settings_data.get('secondary_color', self.secondary_color))
            self.complete_coord = tuple(settings_data.get('complete_coord', self.complete_coord))
            self.color_tolerance = int(settings_data.get('color_tolerance', self.color_tolerance))
            self.color_area_tolerance = int(settings_data.get('color_area_tolerance', self.color_area_tolerance))
            self.complete_click_delay = float(settings_data.get('complete_click_delay', self.complete_click_delay))
            self.use_initial_search = bool(settings_data.get('use_initial_search', self.use_initial_search))
            self.continuous_search = bool(settings_data.get('continuous_search', not settings_data.get('exit_after_select', not self.continuous_search)))
            self.use_space_complete = bool(settings_data.get('use_space_complete', self.use_space_complete))
            self.use_screen_activation = bool(settings_data.get('use_screen_activation', self.use_screen_activation))
            self.use_operation_check = bool(settings_data.get('use_operation_check', self.use_operation_check))
            self.op_check_coord = tuple(settings_data.get('op_check_coord', self.op_check_coord))
            self.op_check_color = tuple(settings_data.get('op_check_color', self.op_check_color))
            self.op_check_max_retries = int(settings_data.get('op_check_max_retries', self.op_check_max_retries))
            self.op_check_retry_interval = float(settings_data.get('op_check_retry_interval', self.op_check_retry_interval))
            self.empty_coord = tuple(settings_data.get('empty_coord', self.empty_coord))
            self.use_search_delay = bool(settings_data.get('use_search_delay', self.use_search_delay))
            self.research_delay = float(settings_data.get('research_delay', self.research_delay))
            self.use_sequence = bool(settings_data.get('use_sequence', self.use_sequence))
            self.area_delay = float(settings_data.get('area_delay', self.area_delay))
            self.search_delay = float(settings_data.get('search_delay', self.search_delay))
            self.total_duration_sec = int(settings_data.get('total_duration_sec', self.total_duration_sec))
            self.active_search_duration_sec = int(settings_data.get('active_search_duration_sec', self.active_search_duration_sec))
            self.wait_duration_sec = int(settings_data.get('wait_duration_sec', self.wait_duration_sec))
            self.search_time_tolerance_sec = int(settings_data.get('search_time_tolerance_sec', self.search_time_tolerance_sec))
            self.area_order = settings_data.get('area_order', [])

            loaded_areas = settings_data.get('areas', {})
            for area_number_str, loaded in loaded_areas.items():
                area_number = int(area_number_str)
                # 'loaded'에 일부 키가 없거나 area가 비어 있어도 문제가 없도록,
                # 기본값으로 초기화한 뒤 저장된 값을 덮어씁니다 (구버전 형식은 내부에서 자동 변환됩니다).
                self._deserialize_area(area_number, loaded)

            self._sanitize_area_order()

            if self.ui:
                self.ui.update_ui_from_controller()
                self.ui.update_status("이전 세션의 설정을 자동으로 불러왔습니다.")
        except Exception as e:
            print(f"자동 로드 실패: {e}")

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

            # 불러오기 전 기존 데이터 및 UI 완전 초기화
            if self.ui:
                self.ui.reset_areas_ui()
                self.ui.reset_initial_areas_ui()
            self.areas = {}
            self.area_order = []

            # 기본 탐색 영역 목록은 구역들의 시드값으로도 쓰이므로 구역 로드보다 먼저 반영합니다.
            self._deserialize_initial_areas(settings_data)

            # 컨트롤러 속성 업데이트 (get 메서드로 기본값 보장)
            self.color = tuple(settings_data.get('color', self.color))
            self.use_secondary_color = bool(settings_data.get('use_secondary_color', self.use_secondary_color))
            self.secondary_color = tuple(settings_data.get('secondary_color', self.secondary_color))
            self.complete_coord = tuple(settings_data.get('complete_coord', self.complete_coord))
            self.color_tolerance = int(settings_data.get('color_tolerance', self.color_tolerance))
            self.color_area_tolerance = int(settings_data.get('color_area_tolerance', self.color_area_tolerance))
            self.complete_click_delay = float(settings_data.get('complete_click_delay', self.complete_click_delay))
            self.use_initial_search = bool(settings_data.get('use_initial_search', self.use_initial_search))
            self.continuous_search = bool(settings_data.get('continuous_search', not settings_data.get('exit_after_select', not self.continuous_search)))
            self.use_space_complete = bool(settings_data.get('use_space_complete', self.use_space_complete))
            self.use_screen_activation = bool(settings_data.get('use_screen_activation', self.use_screen_activation))
            self.use_operation_check = bool(settings_data.get('use_operation_check', self.use_operation_check))
            self.op_check_coord = tuple(settings_data.get('op_check_coord', self.op_check_coord))
            self.op_check_color = tuple(settings_data.get('op_check_color', self.op_check_color))
            self.op_check_max_retries = int(settings_data.get('op_check_max_retries', self.op_check_max_retries))
            self.op_check_retry_interval = float(settings_data.get('op_check_retry_interval', self.op_check_retry_interval))
            self.empty_coord = tuple(settings_data.get('empty_coord', self.empty_coord))
            self.use_search_delay = bool(settings_data.get('use_search_delay', self.use_search_delay))
            self.research_delay = float(settings_data.get('research_delay', self.research_delay))
            self.use_sequence = bool(settings_data.get('use_sequence', self.use_sequence))
            self.area_delay = float(settings_data.get('area_delay', self.area_delay))
            self.search_delay = float(settings_data.get('search_delay', self.search_delay))
            self.total_duration_sec = int(settings_data.get('total_duration_sec', self.total_duration_sec))
            self.active_search_duration_sec = int(settings_data.get('active_search_duration_sec', self.active_search_duration_sec))
            self.wait_duration_sec = int(settings_data.get('wait_duration_sec', self.wait_duration_sec))
            self.search_time_tolerance_sec = int(settings_data.get('search_time_tolerance_sec', self.search_time_tolerance_sec))
            self.area_order = settings_data.get('area_order', [])

            loaded_areas = settings_data.get('areas', {})
            for area_number_str, loaded in loaded_areas.items():
                area_number = int(area_number_str)
                # 'loaded'에 일부 키가 없거나 area가 비어 있어도 문제가 없도록,
                # 기본값으로 초기화한 뒤 저장된 값을 덮어씁니다 (구버전 형식은 내부에서 자동 변환됩니다).
                self._deserialize_area(area_number, loaded)

            self._sanitize_area_order()

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
        if coord_key == 'complete': display_name = '완료'
        elif coord_key == 'empty_coord': display_name = '빈공간'
        elif coord_key == 'area_op_check_coord': display_name = '화면확인 좌표'
        elif coord_key.startswith('initial_'):
            # 예: 'initial_1_p1' -> 기본 영역1 ↖영역
            parts = coord_key.split('_')
            area_id, type_key = parts[1], parts[2]
            type_map = {'p1': '↖영역', 'p2': '↘영역'}
            display_name = f"기본 영역{area_id} {type_map.get(type_key, type_key)}"
        elif coord_key.startswith('area_') and '_sub_' in coord_key:
            # 예: 'area_1_sub_2_p1' -> 구역1 영역2 ↖영역
            parts = coord_key.split('_')
            area_num, sub_id, type_key = parts[1], parts[3], parts[4]
            type_map = {'p1': '↖영역', 'p2': '↘영역'}
            display_name = f"구역{area_num} 영역{sub_id} {type_map.get(type_key, type_key)}"
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
        if coord_key.startswith('initial_'): # 예: 'initial_1_p1'
            try:
                parts = coord_key.split('_')
                area_id = int(parts[1])
                key_type = parts[2] # 'p1' or 'p2'
                var_key_map = {'p1': 'p1_var', 'p2': 'p2_var'}
                var_key = var_key_map[key_type]
                self.ui.initial_area_vars[area_id][var_key].set(str(new_pos))
                self.ui.queue_task(lambda: self.ui.flash_setting_change('global_setting_change'))
            except (IndexError, KeyError, ValueError) as e:
                print(f"잘못된 기본 영역 좌표 키입니다: {coord_key}, 오류: {e}")
        elif coord_key == 'complete':
            self.ui.complete_coord_var.set(str(new_pos))
            self.ui.queue_task(lambda: self.ui.flash_setting_change('global_setting_change'))
        elif coord_key == 'empty_coord':
            self.ui.empty_coord_var.set(str(new_pos))
            self.ui.queue_task(lambda: self.ui.flash_setting_change('global_setting_change'))
        elif coord_key == 'area_op_check_coord':
            self.ui.op_check_coord_var.set(str(new_pos))
            self.ui.queue_task(lambda: self.ui.flash_setting_change('area_setting_change'))
        elif coord_key.startswith('area_') and '_sub_' in coord_key: # 예: 'area_1_sub_2_p1'
            try:
                parts = coord_key.split('_')
                area_number = int(parts[1])
                sub_id = int(parts[3])
                key_type = parts[4] # 'p1' or 'p2'
                var_key_map = {'p1': 'p1_var', 'p2': 'p2_var'}
                var_key = var_key_map[key_type]
                self.ui.area_vars[area_number]['sub_area_vars'][sub_id][var_key].set(str(new_pos))
                self.ui.queue_task(lambda: self.ui.flash_setting_change('area_setting_change'))
            except (IndexError, KeyError, ValueError) as e:
                print(f"잘못된 영역 좌표 키입니다: {coord_key}, 오류: {e}")
        elif coord_key.startswith('area_'): # 예: 'area_1_click_coord'
            try:
                parts = coord_key.split('_')
                area_number = int(parts[1])
                key_type = '_'.join(parts[2:]) # 'click_coord'
                var_key_map = {'click_coord': 'coord_var'}
                var_key = var_key_map[key_type]
                self.ui.area_vars[area_number][var_key].set(str(new_pos))
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
        elif color_key == 'area_op_check_color': display_name = '화면확인 색상'
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
        elif color_key == 'area_op_check_color':
            self.ui.op_check_color_var.set(str(new_color))
            self.ui.queue_task(lambda: self.ui.flash_setting_change('area_setting_change'))
        elif color_key.startswith('area_'): # 예: 'area_1_color'
            try:
                area_number = int(color_key.split('_')[1]) # '1'
                self.ui.area_vars[area_number]['color_var'].set(str(new_color))
                # 구역 색상 설정 변경 시 창 색상 플래시
                self.ui.queue_task(lambda: self.ui.flash_setting_change('area_setting_change'))
            except (IndexError, ValueError) as e:
                print(f"잘못된 구역 색상 키입니다: {color_key}, 오류: {e}")

        
        self.ui.queue_task(lambda: self.ui.play_sound(1))
        print(f"색상 저장 완료 ({color_key}): {new_color}")

    def start_combined_picker(self, prefix: str):
        """좌표와 색상을 한 번에 캡처하는 프로세스를 시작합니다. (화면확인용)"""
        if not self.ui: return
        display_name = "화면확인(좌표&색상)"
        self.ui.update_status(f"'{display_name}' 지정: 2초 후 마우스 위치의 좌표와 색상을 저장합니다...")
        self.ui.root.after(2000, lambda: self._grab_combined_after_delay(prefix, display_name))

    def _grab_combined_after_delay(self, prefix: str, display_name: str):
        """마우스 위치에서 좌표와 색상을 동시에 가져와 저장합니다."""
        if not self.ui: return
        x, y = self.mouse_controller.position
        pos = (int(x), int(y))
        
        # 화면 전체 캡처 후 마우스 위치의 색상 추출 (Retina 스케일링 대응)
        screenshot = ImageGrab.grab()
        img_w, _ = screenshot.size
        screen_w = self.ui.root.winfo_screenwidth()
        scale = img_w / screen_w
        color = screenshot.getpixel((int(x * scale), int(y * scale)))[:3]

        if prefix == 'op_check':
            self.ui.op_check_coord_var.set(str(pos))
            self.ui.op_check_color_var.set(str(color))
            self.ui.queue_task(lambda: self.ui.flash_setting_change('area_setting_change'))

        self.ui.update_status(f"'{display_name}' 저장 완료: 좌표{pos}, 색상{color}")
        self.ui.queue_task(lambda: self.ui.play_sound(1))
        print(f"통합 저장 완료 ({prefix}): {pos}, {color}")


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
            
        # --- 탐색 모드 분기 처리 ---
        # '기본 탐색'과 '구역 탐색'이 모두 해제되어 있는 경우
        if not self.use_initial_search and not self.use_sequence:
            if self.use_space_complete:
                # 자동 탐색 없이 스페이스바 입력만 대기하는 '수동 모드'
                self.is_searching = True
                self.ui.queue_task(lambda: self.ui.update_status("스페이스바 대기 중... (Space: 완료 / ESC: 중지)"))
                self.ui.queue_task(lambda: self.ui.update_button_text("중지 (ESC)"))
                self.ui.queue_task(lambda: self.ui.update_window_bg('searching'))
                print("--- 스페이스 완료 모드 시작 (수동) ---")
                return
            else:
                # 자동 탐색도 꺼져 있고 스페이스 모드도 아니면 동작하지 않습니다.
                self.ui.update_status("'기본 탐색' 또는 '구역 탐색'을 체크해야 시작됩니다.")
                return

        self.tries_count = 0 # 검색 시작 시 시도 횟수 초기화

        # --- 검색 계획 생성 ---
        # 찾기 버튼을 누르는 시점에 모든 검색 단계를 미리 정의합니다.
        search_plan = []
        # 1. 초기 탐색 계획 (기본 탐색 영역들을 순서대로 시도, 못 찾으면 다음 영역으로 폴백)
        search_plan.append({
            'type': 'initial',
            'search_color': self.color,
            'initial_areas': [
                {
                    'search_area': self.initial_areas[aid]['search_area'],
                    'search_direction': self.initial_areas[aid]['direction'],
                }
                for aid in self.initial_area_order
            ],
            'description': '초기 탐색 (기본 색상)'
        })

        # 2. 재시도 탐색 계획
        if self.use_sequence:
            for area_number in self.area_order:
                settings = self.areas[area_number]
                if settings['use'] and settings['click_coord'] != (0, 0):
                    # 이 재시도 단계에서 순서대로 시도할 영역(sub-area)들의 탐색 영역과 방향을 결정합니다.
                    # 앞의 영역에서 색을 찾지 못하면 다음 영역으로 넘어가며 시도합니다.
                    sub_area_plans = [
                        {
                            'search_area': settings['sub_areas'][sid]['search_area'],
                            'search_direction': settings['sub_areas'][sid]['direction'],
                        }
                        for sid in settings['sub_area_order']
                    ]

                    search_plan.append({
                        'type': 'retry',
                        'area_number': area_number,
                        # 재시도 시 찾을 색상을 이 시점에 고정합니다.
                        'search_color': settings['color'] if settings['use_color'] else self.color,
                        'sub_areas': sub_area_plans,
                        'click_coord': settings['click_coord'],
                        'num_retries': settings['clicks'],
                        'offset': settings['offset'],
                        'description': f'구역{area_number} 재시도'
                    })

        self.is_searching = True
        status_text = "색상 검색 중... (ESC로 중지)"
        if self.use_space_complete:
            status_text = "자동 탐색 및 스페이스 대기 중... (ESC로 중지)"
        self.ui.queue_task(lambda text=status_text: self.ui.update_status(text))
        
        self.ui.queue_task(lambda: self.ui.update_button_text("중지 (ESC)"))
        self.ui.queue_task(lambda: self.ui.update_window_bg('searching'))
        self.ui.queue_task(lambda: self.ui.update_button_text("중지 (Shift x2 / ESC)"))
        print("--- 색상 검색 시작 ---")

        # 별도 스레드에서 검색 작업 실행 (생성된 계획 전달)
        self.search_thread = threading.Thread(target=self._search_worker, args=(search_plan,), daemon=True)
        self.search_thread.start()

    def stop_search(self, message=None, play_sound=True):
        """색상 검색 프로세스를 중지합니다."""
        if not self.is_searching: return
        if not self.ui: return
        self.is_searching = False

        if message is None:
            message = "검색이 종료되었습니다."

        # 검색 종료와 관련된 모든 UI 업데이트를 하나의 작업으로 묶어 큐에 추가합니다.
        self.ui.queue_task(lambda msg=message: self.ui.set_final_status(msg))
        
        if play_sound:
            self.ui.queue_task(lambda: self.ui.play_sound(1))

        self.ui.queue_task(lambda: self.ui.update_button_text("찾기 (Shift x2)"))
        self.ui.queue_task(lambda: self.ui.update_button_text("찾기 (Shift x2 / ESC)"))
        print(f"--- {message} ---")

    def _handle_found_color(self, found_pos: tuple, success_message: str):
        """색상을 찾았을 때의 공통 처리 로직입니다."""
        if not self.is_searching: return

        # 화면 활성화 기능이 켜져 있으면, 색상 클릭 전에 빈 공간을 먼저 클릭합니다.
        if self.use_screen_activation and self.empty_coord != (0, 0):
            # 빈 공간을 두 번 클릭하여 창을 확실히 활성화합니다.
            click_x, click_y = self.empty_coord
            self.color_finder.click_action(click_x, click_y) # 첫 번째 클릭
            self.color_finder.click_action(click_x, click_y) # 두 번째 클릭
            self.color_finder.click_action(click_x, click_y) # 세 번째 클릭
            time.sleep(0.1) # Chrome 등 브라우저가 클릭을 처리할 시간을 확보하기 위한 대기
        # 1. 찾은 위치(색상 영역의 중심)를 클릭합니다.
        if found_pos and found_pos != (0, 0):
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

        if self.continuous_search:
            if self.ui:
                self.ui.queue_task(lambda msg=status_message: self.ui.update_status(f"{msg} (계속 탐색 중)"))
            if self.research_delay > 0:
                time.sleep(self.research_delay)
        else:
            self.stop_search(message=status_message)

    def _perform_space_complete_action(self):
        """스페이스 완료 모드에서 스페이스바 입력 시 수행할 동작"""
        if not self.is_searching: return
        
        # 별도 스레드에서 클릭 동작 수행 (키보드 리스너 블로킹 방지)
        threading.Thread(target=self._space_complete_worker, daemon=True).start()

    def _space_complete_worker(self):
        if not self.complete_coord or self.complete_coord == (0, 0):
            self.ui.queue_task(lambda: self.ui.update_status("오류: 완료 좌표가 설정되지 않았습니다."))
            return

        x, y = self.complete_coord
        # 오차 적용
        if self.color_area_tolerance > 0:
            x += random.randint(-self.color_area_tolerance, self.color_area_tolerance)
            y += random.randint(-self.color_area_tolerance, self.color_area_tolerance)
        
        self.color_finder.click_action(x, y)
        
        if self.ui:
            self.ui.queue_task(lambda: self.ui.play_sound(3))

        if self.continuous_search:
            if self.ui:
                self.ui.queue_task(lambda: self.ui.update_status(f"스페이스바 입력으로 완료 ({x}, {y}) (계속 탐색 중)"))
            if self.research_delay > 0:
                time.sleep(self.research_delay)
        else:
            self.stop_search(message=f"스페이스바 입력으로 완료 ({x}, {y})")

    def on_key_press(self, key):
        """전역 키 입력을 감지하여 단축키 조합을 처리합니다."""
        # 스페이스 완료 모드 동작 (검색 중일 때 스페이스바로 완료 표시)
        if key == keyboard.Key.space:
            if self.is_searching and self.use_space_complete:
                self._perform_space_complete_action()
            return

        # ↑ + ↑ 활성화 (검색 시작/중지 토글)
        if key == keyboard.Key.up:
            if self.up_press_timer:
                self.up_press_timer.cancel()
            self.up_press_count += 1

            if self.up_press_count >= 2:
                self._reset_up_count()
                # UI 버튼이나 Shift 연타와 동일하게 검색 상태를 토글합니다.
                self.toggle_search()
            else:
                self.up_press_timer = threading.Timer(0.4, self._reset_up_count)
                self.up_press_timer.start()
            return

        # Shift + Shift + Number 조합 처리
        if self.direction_change_pending:
            direction_map = {
                'q': SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT, 'ㅂ': SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT,
                'w': SearchDirection.TOP_RIGHT_TO_BOTTOM_LEFT, 'ㅈ': SearchDirection.TOP_RIGHT_TO_BOTTOM_LEFT,
                'a': SearchDirection.BOTTOM_LEFT_TO_TOP_RIGHT, 'ㅁ': SearchDirection.BOTTOM_LEFT_TO_TOP_RIGHT,
                's': SearchDirection.BOTTOM_RIGHT_TO_TOP_LEFT, 'ㄴ': SearchDirection.BOTTOM_RIGHT_TO_TOP_LEFT,
                'e': SearchDirection.TOP_TO_BOTTOM_LEFT_TO_RIGHT, 'ㄷ': SearchDirection.TOP_TO_BOTTOM_LEFT_TO_RIGHT,
                'r': SearchDirection.TOP_TO_BOTTOM_RIGHT_TO_LEFT, 'ㄱ': SearchDirection.TOP_TO_BOTTOM_RIGHT_TO_LEFT,
                'd': SearchDirection.BOTTOM_TO_TOP_LEFT_TO_RIGHT, 'ㅇ': SearchDirection.BOTTOM_TO_TOP_LEFT_TO_RIGHT,
                'f': SearchDirection.BOTTOM_TO_TOP_RIGHT_TO_LEFT, 'ㄹ': SearchDirection.BOTTOM_TO_TOP_RIGHT_TO_LEFT,
                'z': SearchDirection.CENTER_TOP_TO_BOTTOM, 'ㅋ': SearchDirection.CENTER_TOP_TO_BOTTOM,
                'x': SearchDirection.CENTER_BOTTOM_TO_TOP, 'ㅌ': SearchDirection.CENTER_BOTTOM_TO_TOP,
                'c': SearchDirection.CENTER_LEFT_TO_RIGHT, 'ㅊ': SearchDirection.CENTER_LEFT_TO_RIGHT,
                'v': SearchDirection.CENTER_RIGHT_TO_LEFT, 'ㅍ': SearchDirection.CENTER_RIGHT_TO_LEFT,
                'g': SearchDirection.CENTER_TO_CENTER, 'ㅎ': SearchDirection.CENTER_TO_CENTER,
            }

            # key.char가 존재하는지 확인 (특수키가 아닐 경우)
            if hasattr(key, 'char') and key.char in direction_map:
                # 기본 탐색 영역 목록의 첫 번째 영역 방향을 변경합니다.
                first_id = self.initial_area_order[0]
                new_direction = direction_map[key.char]
                self.initial_areas[first_id]['direction'] = new_direction
                # UI에도 변경된 방향을 즉시 반영합니다.
                if self.ui:
                    self.ui.initial_area_vars[first_id]['direction_var'].set(self.ui.SEARCH_DIRECTION_MAP[new_direction])
                print(f"탐색 방향이 {new_direction.value}로 변경되었습니다.")
            
            # 숫자키가 눌렸든 아니든, 방향 변경 상태를 해제하고 검색을 시작합니다.
            self.direction_change_pending = False
            self.start_search()
            return # 추가적인 Shift 처리 방지

        # Shift 키 연속 누름 감지
        if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            if self.shift_press_timer:
                self.shift_press_timer.cancel()

            self.shift_press_count += 1

            if self.shift_press_count >= 2:
                # 두 번 눌림 감지. 바로 토글하지 않고, 숫자 입력을 기다립니다.
                self.shift_press_count = 0
                self.direction_change_pending = True
                # 0.4초 안에 숫자키가 안 눌리면, 방향 변경 없이 그냥 토글합니다.
                self.shift_press_timer = threading.Timer(0.4, self._execute_toggle_without_direction_change)
                self.shift_press_timer.start()
            else:
                # 첫 번째 눌림, 0.4초 후 카운트 리셋 타이머 시작
                self.shift_press_timer = threading.Timer(0.4, self._reset_shift_count)
                self.shift_press_timer.start()
        
        # ESC 키로 종료
        if key == keyboard.Key.esc:
            if self.is_searching:
                self.stop_search()

    def _execute_toggle_without_direction_change(self):
        """숫자 입력 없이 Shift+Shift만 눌렸을 때 검색을 토글합니다."""
        if self.direction_change_pending:
            self.direction_change_pending = False
            self.toggle_search() # 일반 토글은 apply_settings를 실행

    def _reset_shift_count(self):
        """시간이 초과되면 Shift 키 누름 횟수를 초기화합니다."""
        self.shift_press_count = 0
        self.shift_press_timer = None

    def _reset_up_count(self):
        self.up_press_count = 0
        self.up_press_timer = None

    def _check_operation_status(self) -> bool:
        """탐색 화면이 정상인지 확인합니다. 정상이 아니면 False를 반환하고 검색을 중지합니다."""
        # '탐색 화면 정상 여부 확인(use_operation_check)' 옵션 자체가 꺼져있으면 체크를 건너뜁니다.
        # (구역 탐색/기본 탐색 여부와 무관하게 사용할 수 있습니다.)
        if not self.is_searching or not self.use_operation_check:
            return True
            
        x, y = self.op_check_coord
        max_retries = self.op_check_max_retries
        retry_delay = self.op_check_retry_interval

        for i in range(max_retries):
            # 1x1 영역을 탐색하여 색상이 일치하는지 확인 (Retina 스케일링이 적용된 ColorFinder 로직 재사용)
            found = self.color_finder.find_color_in_area(
                (x, y, x + 1, y + 1), 
                self.op_check_color, 
                self.color_tolerance, 
                SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT
            )
            
            if found is not None:
                return True
            
            # 콘솔 로그 출력
            print(f"--- [화면 확인 실패] ({i+1}/{max_retries}) {retry_delay}초 후 재시도... ---")

            # 마지막 시도가 아니라면 잠깐 대기 후 재시도
            if i < max_retries - 1:
                if self.ui:
                    retry_msg = f"화면 확인 실패... 재시도 ({i+1}/{max_retries})"
                    self.ui.queue_task(lambda msg=retry_msg: self.ui.update_status(msg))
                time.sleep(retry_delay)
                if not self.is_searching: return False
        
        # 모든 재시도 실패 시 중지
        self.stop_search(f"화면 확인 최종 실패: 좌표 ({x}, {y}) 색상 불일치 ({max_retries}회 시도)", play_sound=False)
        if self.ui:
            self.ui.queue_task(lambda: self.ui.play_sound(5))
        return False

    def _jitter_duration(self, base_seconds: float) -> float:
        """
        설정된 시간 오차(초)를 적용해 약간 무작위화된 시간을 반환합니다.
        오차가 기준 시간보다 크면(예: 탐색(초)=5, 시간 오차(초)=5보다 더 큰 경우) 0 아래로
        잘리면서 평균이 기준값보다 커지고, 짧은 시간일수록 오차에 완전히 뒤덮여 설정값이
        거의 반영되지 않는 것처럼 보이는 문제가 있어, 오차 범위를 기준 시간 이하로 제한합니다.
        """
        tolerance = min(self.search_time_tolerance_sec, base_seconds)
        offset = random.uniform(-tolerance, tolerance)
        return max(0, base_seconds + offset)

    def _search_worker(self, search_plan: list):
        """(스레드 워커) 전달받은 검색 계획(search_plan)을 순차적으로 실행합니다."""
        if self.use_sequence:
            # [구역 사용 ON]: 총 탐색 시간 동안 (탐색 -> 대기) 사이클 반복

            # 오차를 적용한 실제 총 탐색 시간 계산
            actual_total_duration = self._jitter_duration(self.total_duration_sec)

            main_start_time = time.time()
            while self.is_searching and (time.time() - main_start_time) < actual_total_duration:
                # --- 탐색 사이클 ---
                # 남은 총 탐색 시간과 한 사이클의 탐색 시간 중 더 작은 값을 이번 사이클의 duration으로 설정합니다.
                actual_active_search_duration = self._jitter_duration(self.active_search_duration_sec)

                remaining_total_time = actual_total_duration - (time.time() - main_start_time)
                current_cycle_duration = min(actual_active_search_duration, remaining_total_time)

                cycle_start_time = time.time()
                self._perform_search_cycle(search_plan, cycle_start_time, main_start_time, current_cycle_duration, actual_active_search_duration, actual_total_duration)
                
                # 탐색 중 사용자가 중지하면 루프 탈출
                if not self.is_searching: break

                # --- 대기 사이클 ---
                if self.wait_duration_sec > 0:
                    # 대기 상태 시작 시 창 색상을 'waiting'으로 변경
                    self.ui.queue_task(lambda: self.ui.update_window_bg('waiting'))

                    actual_wait_duration = self._jitter_duration(self.wait_duration_sec)

                    wait_end_time = time.time() + actual_wait_duration
                    while self.is_searching and time.time() < wait_end_time:
                        remaining_wait = int(wait_end_time - time.time())
                        total_elapsed_time = int(time.time() - main_start_time)
                        status_text = f"대기 중... ({remaining_wait}초 남음) | ({total_elapsed_time}s / {int(actual_total_duration)}s)"
                        self.ui.queue_task(lambda text=status_text: self.ui.update_status(text))
                        time.sleep(1)
                    
                    # 대기 시간이 종료되었고, 아직 검색 중이라면 알람을 울립니다.
                    if self.is_searching:
                        self.ui.queue_task(lambda: self.ui.play_sound(1))
                        # 다음 탐색을 위해 창 색상을 다시 'searching'으로 변경
                        self.ui.queue_task(lambda: self.ui.update_window_bg('searching'))
                
                if not self.is_searching: break

            if self.is_searching:
                # 총 탐색 시간이 종료되었을 때 알람 3회
                self.ui.queue_task(lambda: self.ui.play_sound(3))
                self.stop_search(f"총 탐색 시간({int(actual_total_duration)}s) 도달, 검색 종료.", play_sound=False)
        else:
            # [구역 사용 OFF]: 색상을 찾을 때까지 초기 탐색만 무한 반복
            while self.is_searching:
                self._perform_search_cycle(search_plan, time.time(), time.time(), float('inf'), float('inf'), float('inf'))

    def _find_color_in_areas(self, areas: list, color: tuple, tolerance: int):
        """area 목록을 순서대로 탐색하며 첫 발견 위치를 반환합니다. 못 찾으면 None을 반환합니다."""
        for area_plan in areas:
            found = self.color_finder.find_color_in_area(area_plan['search_area'], color, tolerance, area_plan['search_direction'])
            if found:
                return found
        return None

    def _attempt_zone_click(self, step: dict, final_x: int, final_y: int, start_time: float, duration: float,
                             main_start_time: float, cycle_target_duration: float, total_target_duration: float,
                             attempt_label: str, bound_by_cycle: bool = True, click_before_search: bool = True):
        """
        구역의 클릭 좌표를 (필요하면) 클릭한 뒤 해당 구역의 영역들에서 색상을 탐색합니다.
        반환값: (status, found_pos)
          - status='stop': 화면 확인 실패 등으로 즉시 검색을 중단해야 함 (호출자는 False를 반환해야 함)
          - status='break': 중지/시간 초과로 이번 구역 순환을 그만해야 함 (호출자는 루프를 빠져나가면 됨)
          - status='ok': 정상적으로 시도했음. found_pos는 발견 위치 또는 None

        bound_by_cycle=True(기본, 일반 시도용): 이번 탐색 사이클(탐색(초)) 예산 안에서만 진행합니다.
        bound_by_cycle=False(발견 후 재탐색용): 사이클 예산이 아니라 총 탐색(초) 예산까지 진행합니다.
        색상을 발견해 즉시클릭→재탐색을 반복하는 도중에 '탐색(초)' 타이머가 끝났다는 이유만으로
        클릭 시퀀스가 중간에 끊기면 안 되기 때문입니다.

        click_before_search=True(기본, 일반 시도용): 구역 클릭 좌표를 클릭한 뒤 탐색합니다.
        click_before_search=False(발견 후 재탐색용): 구역 버튼을 다시 누르지 않고, 발견 시 이미
        클릭(색상 위치 클릭 + 완료 클릭)한 상태 그대로 곧바로 다시 탐색만 합니다.
        """
        if bound_by_cycle:
            time_up = (time.time() - start_time) >= duration
        else:
            time_up = (time.time() - main_start_time) >= total_target_duration

        if not self.is_searching or time_up:
            return 'break', None

        self.tries_count += 1

        if self.area_delay > 0:
            # 기본 딜레이에 +-60ms(0.06초)의 랜덤 오차를 추가합니다.
            random_offset = random.uniform(-0.06, 0.06)
            final_delay = self.area_delay + random_offset
            # 최종 딜레이가 음수가 되지 않도록 max(0, ...) 처리합니다.
            time.sleep(max(0, final_delay))

        if not self.is_searching:
            return 'break', None

        if click_before_search:
            if (final_x, final_y) != (0, 0):
                self.color_finder.click_action(final_x, final_y)
            else:
                # 클릭 좌표가 (0,0)인 경우 경고 메시지 출력
                self.ui.queue_task(lambda: self.ui.update_status(f"경고: 구역 {step.get('area_number', 'N/A')} 클릭 좌표가 (0,0)이므로 건너뜁니다."))
                print(f"경고: 구역 {step.get('area_number', 'N/A')} 클릭 좌표가 (0,0)이므로 건너뜁니다.")

            time.sleep(0.1)
        elapsed_time = int(time.time() - start_time)
        if duration == float('inf'):
            time_info = f"경과 시간 ({elapsed_time}s)"
        else:
            total_elapsed_time = int(time.time() - main_start_time)
            time_info = f"({elapsed_time}s / {int(cycle_target_duration)}s) ({total_elapsed_time}s / {int(total_target_duration)}s)"
        search_status_text = f"재탐색: 구역{step['area_number']} ({attempt_label}) | {time_info}"
        self.ui.queue_task(lambda text=search_status_text: self.ui.update_status(text))

        if not self._check_operation_status():
            return 'stop', None

        # 구역 내 영역들을 순서대로 탐색합니다. 앞 영역에서 못 찾으면 다음 영역으로 넘어갑니다.
        found_pos = self._find_color_in_areas(step['sub_areas'], step['search_color'], self.color_tolerance)
        return 'ok', found_pos

    def _perform_search_cycle(self, search_plan: list, start_time: float, main_start_time: float, duration: float, cycle_target_duration: float, total_target_duration: float):
        """주어진 시간(duration) 동안 탐색 로직을 수행합니다."""
        if self.use_sequence:
            # [구역 사용 ON]: 초기 탐색 후, 시도 횟수만큼 재시도 순환
            initial_step = search_plan[0]

            # '기본 탐색 사용'이 체크된 경우에만 초기 탐색을 수행합니다.
            if self.use_initial_search:
                # 1. 1순위 색상 탐색 (기본 탐색 영역들을 순서대로, 못 찾으면 다음 영역으로)
                status_text = "초기 탐색 (1순위): 기본 영역에서 탐색 중..."
                self.ui.queue_task(lambda text=status_text: self.ui.update_status(text))
                if not self._check_operation_status(): return False
                found_pos = self._find_color_in_areas(initial_step['initial_areas'], initial_step['search_color'], self.color_tolerance)
                if found_pos:
                    self._handle_found_color(found_pos, "초기 탐색 중 1순위 색상 발견")
                    if not self.continuous_search: return True

                # 2. 2순위 색상 탐색 (조건부)
                if self.is_searching and self.use_secondary_color:
                    status_text = "초기 탐색 (2순위): 기본 영역에서 탐색 중..."
                    self.ui.queue_task(lambda text=status_text: self.ui.update_status(text))
                    if not self._check_operation_status(): return False
                    found_pos_secondary = self._find_color_in_areas(initial_step['initial_areas'], self.secondary_color, self.color_tolerance)
                    if found_pos_secondary:
                        self._handle_found_color(found_pos_secondary, "초기 탐색 중 2순위 색상 발견")
                        if not self.continuous_search: return True

            retry_steps = [step for step in search_plan if step['type'] == 'retry']
            if not retry_steps:
                self.stop_search("활성화된 재시도 구역이 없어 중지합니다.")
                return

            retry_cycle = itertools.cycle(retry_steps)
            while self.is_searching and (time.time() - start_time) < duration:
                step = next(retry_cycle)
                final_x, final_y = step['click_coord']
                if step['offset'] > 0:
                    final_x += random.randint(-step['offset'], step['offset'])
                    final_y += random.randint(-step['offset'], step['offset'])

                for i in range(step['num_retries']):
                    if not self.is_searching or (time.time() - start_time) >= duration: break

                    status, found_pos = self._attempt_zone_click(
                        step, final_x, final_y, start_time, duration,
                        main_start_time, cycle_target_duration, total_target_duration,
                        f"{i+1}/{step['num_retries']}"
                    )
                    if status == 'stop': return False
                    if status == 'break': break

                    if found_pos:
                        self._handle_found_color(found_pos, f"재시도 중 구역{step['area_number']}에서 색상 발견")
                        if not self.continuous_search: return True

                        # 연속 찾기 ON: 발견 → 클릭했다면, 설정된 횟수와 무관하게 같은 구역을
                        # 계속 재탐색합니다. 구역 버튼은 다시 누르지 않고 탐색만 반복하며,
                        # 더 이상 못 찾으면 그때 다음 구역으로 넘어갑니다.
                        while True:
                            status, found_pos = self._attempt_zone_click(
                                step, final_x, final_y, start_time, duration,
                                main_start_time, cycle_target_duration, total_target_duration,
                                "재탐색", bound_by_cycle=False, click_before_search=False
                            )
                            if status == 'stop': return False
                            if status == 'break' or not found_pos: break

                            self._handle_found_color(found_pos, f"재시도 중 구역{step['area_number']}에서 색상 발견")
                            if not self.continuous_search: return True

            if self.is_searching and duration != float('inf'):
                # 한 탐색 사이클의 최대 시간 도달 시 소리 1번 재생
                self.ui.queue_task(lambda: self.ui.play_sound(1))
            return False
        else:
            # [구역 사용 OFF]: 색상을 찾을 때까지 초기 탐색만 무한 반복
            initial_step = search_plan[0]
            while self.is_searching:
                # 1. 1순위 색상 탐색 (기본 탐색 영역들을 순서대로, 못 찾으면 다음 영역으로)
                status_text = "기본 영역 반복 탐색 (1순위)..."
                self.ui.queue_task(lambda text=status_text: self.ui.update_status(text))
                if not self._check_operation_status(): return False
                found_pos = self._find_color_in_areas(initial_step['initial_areas'], initial_step['search_color'], self.color_tolerance)
                if found_pos:
                    self._handle_found_color(found_pos, "기본 영역에서 1순위 색상 발견")
                    if not self.continuous_search: return True

                # 2. 2순위 색상 탐색 (조건부)
                if self.is_searching and self.use_secondary_color:
                    status_text = "기본 영역 반복 탐색 (2순위)..."
                    self.ui.queue_task(lambda text=status_text: self.ui.update_status(text))
                    if not self._check_operation_status(): return False
                    found_pos_secondary = self._find_color_in_areas(initial_step['initial_areas'], self.secondary_color, self.color_tolerance)
                    if found_pos_secondary:
                        self._handle_found_color(found_pos_secondary, "기본 영역에서 2순위 색상 발견")
                        if not self.continuous_search: return True

                if self.use_search_delay and self.search_delay > 0:
                    time.sleep(self.search_delay)
            return False
