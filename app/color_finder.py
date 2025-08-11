from pynput import mouse
from PIL import ImageGrab
import time
import numpy as np

class ColorFinder:
    """화면에서 특정 색상을 찾고 관련 동작을 수행하는 클래스"""
    def __init__(self):
        self.mouse_controller = mouse.Controller()

    def find_color_in_area(self, area: tuple, color: tuple, tolerance: int) -> tuple[int, int] | None:
        """
        지정된 영역(area)에서 주어진 색상(color)을 허용 오차(tolerance) 내에서 찾습니다.
        NumPy를 사용하여 성능을 최적화했습니다.
        """
        x1, y1, x2, y2 = area
        if not (x2 > x1 and y2 > y1):
            return None

        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        img_array = np.array(screenshot)
        
        # NumPy의 브로드캐스팅을 사용하여 모든 픽셀에 대해 색상 차이를 한 번에 계산
        target_color = np.array(color)
        distances = np.sqrt(np.sum((img_array[:, :, :3] - target_color)**2, axis=2))
        
        # 허용 오차 내에 있는 픽셀의 위치를 찾음
        match_coords = np.where(distances <= tolerance)
        
        if len(match_coords[0]) > 0:
            # 첫 번째로 찾은 픽셀의 상대 좌표
            rel_y, rel_x = match_coords[0][0], match_coords[1][0]
            # 절대 좌표로 변환하여 반환
            return x1 + rel_x, y1 + rel_y
            
        return None

    def click_action(self, x: int, y: int):
        """지정된 좌표로 마우스를 이동하고 클릭합니다."""
        self.mouse_controller.position = (x, y)
        time.sleep(0.05) # 마우스 이동 후 안정화를 위한 짧은 대기
        self.mouse_controller.click(mouse.Button.left, 1)