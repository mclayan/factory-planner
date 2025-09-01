import tkinter as tk
import tkinter.ttk as ttk
import typing

from configuration import GuiConfig
from planner_ui import Controller, View


class LoginController(Controller):
    def __init__(self, master, v_id: str, parent: typing.Optional[typing.Self], config: GuiConfig):
        super().__init__(v_id, parent)
        self.config = config

        self.view = LoginView(master, self)
        self.view.btn_login.configure(command=self.cb_btn_login)
        self.notify_button_pressed = None

        users = [user.user_id for user in config.user_list]
        workstations = [ws.hostname for ws in config.workstation_list]
        self.view.cb_username.configure(values=users)
        self.view.cb_workstation.configure(values=workstations)

    def widget(self) -> tk.Widget:
        return self.view

    def value(self) -> typing.Optional[tuple[str, str]]:
        return self.view.cb_username.get(), self.view.cb_workstation.get()

    def set_value(self, val: tuple[str, str]):
        self.view.cb_username.set(val[0])
        self.view.cb_workstation.set(val[1])

    def cb_btn_login(self):
        if self.notify_button_pressed is not None:
            self.notify_button_pressed()


class LoginView(ttk.Frame, View):
    def __init__(self, master, controller: LoginController):
        View.__init__(self, controller)
        super().__init__(master)
        row = 0
        self.lbl_header = tk.Label(self, text='Please login to use the application:')
        self.lbl_header.grid(row=row, column=0, columnspan=2, pady=15)
        row += 1

        self.lbl_username = tk.Label(self, text='Username')
        self.lbl_username.grid(row=row, column=0, padx=10)

        self.cb_username = ttk.Combobox(self,)
        self.cb_username.grid(row=row, column=1, padx=10)
        row += 1

        self.lbl_workstation = tk.Label(self, text='Workstation')
        self.lbl_workstation.grid(row=row, column=0, padx=10)

        self.cb_workstation = ttk.Combobox(self,)
        self.cb_workstation.grid(row=row, column=1, padx=10)
        row += 1

        self.btn_login = tk.Button(self, text='Login')
        self.btn_login.grid(row=row, column=0, columnspan=2, padx=15, pady=15)
        row += 1
