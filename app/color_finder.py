from enum import Enum
from pynput import mouse
from PIL import ImageGrab
import time
import numpy as np

class SearchDirection(Enum):
    """탐색 방향을 정의합니다."""
    TOP_LEFT_TO_BOTTOM_RIGHT = "→↓"
    TOP_RIGHT_TO_BOTTOM_LEFT = "←↓"
    BOTTOM_LEFT_TO_TOP_RIGHT = "→↑"
    BOTTOM_RIGHT_TO_TOP_LEFT = "←↑"

class ColorFinder:
    """화면에서 특정 색상을 찾고 관련 동작을 수행하는 클래스"""
    def __init__(self):
        self.mouse_controller = mouse.Controller()

    def find_color_in_area(self, area: tuple, color: tuple, tolerance: int, direction: SearchDirection) -> tuple[int, int] | None:
        """
        지정된 영역(area)에서 주어진 색상(color)을 허용 오차(tolerance) 내에서 찾습니다.
        지정된 방향으로 픽셀을 순회합니다.
        """
        x1, y1, x2, y2 = area
        if not (x2 > x1 and y2 > y1):
            return None

        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        img_array = np.array(screenshot)
        height, width, _ = img_array.shape
        
        # 성능을 위해 제곱된 허용 오차를 사용합니다.
        tolerance_sq = tolerance**2
        r2, g2, b2 = color

        # 탐색 방향에 따른 범위 설정
        if direction == SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT:
            y_range, x_range = range(height), range(width)
        elif direction == SearchDirection.TOP_RIGHT_TO_BOTTOM_LEFT:
            y_range, x_range = range(height), range(width - 1, -1, -1)
        elif direction == SearchDirection.BOTTOM_LEFT_TO_TOP_RIGHT:
            y_range, x_range = range(height - 1, -1, -1), range(width)
        elif direction == SearchDirection.BOTTOM_RIGHT_TO_TOP_LEFT:
            y_range, x_range = range(height - 1, -1, -1), range(width - 1, -1, -1)
        else: # 기본값
            y_range, x_range = range(height), range(width)
        
        # 지정된 순서로 픽셀을 순회합니다.
        for y in y_range:
            for x in x_range:
                r1, g1, b1 = img_array[y, x][:3]
                # 제곱 거리를 사용하여 색상 유사도를 계산합니다.
                dist_sq = (int(r1) - r2)**2 + (int(g1) - g2)**2 + (int(b1) - b2)**2
                
                if dist_sq <= tolerance_sq:
                    # 첫 번째로 찾은 픽셀의 절대 좌표를 반환합니다.
                    return x1 + x, y1 + y

        return None

    def click_action(self, x: int, y: int):
        """지정된 좌표로 마우스를 이동하고 클릭합니다."""
        self.mouse_controller.position = (x, y)
        time.sleep(0.05) # 마우스 이동 후 안정화를 위한 짧은 대기
        self.mouse_controller.click(mouse.Button.left, 1)