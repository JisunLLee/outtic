import sys
import unittest
from unittest.mock import Mock, patch

from app import screen_capture


class ScreenCaptureTests(unittest.TestCase):
    def test_windows_capture_includes_negative_monitor_coordinates(self):
        grab = Mock()
        with patch.object(sys, 'platform', 'win32'), patch.dict(
            sys.modules, {'PIL': Mock(ImageGrab=Mock(grab=grab))}
        ):
            screen_capture.color_at(-120.5, 250.8)
        grab.assert_called_once_with(bbox=(-120, 250, -119, 251), all_screens=True)
        grab.return_value.convert.assert_called_once_with('RGB')
        grab.return_value.convert.return_value.getpixel.assert_called_once_with((0, 0))

    def test_macos_keeps_bbox_capture_without_windows_options(self):
        grab = Mock()
        with patch.object(sys, 'platform', 'darwin'), patch.dict(
            sys.modules, {'PIL': Mock(ImageGrab=Mock(grab=grab))}
        ):
            screen_capture.grab_area((10, 20, 30, 40))
        grab.assert_called_once_with(bbox=(10, 20, 30, 40))

    def test_windows_selects_per_monitor_v2_before_legacy_api(self):
        import ctypes
        windll = Mock()
        with patch.object(sys, 'platform', 'win32'), patch.object(ctypes, 'windll', windll, create=True):
            screen_capture.enable_windows_dpi_awareness()
        self.assertEqual(windll.user32.SetProcessDpiAwarenessContext.call_args.args[0].value, ctypes.c_void_p(-4).value)
        windll.shcore.SetProcessDpiAwareness.assert_not_called()

    def test_windows_falls_back_when_v2_is_unavailable(self):
        import ctypes
        windll = Mock()
        windll.user32.SetProcessDpiAwarenessContext.side_effect = AttributeError
        windll.shcore.SetProcessDpiAwareness.return_value = 0
        with patch.object(sys, 'platform', 'win32'), patch.object(ctypes, 'windll', windll, create=True):
            screen_capture.enable_windows_dpi_awareness()
        windll.shcore.SetProcessDpiAwareness.assert_called_once_with(2)
        windll.user32.SetProcessDPIAware.assert_not_called()


if __name__ == '__main__':
    unittest.main()
