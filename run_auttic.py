import tkinter as tk
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app.ui import AppUI
from app.controller import AppController

if __name__ == "__main__":
    # 1. 메인 Tkinter 윈도우 생성
    root = tk.Tk()

    # 2. 애플리케이션의 "두뇌"인 컨트롤러 생성
    controller = AppController()

    # 3. 애플리케이션의 "얼굴"인 UI 생성, 컨트롤러를 넘겨줌
    ui = AppUI(root, controller)

    # 4. 두뇌(컨트롤러)에 얼굴(UI)을 연결하여 서로 통신할 수 있도록 함
    controller.set_ui(ui)
    
    # 5. Tkinter 이벤트 루프 시작
    root.mainloop()
