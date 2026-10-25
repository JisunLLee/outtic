"""Keep mouse, Tk and screen capture coordinates in the same coordinate space."""
import sys


def enable_windows_dpi_awareness():
    """Run before Tk windows or pynput can select a different DPI mode."""
    if sys.platform != 'win32':
        return
    import ctypes

    try:
        # PER_MONITOR_AWARE_V2 handles monitors with different scaling factors.
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except (AttributeError, OSError):
        pass
    try:
        # Older Windows versions do not support the V2 API.
        if ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0:
            return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


def grab_area(bbox):
    from PIL import ImageGrab

    # Include the virtual desktop so negative coordinates on secondary monitors
    # refer to the same pixels as pynput's physical mouse coordinates.
    options = {'all_screens': True} if sys.platform == 'win32' else {}
    return ImageGrab.grab(bbox=bbox, **options).convert('RGB')


def color_at(x, y):
    x, y = int(x), int(y)
    return grab_area((x, y, x + 1, y + 1)).getpixel((0, 0))
