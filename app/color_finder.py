from enum import Enum
from pynput import mouse
from typing import Optional
from PIL import ImageGrab
import random
import time
import numpy as np

class SearchDirection(Enum):
    """탐색 방향을 정의합니다."""
    # 좌상단 -> 우하단 (가로 우선)
    TOP_LEFT_TO_BOTTOM_RIGHT = "tl_br"
    # 우상단 -> 좌하단 (가로 우선)
    TOP_RIGHT_TO_BOTTOM_LEFT = "tr_bl"
    # 좌하단 -> 우상단 (가로 우선)
    BOTTOM_LEFT_TO_TOP_RIGHT = "bl_tr"
    # 우하단 -> 좌상단 (가로 우선)
    BOTTOM_RIGHT_TO_TOP_LEFT = "br_tl"

class ColorFinder:
    def __init__(self, sleep_time: float = 0.02):
        self.mouse_controller = mouse.Controller()
        self.sleep_time = sleep_time

    def click_action(self, x: int, y: int, delay: Optional[float] = None, offset: int = 0):
        try:
            final_x, final_y = x, y
            if offset > 0:
                offset_x = random.randint(-offset, offset)
                offset_y = random.randint(-offset, offset)
                final_x = x + offset_x
                final_y = y + offset_y

            self.mouse_controller.position = (final_x, final_y)
            # Use provided delay if available, otherwise use the default sleep_time
            sleep_duration = delay if delay is not None else self.sleep_time
            time.sleep(sleep_duration)
            self.mouse_controller.click(mouse.Button.left, 1)
            print(f"클릭 완료: ({final_x}, {final_y}) [원래: ({x},{y}), 오차: {offset}]")
        except Exception as e:
            print(f"An error occurred: {e}")

    def find_color_in_area(self, area: tuple[int, int, int, int], color: tuple[int, int, int], tolerance: int = 10, direction: SearchDirection = SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT):
        x1, y1, x2, y2 = area
        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        color_x, color_y = self._find_color_in_area(screenshot, color, tolerance, direction)
        opt_x = 1.5 # 색상 버튼의 가로 크기에 따라 조정
        opt_y = 2.5 # 색상 버튼의 세로 크기에 따라 조정

        if color_x is not None and color_y is not None:
            # 최종 좌표는 정수로 변환하여 반환
            abs_x = int(x1 + color_x + opt_x)
            abs_y = int(y1 + color_y + opt_y)
            print(f"Color found at ({abs_x}, {abs_y}) with tolerance {tolerance}")
            return abs_x, abs_y
        return None, None

    def _find_color_in_area(self, screenshot, color: tuple[int, int, int], tolerance: int, direction: SearchDirection):
        # 1. Pillow 이미지를 NumPy 배열로 변환하여 픽셀 접근 속도를 높입니다.
        img_array = np.array(screenshot)
        height, width, _ = img_array.shape
        
        r2, g2, b2 = int(color[0]), int(color[1]), int(color[2])

        # 탐색 방향에 따른 범위 설정
        if direction == SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT:
            y_range = range(height)
            x_range = range(width)
        elif direction == SearchDirection.TOP_RIGHT_TO_BOTTOM_LEFT:
            y_range = range(height)
            x_range = range(width - 1, -1, -1)
        elif direction == SearchDirection.BOTTOM_LEFT_TO_TOP_RIGHT:
            y_range = range(height - 1, -1, -1)
            x_range = range(width)
        elif direction == SearchDirection.BOTTOM_RIGHT_TO_TOP_LEFT:
            y_range = range(height - 1, -1, -1)
            x_range = range(width - 1, -1, -1)
        else: # Fallback to default
            y_range = range(height)
            x_range = range(width)

        # 3. NumPy 배열을 순회하며 색상을 찾습니다.
        for y in y_range:
            for x in x_range:
                # getpixel() 대신 배열에서 직접 픽셀 값을 읽습니다.
                r1, g1, b1 = img_array[y, x][:3]

                # 4. 각 채널의 차이가 허용 오차(tolerance) 이내인지 확인합니다.
                if abs(int(r1) - r2) <= tolerance and \
                   abs(int(g1) - g2) <= tolerance and \
                   abs(int(b1) - b2) <= tolerance:
                    return x, y
        return None, None
