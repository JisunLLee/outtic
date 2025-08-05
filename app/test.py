import tkinter as tk
from tkinter import messagebox

class Calculator:
    def __init__(self, master):
        self.master = master
        self.master.title("간단 계산기")

        # 결과 표시창
        self.display = tk.Entry(master, width=30, justify='right')
        self.display.grid(row=0, column=0, columnspan=4, pady=5)

        # 버튼 텍스트
        buttons = [
            '7', '8', '9', '/',
            '4', '5', '6', '*',
            '1', '2', '3', '-',
            '0', '.', '=', '+'
        ]

        # 버튼 생성 및 배치
        row = 1
        col = 0
        for button in buttons:
            cmd = lambda x=button: self.click(x)
            tk.Button(master, text=button, width=5, command=cmd).grid(row=row, column=col)
            col += 1
            if col > 3:
                col = 0
                row += 1

    def click(self, key):
        if key == '=':
            try:
                result = eval(self.display.get())
                self.display.delete(0, tk.END)
                self.display.insert(tk.END, str(result))
            except:
                messagebox.showerror("에러", "잘못된 수식입니다")
                self.display.delete(0, tk.END)
        else:
            self.display.insert(tk.END, key)

# 메인 윈도우 생성
root = tk.Tk()
calculator = Calculator(root)
root.mainloop()