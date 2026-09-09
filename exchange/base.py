"""
KIA BOT - Exchange Base
"""

class Exchange:
    def __init__(self):
        self.name = "EXCHANGE"
        self.connected = False

    def connect(self):
        self.connected = True
        print(f"{self.name} connected")

    def disconnect(self):
        self.connected = False
        print(f"{self.name} disconnected")
