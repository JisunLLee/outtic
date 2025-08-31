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

    def _is_color_match(self, c1_rgb: tuple, c2_rgb: tuple, tolerance_sq: int) -> bool:
        """두 색상이 허용 오차 내에 있는지 확인합니다."""
        r1, g1, b1 = c1_rgb
        r2, g2, b2 = c2_rgb
        dist_sq = (int(r1) - r2)**2 + (int(g1) - g2)**2 + (int(b1) - b2)**2
        return dist_sq <= tolerance_sq

    def _find_blob_center(self, img_array: np.ndarray, start_x: int, start_y: int, color: tuple, tolerance_sq: int) -> tuple[int, int]:
        """
        발견된 픽셀을 시작으로 상하좌우로 색상 영역을 스캔하여
        해당 영역(blob)의 중심 좌표를 찾습니다.
        """
        height, width, _ = img_array.shape
        
        # 1. 가로 경계 찾기 (x-axis)
        x_min, x_max = start_x, start_x
        # 시작점에서 왼쪽으로 스캔
        for x in range(start_x - 1, -1, -1):
            if self._is_color_match(img_array[start_y, x][:3], color, tolerance_sq):
                x_min = x
            else:
                break
        # 시작점에서 오른쪽으로 스캔
        for x in range(start_x + 1, width):
            if self._is_color_match(img_array[start_y, x][:3], color, tolerance_sq):
                x_max = x
            else:
                break
        
        center_x = (x_min + x_max) // 2

        # 2. 세로 경계 찾기 (y-axis at a horizontal center)
        y_min, y_max = start_y, start_y
        # 중심 x좌표에서 위쪽으로 스캔
        for y in range(start_y - 1, -1, -1):
            if self._is_color_match(img_array[y, center_x][:3], color, tolerance_sq):
                y_min = y
            else:
                break
        # 중심 x좌표에서 아래쪽으로 스캔
        for y in range(start_y + 1, height):
            if self._is_color_match(img_array[y, center_x][:3], color, tolerance_sq):
                y_max = y
            else:
                break
        
        center_y = (y_min + y_max) // 2
        
        return center_x, center_y

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
                pixel_color = img_array[y, x][:3]
                if self._is_color_match(pixel_color, color, tolerance_sq):
                    # 색상 발견! 이제 해당 색상 영역의 중심을 찾습니다.
                    center_x_rel, center_y_rel = self._find_blob_center(img_array, x, y, color, tolerance_sq)
                    # 중심점의 절대 좌표를 반환합니다.
                    return x1 + center_x_rel, y1 + center_y_rel

        return None

    def click_action(self, x: int, y: int):
        """지정된 좌표로 마우스를 이동하고 클릭합니다."""
        self.mouse_controller.position = (x, y)
        time.sleep(0.05) # 마우스 이동 후 안정화를 위한 짧은 대기
        self.mouse_controller.click(mouse.Button.left, 1)