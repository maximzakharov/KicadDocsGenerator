import logging
import os
from datetime import datetime

class LoggerConfig:
    def __init__(self):
        self.name = "kicad_app.log"

    def log(self, text, level):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.name, 'a') as file:
            file.write(current_time + " - " + str(level) + " - " + str(text) + "\r\n")

    def debug(self, text):
        self.log(text, "DEBUG")

    def info(self, text):
        self.log(text, "INFO")

    def error(self, text):
        self.log(text, "ERROR")
