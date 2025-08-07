import threading
import time
import ast
import random
from pynput import mouse, keyboard
from typing import Optional

from .color_finder import ColorFinder, SearchDirection
from .global_hotkey_listener import GlobalHotkeyListener
# 타입 힌팅을 위해 AppUI를 임포트합니다.
from .app_ui import AppUI

class AppController:
    def __init__(self):
        self.ui = None  # UI 인스턴스는 나중에 set_ui를 통해 설정됩니다.
        self.ui: Optional[AppUI] = None  # UI 인스턴스는 나중에 set_ui를 통해 설정됩니다.
        self._initialize_attributes()
        # 핵심 로직 컴포넌트 초기화
        self.color_finder = ColorFinder(sleep_time=self.sleep_time)
        self.mouse_controller = mouse.Controller()
        hotkey_map = {
            'shift+esc': self.start_search,
            keyboard.Key.esc: lambda: self.stop_search()
        }
        self.global_hotkey_listener = GlobalHotkeyListener(hotkey_map)
        self.global_hotkey_listener.start()

    def set_ui(self, ui):
        """UI 인스턴스를 컨트롤러에 연결합니다."""
        self.ui = ui

    def _initialize_attributes(self):
        """애플리케이션의 모든 속성을 초기화합니다."""
        # 설정값
        self.position1 = (75, 193)
        self.position2 = (451, 485)
        self.position3 = (805, 704)
        self.position4 = (813, 396)
        self.position5 = (815, 429)
        self.color = (0, 204, 204)
        self.color4 = self.color
        self.color5 = self.color
        self.color_tolerance = 15
        self.search_direction = SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT
        self.sleep_time = 0.02
        self.fail_click_delay = 0.50
        self.complete_click_delay = 0.02
        self.pos4_click_count = 3
        self.pos5_click_count = 2
        self.click_offset3 = 0
        self.click_offset4 = 5
        self.click_offset5 = 5
        self.max_fail_clicks = 525

        # 내부 상태 변수
        self.area = (0, 0, 0, 0)
        self.area_width = 0
        self.area_height = 0
        self.is_searching = False
        self.search_thread = None
        self.use_fail_sequence = False
        self.use_position5 = False
        self.next_color_after_pos4 = self.color
        self.next_color_after_pos5 = self.color
        self.current_search_color = self.color
        self.fail_sequence_step = 0
        self.fail_sequence_click_count = 0
        self.total_fail_clicks = 0
        self.fail_sequence_target_coord = None

        self._parse_area()

    def apply_settings(self, event=None):
        """UI의 설정값들을 실제 애플리케이션 상태에 적용합니다."""
        try:
            # UI로부터 값 가져오기
            ui_vars = self.ui.get_all_vars()
            self.position1 = ast.literal_eval(ui_vars['coord1_var'].get())
            self.position2 = ast.literal_eval(ui_vars['coord2_var'].get())
            self.position3 = ast.literal_eval(ui_vars['coord3_var'].get())
            self.position4 = ast.literal_eval(ui_vars['coord4_var'].get())
            self.position5 = ast.literal_eval(ui_vars['coord5_var'].get())
            self.color = ast.literal_eval(ui_vars['color_var'].get())
            self.color4 = ast.literal_eval(ui_vars['color4_var'].get())
            self.color5 = ast.literal_eval(ui_vars['color5_var'].get())
            self.color_tolerance = ui_vars['tolerance_var'].get()
            self.fail_click_delay = int(ui_vars['fail_delay_var'].get()) / 1000.0
            self.use_fail_sequence = ui_vars['use_fail_sequence_var'].get()
            self.use_position5 = ui_vars['use_position5_var'].get()
            self.pos4_click_count = int(ui_vars['pos4_clicks_var'].get())
            self.pos5_click_count = int(ui_vars['pos5_clicks_var'].get())
            self.click_offset3 = int(ui_vars['offset3_var'].get())
            self.click_offset4 = int(ui_vars['offset4_var'].get())
            self.click_offset5 = int(ui_vars['offset5_var'].get())
            self.complete_click_delay = int(ui_vars['complete_delay_var'].get()) / 1000.0

            if ui_vars['use_same_color4_var'].get():
                self.next_color_after_pos4 = self.color4
            else:
                self.next_color_after_pos4 = self.color
            if ui_vars['use_same_color5_var'].get():
                self.next_color_after_pos5 = self.color5
            else:
                self.next_color_after_pos5 = self.color

            selected_display_name = ui_vars['direction_var'].get()
            reversed_direction_map = {v: k for k, v in self.ui.SEARCH_DIRECTION_MAP.items()}
            direction_name = reversed_direction_map.get(selected_display_name)
            if direction_name:
                self.search_direction = SearchDirection[direction_name]

            self._parse_area()
            self.ui.update_status("설정이 성공적으로 적용되었습니다.")
            print("--- Settings Applied ---")

        except (ValueError, SyntaxError) as e:
            error_msg = f"설정 적용 오류: 입력값을 확인하세요. ({e})"
            self.ui.update_status(error_msg)
        except Exception as e:
            self.ui.update_status(f"설정 적용 오류: {e}")

    def _parse_area(self):
        """두 좌표를 기반으로 사각 영역을 계산합니다."""
        x1, y1 = self.position1
        x2, y2 = self.position2
        
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)

        self.area = (left, top, right, bottom)
        self.area_width = right - left
        self.area_height = bottom - top

        print(f"영역 좌표: {self.area}")
        print(f"영역 Width: {self.area_width}")
        print(f"영역 Height: {self.area_height}")

    def start_search(self):
        """색상 검색을 시작합니다."""
        # UI가 준비되기 전에 단축키가 눌리는 것을 방지
        if not self.ui:
            return
            
        def start_search_task():
            if self.is_searching:
                return
            self.apply_settings()
            if "오류" in self.ui.get_status():
                return

            self.fail_sequence_target_coord = None
            self.current_search_color = self.color
            self.fail_sequence_step = 0
            self.fail_sequence_click_count = 0
            self.total_fail_clicks = 0
            self.is_searching = True

            self.ui.update_status("색상 검색 중... (ESC로 중지)")
            self.ui.update_button_text("중지 (ESC)")
            self.ui.update_window_bg('searching')
            self.ui.play_sound(1)
            print("--- 색상 검색 ON ---")

            self.search_thread = threading.Thread(target=self._search_worker, daemon=True)
            self.search_thread.start()
        
        self.ui.queue_task(start_search_task)

    def stop_search(self, message="검색이 중지되었습니다.", auto_stopped=False):
        """색상 검색을 중지합니다."""
        # UI가 준비되기 전에 단축키가 눌리는 것을 방지
        if not self.is_searching or not self.ui:
            return
        
        self.is_searching = False

        def stop_search_task():
            self.ui.update_button_text("찾기(Shift+ESC)")
            self.ui.update_status(message)
            self.ui.update_window_bg('default')

            if auto_stopped:
                self.ui.play_sound(3)
            else:
                self.ui.play_sound(2)
            print("--- 색상 검색 OFF ---")
        
        self.ui.queue_task(stop_search_task)

    def toggle_search(self):
        """UI 버튼 클릭 시 검색을 토글합니다."""
        if self.is_searching:
            self.stop_search()
        else:
            self.start_search()

    def _search_worker(self):
        """(스레드 워커) 색상을 주기적으로 검색하고, 찾으면 클릭 후 종료합니다."""
        while self.is_searching:
            abs_x, abs_y = self.color_finder.find_color_in_area(self.area, self.current_search_color, self.color_tolerance, self.search_direction)

            if abs_x is not None and abs_y is not None:
                self.color_finder.click_action(abs_x, abs_y)

                if self.position3 != (0, 0):
                    time.sleep(0.1)
                    comp_x, comp_y = self.position3

                    final_comp_x, final_comp_y = comp_x, comp_y
                    if self.click_offset3 > 0:
                        offset_x = random.randint(-self.click_offset3, self.click_offset3)
                        offset_y = random.randint(-self.click_offset3, self.click_offset3)
                        final_comp_x += offset_x
                        final_comp_y += offset_y
                    self.color_finder.click_action(final_comp_x, final_comp_y, delay=self.complete_click_delay)
                    status_message = f"색상 클릭 후 완료선택({final_comp_x},{final_comp_y}) 클릭"
                else:
                    status_message = f"색상 발견 및 클릭 완료: ({abs_x}, {abs_y})"

                self.is_searching = False
                self.ui.queue_task(lambda: self.ui.play_sound(4))
                self.ui.queue_task(lambda: self.ui.update_status(status_message))
                self.ui.queue_task(lambda: self.ui.update_button_text("찾기(Shift+ESC)"))
                self.ui.queue_task(lambda: self.ui.update_window_bg('default'))

                print("--- 색상 발견, 작업 완료, 검색 종료 ---")
                return

            if self.use_fail_sequence:
                if self.fail_sequence_step == 0:
                    target_coord = self.position4
                    target_offset = self.click_offset4
                    coord_num = 4
                    total_clicks_for_step = self.pos4_click_count
                else:
                    target_coord = self.position5
                    target_offset = self.click_offset5
                    coord_num = 5
                    total_clicks_for_step = self.pos5_click_count

                if self.fail_sequence_click_count == 0:
                    base_x, base_y = target_coord
                    final_x, final_y = base_x, base_y
                    if target_offset > 0:
                        offset_x = random.randint(-target_offset, target_offset)
                        offset_y = random.randint(-target_offset, target_offset)
                        final_x += offset_x
                        final_y += offset_y
                    self.fail_sequence_target_coord = (final_x, final_y)

                should_click = False
                if coord_num == 4:
                    should_click = True
                elif coord_num == 5:
                    should_click = self.use_position5

                if should_click and self.fail_sequence_target_coord and self.fail_sequence_target_coord != (0, 0):
                    fail_x, fail_y = self.fail_sequence_target_coord
                    
                    status_text = f"구역 선택: 구역{coord_num-3} ({self.fail_sequence_click_count + 1}/{total_clicks_for_step}) | 총 {self.total_fail_clicks + 1}/{self.max_fail_clicks}"
                    self.ui.queue_task(lambda text=status_text: self.ui.update_status(text))
                    
                    final_delay = self.fail_click_delay
                    if self.fail_click_delay > 0:
                        random_offset = random.uniform(-0.1, 0.1)
                        final_delay = self.fail_click_delay + random_offset
                    self.color_finder.click_action(fail_x, fail_y, delay=max(0, final_delay))

                    self.total_fail_clicks += 1
                    if self.total_fail_clicks >= self.max_fail_clicks:
                        print(f"--- 최대 실패 클릭 횟수({self.max_fail_clicks})에 도달하여 자동 중단합니다. ---")
                        self.ui.queue_task(lambda: self.stop_search(message="최대 클릭 도달, 자동 중단됨", auto_stopped=True))
                        return

                self.fail_sequence_click_count += 1
                if self.fail_sequence_click_count >= total_clicks_for_step:
                    self.fail_sequence_target_coord = None
                    self.fail_sequence_click_count = 0
                    self.fail_sequence_step = 1 - self.fail_sequence_step

                    if self.fail_sequence_step == 1:
                        self.current_search_color = self.next_color_after_pos4
                        print(f"다음 검색 색상 변경 (구역1 규칙): {self.current_search_color}")
                    else:
                        self.current_search_color = self.next_color_after_pos5
                        print(f"다음 검색 색상 변경 (구역2 규칙): {self.current_search_color}")

            time.sleep(0.1)

    def on_closing(self):
        """창을 닫을 때 리소스를 안전하게 정리합니다."""
        self.is_searching = False
        self.global_hotkey_listener.stop()
