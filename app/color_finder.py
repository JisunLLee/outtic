from enum import Enum
from pynput import mouse
from PIL import ImageGrab
import time
import numpy as np
import platform

class SearchDirection(Enum):
    """탐색 방향을 정의합니다."""
    TOP_LEFT_TO_BOTTOM_RIGHT = "→↓"
    TOP_RIGHT_TO_BOTTOM_LEFT = "←↓"
    BOTTOM_LEFT_TO_TOP_RIGHT = "→↑"
    BOTTOM_RIGHT_TO_TOP_LEFT = "←↑"
    TOP_TO_BOTTOM_LEFT_TO_RIGHT = "↓→"
    TOP_TO_BOTTOM_RIGHT_TO_LEFT = "↓←"
    BOTTOM_TO_TOP_LEFT_TO_RIGHT = "↑→"
    BOTTOM_TO_TOP_RIGHT_TO_LEFT = "↑←"
    CENTER_TOP_TO_BOTTOM = "↓↔"
    CENTER_BOTTOM_TO_TOP = "↑↔"
    CENTER_LEFT_TO_RIGHT = "→↕"
    CENTER_RIGHT_TO_LEFT = "←↕"
    CENTER_TO_CENTER = "☉"

class ColorFinder:
    """화면에서 특정 색상을 찾고 관련 동작을 수행하는 클래스"""
    def __init__(self):
        self.mouse_controller = mouse.Controller()
        self.is_mac = platform.system() == "Darwin"

    def _is_color_match(self, c1_rgb: tuple, c2_rgb: tuple, tolerance_sq: int) -> bool:
        """두 색상이 허용 오차 내에 있는지 확인합니다."""
        r1, g1, b1 = c1_rgb
        r2, g2, b2 = c2_rgb
        dist_sq = (int(r1) - r2)**2 + (int(g1) - g2)**2 + (int(b1) - b2)**2
        return dist_sq <= tolerance_sq

    def _find_blob_center(self, img_array: np.ndarray, start_x: int, start_y: int, color: tuple, tolerance_sq: int) -> tuple[int, int, int, int, int, int, int]:
        """
        발견된 픽셀에서 인접한(4방향) 같은 색상 영역 전체를 탐색해, 그 픽셀 덩어리의
        실제 바운딩 박스 중심을 반환합니다. 완전한 원형처럼 내부에 하이라이트/그림자로
        인한 색상 불연속이 있는 도형에서도, 한 줄/한 열만 스캔하는 방식과 달리 정확한
        중심을 찾을 수 있습니다.

        (center_x, center_y, pixel_count, x_min, x_max, y_min, y_max)를 반환합니다.
        호출부에서 pixel_count가 너무 작으면(안티앨리어싱으로 인한 고립된 잡음 픽셀)
        이 결과를 버리고 탐색을 계속할 수 있습니다.
        """
        height, width, _ = img_array.shape
        MAX_PIXELS = 20000

        visited = np.zeros((height, width), dtype=bool)
        visited[start_y, start_x] = True
        stack = [(start_x, start_y)]
        x_min = x_max = start_x
        y_min = y_max = start_y
        visited_count = 1

        while stack:
            x, y = stack.pop()
            if x < x_min: x_min = x
            elif x > x_max: x_max = x
            if y < y_min: y_min = y
            elif y > y_max: y_max = y

            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < width and 0 <= ny < height and not visited[ny, nx]:
                    if self._is_color_match(img_array[ny, nx][:3], color, tolerance_sq):
                        visited[ny, nx] = True
                        visited_count += 1
                        if visited_count > MAX_PIXELS:
                            stack.clear()
                            break
                        stack.append((nx, ny))

        return (x_min + x_max) // 2, (y_min + y_max) // 2, visited_count, x_min, x_max, y_min, y_max

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

        # macOS Retina 디스플레이 대응: 물리적 픽셀과 논리적 좌표의 비율 계산
        scale_x = width / (x2 - x1) if (x2 - x1) != 0 else 1
        scale_y = height / (y2 - y1) if (y2 - y1) != 0 else 1

        # 성능을 위해 제곱된 허용 오차를 사용합니다.
        tolerance_sq = tolerance**2

        # 안티앨리어싱 등으로 생기는 고립된 잡음 픽셀(예: 버튼 위 작은 하이라이트 잔상)이
        # 실제 버튼보다 먼저 발견되어 잘못 클릭되는 것을 막기 위한 최소 크기 기준입니다.
        # 이보다 작은 덩어리는 무시하고 탐색을 계속합니다.
        # 단, "화면 정상 여부 확인"처럼 1x1 영역만 캡처하는 호출은 애초에 3픽셀을 채울 수
        # 없으므로, 캡처된 이미지 전체 픽셀 수를 넘지 않도록 기준을 낮춥니다.
        MIN_BLOB_PIXELS = min(3, width * height)
        noise_mask = np.zeros((height, width), dtype=bool)

        def check_and_resolve(px, py):
            """(px,py)가 색상에 매치되면 덩어리를 찾아, 잡음이면 None(계속 탐색),
            실제 버튼이면 (final_x, final_y)를 반환합니다."""
            if noise_mask[py, px] or not self._is_color_match(img_array[py, px][:3], color, tolerance_sq):
                return False, None
            center_x_rel, center_y_rel, pixel_count, bx_min, bx_max, by_min, by_max = \
                self._find_blob_center(img_array, px, py, color, tolerance_sq)
            if pixel_count < MIN_BLOB_PIXELS:
                print(f"[DEBUG-NOISE] entry=({px},{py}) bbox=(x:{bx_min}-{bx_max},y:{by_min}-{by_max}) "
                      f"pixel_count={pixel_count} < {MIN_BLOB_PIXELS} -> 무시하고 계속 탐색")
                noise_mask[by_min:by_max + 1, bx_min:bx_max + 1] = True
                return False, None
            final_x, final_y = round(x1 + (center_x_rel / scale_x)), round(y1 + (center_y_rel / scale_y))
            print(f"[DEBUG-CLICK] entry=({px},{py}) bbox=(x:{bx_min}-{bx_max},y:{by_min}-{by_max}) "
                  f"pixel_count={pixel_count} final=({final_x},{final_y})")
            return True, (final_x, final_y)

        # 가로 우선 탐색 (기존 방식)
        if direction in [SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT, SearchDirection.TOP_RIGHT_TO_BOTTOM_LEFT, SearchDirection.BOTTOM_LEFT_TO_TOP_RIGHT, SearchDirection.BOTTOM_RIGHT_TO_TOP_LEFT]:
            if direction == SearchDirection.TOP_LEFT_TO_BOTTOM_RIGHT:
                y_range, x_range = range(height), range(width)
            elif direction == SearchDirection.TOP_RIGHT_TO_BOTTOM_LEFT:
                y_range, x_range = range(height), range(width - 1, -1, -1)
            elif direction == SearchDirection.BOTTOM_LEFT_TO_TOP_RIGHT:
                y_range, x_range = range(height - 1, -1, -1), range(width)
            else: # BOTTOM_RIGHT_TO_TOP_LEFT
                y_range, x_range = range(height - 1, -1, -1), range(width - 1, -1, -1)

            for y in y_range:
                for x in x_range:
                    found, result = check_and_resolve(x, y)
                    if found:
                        return result
        elif direction in [SearchDirection.TOP_TO_BOTTOM_LEFT_TO_RIGHT, SearchDirection.TOP_TO_BOTTOM_RIGHT_TO_LEFT, SearchDirection.BOTTOM_TO_TOP_LEFT_TO_RIGHT, SearchDirection.BOTTOM_TO_TOP_RIGHT_TO_LEFT]:
            if direction == SearchDirection.TOP_TO_BOTTOM_LEFT_TO_RIGHT: x_range, y_range = range(width), range(height)
            elif direction == SearchDirection.TOP_TO_BOTTOM_RIGHT_TO_LEFT: x_range, y_range = range(width - 1, -1, -1), range(height)
            elif direction == SearchDirection.BOTTOM_TO_TOP_LEFT_TO_RIGHT: x_range, y_range = range(width), range(height - 1, -1, -1)
            else: x_range, y_range = range(width - 1, -1, -1), range(height - 1, -1, -1)
            for x in x_range:
                for y in y_range:
                    found, result = check_and_resolve(x, y)
                    if found:
                        return result
        # 중앙 우선 탐색 (새로 추가)
        elif direction in [SearchDirection.CENTER_TOP_TO_BOTTOM, SearchDirection.CENTER_BOTTOM_TO_TOP]:
            y_range = range(height) if direction == SearchDirection.CENTER_TOP_TO_BOTTOM else range(height - 1, -1, -1)
            center_x = width // 2
            for y in y_range:
                # 중앙에서 시작하여 좌우로 확장
                for offset in range(max(center_x, width - center_x)):
                    # 중앙 -> 좌
                    x_left = center_x - offset
                    if 0 <= x_left < width:
                        found, result = check_and_resolve(x_left, y)
                        if found:
                            return result
                    # 중앙 -> 우 (offset이 0일때 중복 방지)
                    if offset > 0:
                        x_right = center_x + offset
                        if x_right < width:
                            found, result = check_and_resolve(x_right, y)
                            if found:
                                return result
        elif direction in [SearchDirection.CENTER_LEFT_TO_RIGHT, SearchDirection.CENTER_RIGHT_TO_LEFT]:
            x_range = range(width) if direction == SearchDirection.CENTER_LEFT_TO_RIGHT else range(width - 1, -1, -1)
            center_y = height // 2
            for x in x_range:
                # 중앙에서 시작하여 상하로 확장
                for offset in range(max(center_y, height - center_y)):
                    # 중앙 -> 상
                    y_up = center_y - offset
                    if 0 <= y_up < height:
                        found, result = check_and_resolve(x, y_up)
                        if found:
                            return result
                    # 중앙 -> 하 (offset이 0일때 중복 방지)
                    if offset > 0:
                        y_down = center_y + offset
                        if y_down < height:
                            found, result = check_and_resolve(x, y_down)
                            if found:
                                return result
        # 중앙에서 외곽으로 확장 탐색
        elif direction == SearchDirection.CENTER_TO_CENTER:
            center_x, center_y = width // 2, height // 2
            max_r = max(center_x, width - center_x, center_y, height - center_y)
            for r in range(max_r + 1):
                # 반지름 r인 정사각형의 둘레를 시계방향으로 탐색
                for dx in range(-r, r + 1):
                    for dy in [-r, r]: # 상단과 하단 변
                        curr_x, curr_y = center_x + dx, center_y + dy
                        if 0 <= curr_x < width and 0 <= curr_y < height:
                            found, result = check_and_resolve(curr_x, curr_y)
                            if found:
                                return result
                for dy in range(-r + 1, r):
                    for dx in [-r, r]: # 좌측과 우측 변 (모서리 중복 제외)
                        curr_x, curr_y = center_x + dx, center_y + dy
                        if 0 <= curr_x < width and 0 <= curr_y < height:
                            found, result = check_and_resolve(curr_x, curr_y)
                            if found:
                                return result

        return None

    def click_action(self, x: int, y: int):
        """지정된 좌표로 마우스를 이동하고 클릭합니다."""
        # 좌표가 (0, 0)이면 오동작 방지를 위해 무시합니다.
        if int(x) == 0 and int(y) == 0:
            return
            
        self.mouse_controller.position = (int(x), int(y))
        
        if self.is_mac:
            # macOS에서는 이동 후 즉시 클릭하면 무시되는 경우가 많아 지연 시간을 늘리고 press/release를 분리합니다.
            time.sleep(0.1)
            self.mouse_controller.press(mouse.Button.left)
            time.sleep(0.05)
            self.mouse_controller.release(mouse.Button.left)
        else:
            time.sleep(0.05)
            self.mouse_controller.click(mouse.Button.left, 1)