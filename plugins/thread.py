import os
import wx
import shutil
import tempfile
from threading import Thread
from .events import StatusEvent
from .process import ProcessManager
from .config import *
import shutil
from . import plot
import pcbnew
import configparser
from datetime import datetime
import logging
import subprocess
import platform


def bool_convert(text):
    return text == "True"


class ProcessThread(Thread):
    def __init__(self, wx):
        Thread.__init__(self)
        self.process_manager = ProcessManager()
        self.wx = wx
        self.start()

        current_dir = os.path.dirname(__file__)

        log_level = logging.INFO
        LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        file_handler = logging.FileHandler(os.path.join(current_dir, "thread.log"))
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

        if len(logging.getLogger().handlers) == 0:
            logging.basicConfig(level=log_level, format=LOG_FORMAT, handlers=[file_handler, console_handler])
        else:
            logger = logging.getLogger(__name__)
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)

        config = configparser.ConfigParser()

        plot_config = None

        config_file = os.path.join(os.path.dirname(self.process_manager.board.GetFileName()), "docs.config.ini")

        plot_config = config.read(config_file)

        self.plot_scale = 1
        self.delete_single_page_files = True
        self.del_temp_files = True
        self.create_svg = False

        if plot_config:
            self.logger.info("plot_config SUCCESS " + str(plot_config))
            try:
                self.plot_scale = float(config.get("main", "scale"))
            except:
                self.plot_scale = 1
            self.logger.info("Second plot_scale = " + str(self.plot_scale))
            self.delete_single_page_files = bool_convert(config.get("main", "delete_single_page_files"))
            self.del_temp_files = bool_convert(config.get("main", "del_temp_files"))
            self.create_svg = bool_convert(config.get("main", "create_svg"))
        else:
            self.logger.info("plot_config FAILED " + str(plot_config))

    def open_folder(self, path):
        system_name = platform.system()
        if system_name == "Windows":  # Windows
            os.startfile(path)
        elif system_name == "Darwin":  # macOS
            subprocess.run(["open", path])
        elif system_name == "Linux":  # Linux
            subprocess.run(["xdg-open", path])
        else:
            raise NotImplementedError("Unsupported operating system")

    def run(self):
        # initializing
        self.report(0)

        temp_dir = os.path.join(os.path.dirname(self.process_manager.board.GetFileName()), "temp")
        temp_file = os.path.join(temp_dir, "tmp")

        project_name = self.process_manager.board.GetFileName().split("/")[-1].split(".")[0]
        project_directory = os.path.dirname(self.process_manager.board.GetFileName())
        current_time = datetime.strftime(datetime.now(), "%d-%m-%Y")
        version = self.process_manager.get_revision(self.process_manager.board.GetFileName())
        if version is None:
            version = "0"

        outputFolder = "production_" + project_name + "_" + current_time + "_" + version
        output_path = os.path.join(project_directory, outputFolder)

        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                wx.MessageBox(
                    "del_temp_files failed\n\nOn dir " + temp_dir + "\n\n" + traceback.format_exc(),
                    "Error",
                    wx.OK | wx.ICON_ERROR,
                )

        if os.path.exists(output_path):
            try:
                shutil.rmtree(output_path)
            except:
                wx.MessageBox(
                    "del_temp_files failed\n\nOn dir " + output_path + "\n\n" + traceback.format_exc(),
                    "Error",
                    wx.OK | wx.ICON_ERROR,
                )

        try:
            # configure and generate gerber
            self.report(5)
            path = os.path.join(temp_dir, gerberDir)
            os.makedirs(path, exist_ok=True)
            self.process_manager.generate_gerber(path)

            # generate drill file
            self.report(15)
            path = os.path.join(temp_dir, drillDir)
            os.makedirs(path, exist_ok=True)
            self.process_manager.generate_drills(path)

            # # generate netlist
            # self.report(25)
            # self.process_manager.generate_netlist(temp_dir)

            # generate pick and place file
            self.report(40)
            path = os.path.join(temp_dir, placementDir)
            os.makedirs(path, exist_ok=True)
            self.process_manager.generate_positions(path)

            # generate BOM file
            self.report(60)
            path = os.path.join(temp_dir, bomFileDir)
            os.makedirs(path, exist_ok=True)
            self.process_manager.generate_bom(path, project_name, wx)

            self.report(70)
            path = os.path.join(temp_dir, stackFileDir)
            os.makedirs(path, exist_ok=True)
            self.process_manager.genarate_steckup_info(path, self.process_manager.board.GetFileName(), project_name)

            self.report(75)
            layers = {
                "Top": {
                    "mirrored": True,
                    "tented": False,
                    "enabled_layers": "Edge.Cuts,B.Fab,B.Paste,B.Silkscreen,User.9,User.1",
                    "frame": "User.9",
                    "layers": {
                        "B.Cu": "#F0F0F0",
                        "B.Paste": "#00CD66",
                        "Edge.Cuts": "#575757",
                        "B.Fab": "#000000",
                        "B.Silkscreen": "#000000",
                        "B.Courtyard": "#000000",
                        "User.1": "#000000",
                    },
                    "layers_negative": {
                        "B.Fab": "false",
                        "B.Silkscreen": "false",
                        "B.Paste": "false",
                        "B.Courtyard": "false",
                        "Edge.Cuts": "false",
                        "User.1": "false",
                        "B.Cu": "false",
                    },
                },
                "Bottom": {
                    "mirrored": False,
                    "tented": False,
                    "enabled_layers": "User.1,F.Fab,F.Paste,Edge.Cuts,F.Silkscreen,User.9",
                    "frame": "User.9",
                    "layers": {
                        "F.Cu": "#F0F0F0",
                        "F.Paste": "#00CD66",
                        "Edge.Cuts": "#575757",
                        "User.Eco1": "#000000",
                        "F.Silkscreen": "#000000",
                        "F.Fab": "#000000",
                        "F.Courtyard": "#000000",
                        "User.1": "#000000",
                        "B.Silkscreen": "#000000",
                    },
                    "layers_negative": {
                        "User.Eco1": "false",
                        "Edge.Cuts": "false",
                        "F.Silkscreen": "false",
                        "F.Paste": "false",
                        "F.Cu": "false",
                        "F.Fab": "false",
                        "F.Courtyard": "false",
                        "User.1": "false",
                        "B.Silkscreen": "false",
                    },
                },
            }
            enabled_templates = ["Bottom", "Top"]
            board = pcbnew.GetBoard()

            plot.plot_gerbers(
                board,
                temp_dir,
                layers,
                enabled_templates,
                self.del_temp_files,
                self.create_svg,
                self.plot_scale,
                self.delete_single_page_files,
            )

            self.report(90)

            archive_file = self.process_manager.generate_archive(temp_dir, temp_file, project_name)

        except Exception as e:
            wx.MessageBox(str(e), "Error", wx.OK | wx.ICON_ERROR)
            self.report(-1)
            return

        try:
            if os.path.exists(output_path):
                shutil.rmtree(output_path)

            shutil.copytree(temp_dir, output_path)
            shutil.make_archive(outputFolder, "zip", output_path)
            self.open_folder(output_path)

        except Exception as e:
            self.open_folder(temp_dir)

        try:
            shutil.rmtree(temp_dir)
        except:
            wx.MessageBox(
                "del_temp_files failed\n\nOn dir " + temp_dir + "\n\n" + traceback.format_exc(),
                "Error",
                wx.OK | wx.ICON_ERROR,
            )

        self.report(-1)

    def report(self, status):
        wx.PostEvent(self.wx, StatusEvent(status))
