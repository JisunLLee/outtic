import tkinter as tk
from PIL import ImageGrab
import time
import threading
from tkinter import messagebox
import re
import signal
from global_hotkey_listener import GlobalHotkeyListener
from color_finder import ColorFinder, SearchDirection

class SampleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("샘플 테스터")

        self.root.geometry("330x500")
        self.root.configure(bg="#2e2e2e")

        self.position1 = (53, 182)
        self.position2 = (713, 647)
        self.color = (0, 204, 204)
        self.x1, self.y1 = self.position1
        self.x2, self.y2 = self.position2
        
        # 색상 유사도 허용 범위 (0~255, 값이 클수록 더 넓은 범위의 색상을 찾음)
        # 예: 10은 매우 유사한 색상, 50은 눈에 띄게 다른 색상도 포함할 수 있음
        self.color_tolerance = 15
        # 탐색 방향 설정
        self.search_direction = SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT
        self.sleep_time = 0.02

        # 좌표 표시용 변수
        self.coord1 = tk.StringVar(value="{position1}")
        self.coord2 = tk.StringVar(value="{position2}")

        # UI 위젯 생성
        self._create_coord_entry(0, "1번 좌표", self.coord1)
        self._create_coord_entry(1, "2번 좌표", self.coord2)
        # self._create_color_picker_entry(2, "대상 색상", self.color_val)

        self._parse_area()
        self.find_button = tk.Button(root, text="찾기", command=self.click_found_position)
        # self.find_button.pack()

        self.color_finder = ColorFinder(sleep_time=self.sleep_time)
        # 앱의 활성화 여부와 상관없이 동작하는 전역 키보드 리스너를 시작합니다.
        self.global_hotkey_listener = GlobalHotkeyListener(self.click_found_position)
        self.global_hotkey_listener.start()


    def _create_coord_entry(self, row, label_text, coord_var):
        """좌표 선택을 위한 UI 한 줄을 생성하는 헬퍼 메소드"""
        tk.Label(self.root, text=label_text, fg="white", bg="#2e2e2e").grid(
            row=row, column=0, padx=10, pady=10, sticky="e"
            )
        tk.Label(self.root, textvariable=coord_var, width=15, anchor="w", relief="sunken", fg="black", bg="white").grid(
            row=row, column=1
            )
        tk.Button(self.root, text="좌표 따기", command= self.location_onClick).grid(
            row=row, column=2, padx=5
            )

    def location_onClick(self):
        print("click")

    def _parse_area(self):
        width = self.x2 - self.x1
        height = self.y2 - self.y1
        self.area = (self.x1, self.y1, self.x2, self.y2)
        self.area_width = width
        self.area_height = height
        print(f"영역 좌표: {self.area}")
        print(f"영역 Width: {width}")
        print(f"영역 Height: {height}")

    def click_found_position(self):
        abs_x, abs_y = self.color_finder.find_color_in_area(self.area, self.color, self.color_tolerance, self.search_direction)

        if abs_x is not None and abs_y is not None:
            # 지정된 좌표 (abs_x, abs_y)를 클릭합니다.
            self.color_finder.click_action(abs_x, abs_y)
        else:
            print("Color not found in the specified area.")

if __name__ == "__main__":
    root = tk.Tk()
    sampleApp = SampleApp(root)
    root.mainloop()