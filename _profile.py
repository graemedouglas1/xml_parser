from _control import Control

class Profile:
    def __init__(self, name: str):
        self.name = name
        self.controls = []

    def add_control(self, control: Control):
        self.controls.append(control)
