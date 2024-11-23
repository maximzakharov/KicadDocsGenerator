import os
import wx
import shutil
from threading import Thread
from .events import StatusEvent
from .process import ProcessManager
from .config import (
    gerberDir,
    drillDir,
    placementDir,
    bomFileDir,
    stackFileDir,
    layersJob,
)
from . import plot
import pcbnew
import configparser
from datetime import datetime
import subprocess
import platform


def bool_convert(text):
    return text == "True"


class ProcessThread(Thread):
    def __init__(self, wx, logs):
        self.logger = logs
        Thread.__init__(self)
        self.process_manager = ProcessManager(self.logger)
        self.wx = wx
        self.start()

        config = configparser.ConfigParser()
        plot_config = None
        config_file = os.path.join(
            os.path.dirname(self.process_manager.board.GetFileName()), "docs.config.ini"
        )

        plot_config = config.read(config_file)

        self.plot_scale = 1
        self.delete_single_page_files = True
        self.del_temp_files = True
        self.create_svg = False

        if plot_config:
            self.logger.info("plot_config SUCCESS " + str(plot_config))
            try:
                self.plot_scale = float(config.get("main", "scale"))
            except Exception as e:
                self.logger.warning(
                    "Failed to get plot_scale from config, using default value 1: %s", e
                )
                self.plot_scale = 1
            self.logger.info("Second plot_scale = " + str(self.plot_scale))
            self.delete_single_page_files = bool_convert(
                config.get("main", "delete_single_page_files")
            )
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

    @staticmethod
    def delete_directory(directory_path):
        if os.path.exists(directory_path):
            try:
                shutil.rmtree(directory_path)
            except Exception as e:
                print(f"Error deleting directory {directory_path}: {e}")
                wx.MessageBox(
                    f"Error deleting directory {directory_path}: {e}" "Error",
                    wx.OK | wx.ICON_ERROR,
                )

    def run(self):
        # initializing
        self.report(0)

        temp_dir = os.path.join(
            os.path.dirname(self.process_manager.board.GetFileName()), "temp"
        )

        project_path = self.process_manager.board.GetFileName()
        project_name = os.path.splitext(os.path.basename(project_path))[0]
        project_directory = os.path.dirname(self.process_manager.board.GetFileName())
        current_time = datetime.strftime(datetime.now(), "%d-%m-%Y")
        version = self.process_manager.get_revision(
            self.process_manager.board.GetFileName()
        )
        if version is None:
            version = "0"

        outputFolder = "production_" + project_name + "_" + current_time + "_" + version
        output_path = os.path.join(project_directory, outputFolder)

        self.delete_directory(temp_dir)
        self.delete_directory(output_path)

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
            self.process_manager.generate_bom(path, project_name)

            self.report(70)
            path = os.path.join(temp_dir, stackFileDir)
            os.makedirs(path, exist_ok=True)
            self.logger.info("genarate stackup info ")
            self.process_manager.genarate_stackup_info(
                path, self.process_manager.board.GetFileName(), project_name
            )

            self.report(75)

            enabled_templates = ["Top", "Bottom"]
            board = pcbnew.GetBoard()

            plot.plot_gerbers(
                board,
                temp_dir,
                layersJob,
                enabled_templates,
                self.del_temp_files,
                self.create_svg,
                self.plot_scale,
                self.delete_single_page_files,
            )

            self.report(90)

        except Exception as e:
            wx.MessageBox(str(e), "Error", wx.OK | wx.ICON_ERROR)
            self.report(-1)
            return

        try:
            shutil.copytree(temp_dir, output_path)
            shutil.make_archive(outputFolder, "zip", output_path)
            self.open_folder(output_path)

        except Exception as e:
            self.logger.error(f"Make archive failed {str(e)}")
            self.open_folder(temp_dir)

        self.delete_directory(temp_dir)
        self.report(-1)

    def report(self, status):
        self.logger.info("progress " + str(status) + "%")
        wx.PostEvent(self.wx, StatusEvent(status))
