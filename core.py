"""
KIA BOT - Core
"""

class KIABot:
    def __init__(self):
        self.name = "KIA BOT"
        self.running = False

    def start(self):
        self.running = True
        print(f"{self.name} started")

    def stop(self):
        self.running = False
        print(f"{self.name} stopped")


if __name__ == "__main__":
    bot = KIABot()
    bot.start()
