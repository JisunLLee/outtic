import tkinter as tk
from pynput import mouse, keyboard
from PIL import ImageGrab
import time
import threading
from tkinter import messagebox
import re
import signal

class MacroSetupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("테스터")
        # 창 높이를 늘려 새 버튼을 위한 공간 확보
        self.root.geometry("330x500")
        self.root.configure(bg="#2e2e2e")

        # 좌표 표시용 변수
        self.coord1 = tk.StringVar(value="(미지정)")
        self.coord2 = tk.StringVar(value="(미지정)")
        # self.coord3 = tk.StringVar(value="(미지정)")
        self.color_val = tk.StringVar(value="(미지정)")

        self.found_pos= None

        # # UI 위젯 생성
        # self._create_coord_entry(0, "1번 좌표", self.coord1)
        # self._create_coord_entry(1, "2번 좌표", self.coord2)
        # # self._create_coord_entry(2, "3번 좌표 (클릭 대상)", self.coord3)
        # self._create_color_picker_entry(2, "대상 색상", self.color_val)

        # # 영역 확인 버튼
        # tk.Button(self.root, text="영역 확인", command=self.show_area).grid(
        #     row=4, column=0, columnspan=3, pady=10, padx=10, sticky="ew"
        # )

        # # 액션 버튼 프레임 (색상 찾기, 찾은 위치 클릭)f
        # action_frame = tk.Frame(self.root, bg=self.root.cget('bg'))
        # action_frame.grid(row=5, column=0, columnspan=3, pady=(0, 10), padx=10, sticky="ew")
        # action_frame.columnconfigure(0, weight=1)
        # action_frame.columnconfigure(1, weight=1)

        # tk.Button(action_frame, text="색상 대기 & 클릭", command=self.toggle_color_search).grid(
        #     row=0, column=0, sticky="ew", padx=2)
        # tk.Button(action_frame, text="찾은 위치 클릭", command=self.click_found_position).grid(
        #     row=0, column=1, sticky="ew", padx=2)

        # # 상태 메시지
        # self.status = tk.StringVar(value="대기 중...")
        # tk.Label(root, textvariable=self.status, fg="lightblue", bg="#2e2e2e", anchor="w").grid(
        #     row=6, column=0, columnspan=3, sticky="w", padx=10, pady=10
        # )


        # # 영역 표시창을 위한 참조
        # self.area_window = None
        # # 마우스 리스너 참조를 위한 변수
        # self.listener = None
        # # 마지막으로 찾은 색상 위치
        # self.last_found_pos = None
        # # 색상 검색 상태 및 스레드
        # self.is_searching = False
        # self.search_thread = None
        # # 전역 키보드 리스너
        # self.keyboard_listener = None

        # # 잘 눌리는지 확인하는 버튼 1,2,3
        # third_frame = tk.Frame(self.root, bg=self.root.cget('bg'))
        # third_frame.grid(row=12, column=0, columnspan=3, pady=(0, 10), padx=10, sticky="ew")
        # # 각 버튼이 동일한 너비를 갖도록 columnconfigure 설정
        # third_frame.columnconfigure(0, weight=1)
        # third_frame.columnconfigure(1, weight=1)
        # third_frame.columnconfigure(2, weight=1)

        # # command에 lambda를 사용하여 각 버튼에 맞는 인자를 전달합니다.
        # tk.Button(third_frame, text="1", command=lambda: self.on_third_button("1")).grid(
        #     row=0, column=0, sticky="ew", padx=2)
        # tk.Button(third_frame, text="2", command=lambda: self.on_third_button("2")).grid(
        #     row=0, column=1, sticky="ew", padx=2)
        # tk.Button(third_frame, text="3", command=lambda: self.on_third_button("3")).grid(
        #     row=0, column=2, sticky="ew", padx=2)

        # # 창을 닫을 때와 프로세스 종료 신호를 받을 때 리소스를 정리합니다.
        # self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        # signal.signal(signal.SIGTERM, self.signal_handler)

        # # 앱의 활성화 여부와 상관없이 동작하는 전역 키보드 리스너를 시작합니다.
        # self.start_global_hotkey_listener()

    # def _create_coord_entry(self, row, label_text, coord_var):
    #     """좌표 선택을 위한 UI 한 줄을 생성하는 헬퍼 메소드"""
    #     tk.Label(self.root, text=label_text, fg="white", bg="#2e2e2e").grid(
    #         row=row, column=0, padx=10, pady=10, sticky="e"
    #         )
    #     tk.Label(self.root, textvariable=coord_var, width=15, anchor="w", relief="sunken", fg="black", bg="white").grid(
    #         row=row, column=1
    #         )
    #     tk.Button(self.root, text="좌표 따기", command=lambda: self.start_mouse_listener(coord_var)).grid(
    #         row=row, column=2, padx=5
    #         )

    # def _create_color_picker_entry(self, row, label_text, color_var):
    #     """색상 선택을 위한 UI 한 줄을 생성하는 헬퍼 메소드"""
    #     tk.Label(self.root, text=label_text, fg="white", bg="#2e2e2e").grid(
    #         row=row, column=0, padx=10, pady=10, sticky="e"
    #         )
    #     tk.Label(self.root, textvariable=color_var, width=15, anchor="w", relief="sunken", fg="black", bg="white").grid(
    #         row=row, column=1
    #         )
    #     tk.Button(self.root, text="색상 선택", command=self.start_color_picker_listener).grid(
    #         row=row, column=2, padx=5
    #         )

    # def start_mouse_listener(self, coord_var):
    #     # 이미 리스너가 실행 중인 경우, 중복으로 생성되는 것을 방지합니다.
    #     if self.listener and self.listener.is_alive():
    #         self.status.set("오류: 이미 다른 좌표를 선택 중입니다.")
    #         return

    #     self.status.set("마우스 클릭으로 좌표 선택하세요...")

    #     def on_click(x, y, button, pressed):
    #         if pressed:
    #             print(f"Clicked at ({x}, {y})")
    #             # GUI 업데이트는 main thread에서 실행되도록 예약합니다.
    #             # pynput이 소수점 좌표를 반환할 수 있으므로 정수로 변환하여 저장합니다.
    #             self.root.after(0, coord_var.set, f"({int(x)}, {int(y)})")
    #             self.root.after(0, self.status.set, "좌표 저장 완료")
    #             return False  # 리스너를 중지합니다.

    #     # 리스너를 별도 스레드에서 실행하고, 인스턴스 변수에 저장하여 제어할 수 있도록 합니다.
    #     def listener_target():
    #         # 리스너를 생성하고 self.listener에 할당합니다.
    #         self.listener = mouse.Listener(on_click=on_click)
    #         try:
    #             self.listener.run()  # 리스너가 중지될 때까지 여기서 대기합니다.
    #         finally:
    #             # 리스너가 어떤 이유로든 종료될 때 참조를 확실히 제거합니다.
    #             print("--- 좌표 리스너 스레드 종료. ---")
    #             self.listener = None

    #     threading.Thread(target=listener_target, daemon=True).start()

    # def start_color_picker_listener(self):
    #     """마우스 클릭으로 화면의 픽셀 색상을 가져옵니다."""
    #     if self.listener and self.listener.is_alive():
    #         self.status.set("오류: 이미 다른 작업을 선택 중입니다.")
    #         return
    #     self.status.set("마우스 클릭으로 색상을 선택하세요...")

    #     def on_click(x, y, button, pressed):
    #         if pressed:
    #             # 클릭된 위치의 1x1 스크린샷을 찍어 색상 값을 얻습니다.
    #             ix, iy = int(x), int(y)
    #             screenshot = ImageGrab.grab(bbox=(ix, iy, ix + 1, iy + 1))
    #             pixel_color = screenshot.getpixel((0, 0))
    #             # Pillow는 RGBA 값을 반환할 수 있으므로, 처음 3개(RGB) 값만 사용합니다.
    #             color = pixel_color[:3]
    #             self.root.after(0, self.color_val.set, str(color))
    #             self.root.after(0, self.status.set, f"색상 저장 완료: {color}")
    #             return False # 리스너 중지

    #     def listener_target():
    #         self.listener = mouse.Listener(on_click=on_click)
    #         try:
    #             self.listener.run()
    #         finally:
    #             # 리스너가 어떤 이유로든 종료될 때 참조를 확실히 제거합니다.
    #             print("--- 색상 리스너 스레드 종료. ---")
    #             self.listener = None
    #     threading.Thread(target=listener_target, daemon=True).start()

    # def _parse_coord(self, coord_str):
    #     """'(x, y)' 형식의 문자열을 파싱하여 (x, y) 튜플로 반환합니다."""
    #     # eval() 대신 정규표현식을 사용하여 더 안전하게 파싱합니다.
    #     match = re.match(r'\((\d+),\s*(\d+)\)', coord_str)
    #     if match:
    #         return int(match.group(1)), int(match.group(2))
    #     return None

    # def _parse_color(self, color_str):
    #     """'(r, g, b)' 형식의 문자열을 파싱하여 (r, g, b) 튜플로 반환합니다."""
    #     match = re.match(r'\((\d+),\s*(\d+),\s*(\d+)\)', color_str)
    #     if match:
    #         return int(match.group(1)), int(match.group(2)), int(match.group(3))
    #     return None

    # def show_area(self):
    #     """선택된 두 좌표를 기준으로 사각형 영역을 화면에 표시합니다."""
    #     # 이전에 열려 있던 영역 창이 있다면 닫습니다.
    #     if self.area_window:
    #         self.area_window.destroy()

    #     self._parse_area()
    #     width, height, (x1, y1), (x2, y2) = self.found_pos


    #     # 영역을 표시할 새 Toplevel 창 생성
    #     self.area_window = tk.Toplevel(self.root)
    #     self.area_window.overrideredirect(True)  # 창 테두리 제거
    #     self.area_window.geometry(f"{width}x{height}+{x1}+{y1}")
    #     self.area_window.configure(bg="red")  
    #     self.area_window.attributes('-alpha', 0.4)  # 투명도 설정 (0.0 ~ 1.0)
    #     self.area_window.attributes('-topmost', True) # 항상 위에 표시

    #     self.status.set(f"영역 표시: ({x1},{y1}) - ({x2},{y2}) | {width}x{height}")
    #     # 3초 후에 자동으로 창을 닫습니다.
    #     self.area_window.after(3000, self.area_window.destroy)

    # def toggle_color_search(self):
    #     if self.is_searching:
    #         self.is_searching = False
    #         self.status.set("색상 검색 중지 요청")
    #         print("--- 색상 검색 OFF ---")
    #         return
    #     print("--- 색상 검색 ON ---")
    #     # 이미 다른 스레드가 실행 중인 경우 중복 실행 방지
    #     if self.search_thread and self.search_thread.is_alive():
    #         self.status.set("오류: 이미 검색 작업이 실행 중입니다.")
    #         return

    #     self.is_searching = True
    #     self.search_thread = threading.Thread(target=self._wait_and_find_color_worker, daemon=True)
    #     self.search_thread.start()

    # def _wait_and_find_color_worker(self):
    #     """(스레드 워커) 지정된 색상이 나타날 때까지 반복적으로 검색하고, 찾으면 클릭합니다."""
    #     try:
    #         if self.found_pos:
    #             abs_x, abs_y = self.found_pos
    #             # 클릭 위치 보정: 찾은 위치에서 안쪽으로 이동하여 클릭 성공률을 높입니다.
    #             offset_x = 2 # 버튼의 가로 크기에 따라 조정
    #             offset_y = 0 # 버튼의 세로 크기에 따라 조정

    #             final_x = abs_x + offset_x
    #             final_y = abs_y + offset_y
    #             self.last_found_pos = (final_x, final_y)  # 찾은 위치 저장
    #             print(f"색상 발견! 위치: ({final_x}, {final_y})")
    #             self.status.set("색상 발견! 위치: ({final_x}, {final_y})")
            
    #             # 찾은 위치를 바로 클릭합니다.
    #             self.click_found_position()
                
    #         else:
    #             self.last_found_pos = None  # 못 찾았으면 위치 초기화
    #             self.root.after(0, self.status.set, "지정된 영역에서 색상을 찾지 못했습니다.")
        
    #     except Exception as e:
    #         self.last_found_pos = None
    #         print(f"오류 발생: {e}")
    #         self.root.after(0, self.status.set, f"오류 발생: {e}")

    # def _parse_area(self):
    #     pos1 = self._parse_coord(self.coord1.get())
    #     pos2 = self._parse_coord(self.coord2.get())

    #     if not pos1 or not pos2:
    #         self.status.set("오류: 두 좌표를 모두 지정해야 합니다.")
    #         messagebox.showerror("오류", "1번과 2번 좌표를 모두 지정해주세요.")
    #         return

    #     x1, y1 = pos1
    #     x2, y2 = pos2

    #     # 1번 좌표가 2번 좌표의 좌상단에 위치하는지 확인합니다.
    #     if x1 >= x2 or y1 >= y2:
    #         self.status.set("오류: 1번 좌표가 2번 좌표의 좌상단이어야 합니다.")
    #         messagebox.showerror("좌표 오류", "1번 좌표는 2번 좌표의 왼쪽 위에 위치해야 합니다.\n(x1 < x2, y1 < y2)")
    #         return

    #     width = x2 - x1
    #     height = y2 - y1
        
    #     self.found_pos = (width, height, pos1, pos2)
    #     return 


    # def perform_coord3_click(self):
    #     """3번 좌표로 지정된 위치를 클릭합니다."""
    #     coord3_pos = self._parse_coord(self.coord3.get())

    #     if coord3_pos:
    #         x, y = coord3_pos
    #         print(f"색상 발견, 3번 좌표 ({x},{y}) 클릭 실행...")

    #         # 실제 클릭 동작은 UI를 차단하지 않도록 별도 스레드에서 수행합니다.
    #         def click_action():
    #             mouse_controller = mouse.Controller()
    #             mouse_controller.position = (x, y)
    #             time.sleep(0.05)  # ✅ 딜레이 추가: 마우스 이동 후 클릭까지 대기
    #             mouse_controller.click(mouse.Button.left, 1)
    #             print(0, self.status.set, f"클릭 완료: 3번 좌표 ({x}, {y})")

    #         threading.Thread(target=click_action, daemon=True).start()
    #     else:
    #         self.status.set("색상 발견, 그러나 3번 좌표가 지정되지 않아 클릭 실패.")
    #         messagebox.showwarning("알림", "색상은 찾았지만, 클릭할 3번 좌표가 지정되지 않았습니다.")

    # def _perform_click_at(self, x, y):
    #     """(Helper) 지정된 좌표 (x, y)를 클릭합니다. UI 블로킹을 막기 위해 스레드에서 실행합니다."""
    #     def click_action():
    #         mouse_controller = mouse.Controller()
    #         mouse_controller.position = (x, y)
    #         time.sleep(0.05)  # ✅ 딜레이 추가: 마우스 이동 후 클릭까지 대기
    #         mouse_controller.click(mouse.Button.left, 1)
    #         # GUI 업데이트는 메인 스레드에서 실행되도록 예약합니다.
    #         print(f"클릭 완료: ({x}, {y})")

    #     threading.Thread(target=click_action, daemon=True).start()

    # def click_found_position(self):
    #     """저장된 마지막 위치를 마우스로 클릭합니다."""
    #     if self.last_found_pos:
    #         x, y = self.last_found_pos
    #         print(f"저장된 위치 ({x},{y}) 클릭 실행...")
    #         self._perform_click_at(x, y)
    #     else:
    #         self.status.set("오류: 먼저 '색상 찾기'를 실행하여 위치를 찾아주세요.")
    #         messagebox.showwarning("알림", "클릭할 위치가 없습니다.\n먼저 '색상 찾기'를 실행해주세요.")

    # def signal_handler(self, signum, frame):
    #     """프로세스 종료 신호(SIGTERM)를 처리합니다."""
    #     print(f"--- 신호 {signum} 수신, 애플리케이션을 종료합니다. ---")
    #     self.on_closing()

    # def on_closing(self):
    #     """창이 닫힐 때 호출되어 리소스를 안전하게 정리합니다."""
    #     print("--- 애플리케이션 종료 중... ---")
    #     # 활성화된 마우스 리스너가 있다면 중지시킵니다.
    #     if self.keyboard_listener and self.keyboard_listener.is_alive():
    #         print("--- 전역 키보드 리스너를 중지합니다. ---")
    #         self.keyboard_listener.stop()

    #     if self.listener and self.listener.is_alive():
    #         print("--- 활성 마우스 리스너를 중지 시도... ---")
    #         self.listener.stop()
    #         print("--- 활성 마우스 리스너를 중지했습니다. ---")
    #     self.root.destroy()

    # def _on_hotkey_press(self, key):
    #     """전역 단축키가 눌렸을 때 호출됩니다."""
    #     if key == keyboard.Key.f4:
    #         print("[F4]")
    #         self.toggle_color_search()

    # def start_global_hotkey_listener(self):
    #     """시스템 전역의 키보드 입력을 감지하는 리스너를 시작합니다."""
    #     self.keyboard_listener = keyboard.Listener(on_press=self._on_hotkey_press)
    #     self.keyboard_listener.start()
    #     print("--- 전역 단축키 리스너 시작됨. F4를 눌러 색상 찾기 실행. ---")

    # def on_third_button(self, num):
    #     messagebox.showinfo("버튼 클릭", f"{num}번 버튼이 눌렸습니다.")

if __name__ == "__main__":
    root = tk.Tk()
    app = MacroSetupApp(root)
    root.mainloop()
