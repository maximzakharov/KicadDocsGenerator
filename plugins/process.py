# For better annotation.
from __future__ import annotations

# System base libraries
import os
import csv
import math
import shutil
from collections import defaultdict
import re
import pandas as pd

# Interaction with KiCad.
import pcbnew

# Application definitions.
from .config import *
import wx

term_regex = r"""(?mx)
    \s*(?:
        (?P<brackl>\()|
        (?P<brackr>\))|
        (?P<num>\-?\d+\.\d+|\-?\d+)|
        (?P<sq>"[^"]*")|
        (?P<s>[^(^)\s]+)
       )"""


class ProcessManager:
    def __init__(self, log):
        self.logger = log
        self.board = pcbnew.GetBoard()
        self.bom = []
        self.components = []
        self.__rotation_db = self.__read_rotation_db()

    @staticmethod
    def __read_rotation_db(filename: str = os.path.join(os.path.dirname(__file__), "rotations.cf")) -> dict[str, float]:
        """Read the rotations.cf config file so we know what rotations
        to apply later.
        """
        db = {}

        with open(filename, "r") as fh:
            for line in fh:
                line = line.rstrip()
                # remove all trailing space
                line = re.sub(r"\s*$", "", line)

                if line == "":
                    continue

                match = re.match(r"^([^\s]+)\s+(\d+)$", line)

                if match:
                    db.update({match.group(1): int(match.group(2))})

        return db

    def is_number(self, str):
        try:
            float(str)
            return True
        except ValueError:
            return False

    def to_float(self, string):
        num = 0
        if string and self.is_number(string):
            num = float(string)
        return num

    def _get_rotation_from_db(self, footprint: str) -> float:
        """Get the rotation to be added from the database file."""
        # Look for regular expression math of the footprint name and not its root library.
        fpshort = footprint.split(":")[-1]

        for expression, delta in self.__rotation_db.items():
            fp = fpshort

            if re.search(":", expression):
                fp = footprint

            if re.search(expression, fp):
                return delta

        return 0.0

    def generate_gerber(self, temp_dir):
        """Generate the Gerber files."""
        settings = self.board.GetDesignSettings()
        settings.m_SolderMaskMargin = 0
        settings.m_SolderMaskMinWidth = 0

        plot_controller = pcbnew.PLOT_CONTROLLER(self.board)

        plot_options = plot_controller.GetPlotOptions()
        plot_options.SetOutputDirectory(temp_dir)
        plot_options.SetPlotFrameRef(False)
        plot_options.SetSketchPadLineWidth(pcbnew.FromMM(0.1))
        plot_options.SetAutoScale(False)
        plot_options.SetScale(1)
        plot_options.SetMirror(False)
        plot_options.SetUseGerberAttributes(True)
        plot_options.SetUseGerberProtelExtensions(False)
        plot_options.SetUseAuxOrigin(True)
        plot_options.SetSubtractMaskFromSilk(True)
        plot_options.SetDrillMarksType(0)  # NO_DRILL_SHAPE

        if hasattr(plot_options, "SetExcludeEdgeLayer"):
            plot_options.SetExcludeEdgeLayer(True)

        for layer_info in plotPlan:
            if self.board.IsLayerEnabled(layer_info[1]):
                plot_controller.SetLayer(layer_info[1])
                plot_controller.OpenPlotfile(layer_info[0], pcbnew.PLOT_FORMAT_GERBER, layer_info[2])
                plot_controller.PlotLayer()

        plot_controller.ClosePlot()

    def generate_drills(self, temp_dir):
        """Generate the drill file."""
        drill_writer = pcbnew.EXCELLON_WRITER(self.board)

        drill_writer.SetOptions(False, True, self.board.GetDesignSettings().GetAuxOrigin(), True)
        drill_writer.SetFormat(True)
        drill_writer.CreateDrillandMapFilesSet(temp_dir, True, False)

    def generate_netlist(self, temp_dir):
        """Generate the connection netlist."""
        netlist_writer = pcbnew.IPC356D_WRITER(self.board)
        netlist_writer.Write(os.path.join(temp_dir, netlistFileName))

    def generate_positions(self, temp_dir):
        """Generate the position files."""
        if hasattr(self.board, "GetModules"):
            footprints = list(self.board.GetModules())
        else:
            footprints = list(self.board.GetFootprints())

        # sort footprint after designator
        footprints.sort(key=lambda x: x.GetReference())

        # unique designator dictionary
        footprint_designators = defaultdict(int)
        for i, footprint in enumerate(footprints):
            # count unique designators
            footprint_designators[footprint.GetReference()] += 1
        bom_designators = footprint_designators.copy()

        # if len(footprint_designators.items()) > 0:
        #     with open((os.path.join(temp_dir, designatorsFileName)), 'w', encoding='utf-8') as f:
        #         for key, value in footprint_designators.items():
        #             f.write('%s:%s\n' % (key, value))

        for i, footprint in enumerate(footprints):
            try:
                footprint_name = str(footprint.GetFPID().GetFootprintName())
            except AttributeError:
                footprint_name = str(footprint.GetFPID().GetLibItemName())

            layer = {
                pcbnew.F_Cu: "top",
                pcbnew.B_Cu: "bottom",
            }.get(footprint.GetLayer())

            # mount_type = {
            #     0: 'smt',
            #     1: 'tht',
            #     2: 'smt'
            # }.get(footprint.GetAttributes())

            if not footprint.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_POS_FILES:
                # append unique ID if duplicate footprint designator
                unique_id = ""
                if footprint_designators[footprint.GetReference()] > 1:
                    unique_id = str(footprint_designators[footprint.GetReference()])
                    footprint_designators[footprint.GetReference()] -= 1

                designator = "{}{}{}".format(footprint.GetReference(), "" if unique_id == "" else "_", unique_id)
                mid_x = (footprint.GetPosition()[0] - self.board.GetDesignSettings().GetAuxOrigin()[0]) / 1000000.0
                mid_y = (
                    (footprint.GetPosition()[1] - self.board.GetDesignSettings().GetAuxOrigin()[1]) * -1.0 / 1000000.0
                )
                rotation = (
                    footprint.GetOrientation().AsDegrees()
                    if hasattr(footprint.GetOrientation(), "AsDegrees")
                    else footprint.GetOrientation() / 10.0
                )
                # Get the rotation offset to be added to the actual rotation prioritizing the explicated by the
                # designer at the standards symbol fields. If not specified use the internal database.
                rotation_offset = self._get_rotation_offset_from_footprint(
                    footprint
                )  # or self._get_rotation_from_db(footprint)
                rotation = (rotation + rotation_offset) % 360.0

                # position offset needs to take rotation into account
                pos_offset = self._get_position_offset_from_footprint(footprint)
                rsin = math.sin(rotation / 180 * math.pi)
                rcos = math.cos(rotation / 180 * math.pi)
                pos_offset = (pos_offset[0] * rcos - pos_offset[1] * rsin, pos_offset[0] * rsin + pos_offset[1] * rcos)
                mid_x, mid_y = tuple(map(sum, zip((mid_x, mid_y), pos_offset)))

                self.components.append(
                    {
                        "Designator": designator,
                        "Mid X": mid_x,
                        "Mid Y": mid_y,
                        "Rotation": rotation,
                        "Layer": layer,
                    }
                )

            if not footprint.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_BOM:
                # append unique ID if we are dealing with duplicate bom designator
                unique_id = ""
                if bom_designators[footprint.GetReference()] > 1:
                    unique_id = str(bom_designators[footprint.GetReference()])
                    bom_designators[footprint.GetReference()] -= 1

                # merge similar parts into single entry
                insert = True
                for component in self.bom:
                    if component["Mfr_Part_Number"] == self._get_mfr_pn_from_footprint(footprint):
                        component["Designator"] += ", " + "{}{}{}".format(
                            footprint.GetReference(), "" if unique_id == "" else "_", unique_id
                        )
                        component["Quantity"] += 1
                        component["Total price"] += self.to_float(component["Unit price"])
                        insert = False

                # add component to BOM
                if insert:
                    self.bom.append(
                        {
                            "Designator": "{}{}{}".format(
                                footprint.GetReference(), "" if unique_id == "" else "_", unique_id
                            ),
                            "Footprint": self._normalize_footprint_name(footprint_name),
                            "Value": footprint.GetValue(),
                            # 'Mount': mount_type,
                            "Mfr_Part_Number": self._get_mfr_pn_from_footprint(footprint),
                            "Mfr_Name": self._get_mfr_name_from_footprint(footprint),
                            "Quantity": 1,
                            "LCSC_Part": self._get_lcsc_pn_from_footprint(footprint),
                            "Link": self._get_link_from_footprint(footprint),
                            "Unit price": self._get_unit_price_from_footprint(footprint),
                            "Total price": self.to_float(self._get_unit_price_from_footprint(footprint)),
                        }
                    )

        if len(self.components) > 0:
            with open((os.path.join(temp_dir, placementFileName)), "w", newline="", encoding="utf-8") as outfile:
                csv_writer = csv.writer(outfile)
                # writing headers of CSV file
                csv_writer.writerow(self.components[0].keys())

                for component in self.components:
                    # writing data of CSV file
                    if "**" not in component["Designator"]:
                        csv_writer.writerow(component.values())

    def generate_bom(self, temp_dir, project_name, wx):
        name = os.path.join(temp_dir, "Bill of Materials-" + project_name)
        bom_path = os.path.join(temp_dir, name + ".csv")

        if len(self.bom) > 0:
            with open(bom_path, "w", newline="", encoding="utf-8") as outfile:
                csv_writer = csv.writer(outfile)
                # writing headers of CSV file
                csv_writer.writerow(self.bom[0].keys())

                # Output all of the component information
                for component in self.bom:
                    # wx.MessageBox(component, "OK", wx.OK)
                    # writing data of CSV file
                    if "**" not in component["Designator"]:
                        csv_writer.writerow(component.values())

            writer = pd.ExcelWriter(name + ".xlsx")
            read_file = pd.read_csv(bom_path)
            read_file.to_excel(writer, sheet_name="BOM", index=False, na_rep="NaN")
            for column in read_file:
                column_width = max(read_file[column].astype(str).map(len).max(), len(column))
                col_idx = read_file.columns.get_loc(column)
                writer.sheets["BOM"].set_column(col_idx, col_idx, column_width)

            writer.close()

    def parse_sexp(self, sexp):
        # index = sexp.find("stackup", 0)
        # index_end = sexp.find("copper_finish", index)
        # print(str(index))
        # return " "
        stack = []
        out = []
        dbg = False

        if dbg:
            print("%-6s %-14s %-44s %-s" % tuple("term value out stack".split()))
        for termtypes in re.finditer(term_regex, sexp):
            # wx.MessageBox(str(termtypes), "OK", wx.OK)
            term, value = [(t, v) for t, v in termtypes.groupdict().items() if v][0]
            if dbg:
                print("%-7s %-14s %-44r %-r" % (term, value, out, stack))
            if term == "brackl":
                stack.append(out)
                out = []
            elif term == "brackr":
                assert stack, "Trouble with nesting of brackets"
                tmpout, out = out, stack.pop(-1)
                out.append(tmpout)
            elif term == "num":
                v = float(value)
                if v.is_integer():
                    v = int(v)
                out.append(v)
            elif term == "sq":
                out.append(value[1:-1])
            elif term == "s":
                out.append(value)
            else:
                raise NotImplementedError("Error: %r" % (term, value))
        assert not stack, "Trouble with nesting of brackets"
        return out[0]

    def get_stackup_info(self, board_file):
        keys = ["Layer", "Name", "Material", "Thickness", "Color"]
        layers = []
        with open(board_file, "rb") as f:
            data = f.read()

            sexp = self.parse_sexp(data.decode("utf-8"))
            stackup = ""
            for e in sexp:
                if e[0] == "setup":
                    stackup = e[1]
                    break

            count = 0

            for layer in stackup:
                if isinstance(layer, list) and layer[0] == "layer":
                    count += 1
                    layer_dict = dict.fromkeys(keys)
                    layer_dict["Layer"] = count
                    for properties in layer[1:]:
                        if properties[0] == "type":
                            layer_dict["Name"] = properties[1]
                        if properties[0] == "color":
                            layer_dict["Color"] = properties[1]
                        if properties[0] == "thickness":
                            layer_dict["Thickness"] = properties[1]
                        if properties[0] == "material":
                            layer_dict["Material"] = properties[1]
                    layers.append(layer_dict)

        return layers

    def get_revision(self, board_file):
        try:
            with open(board_file, "r") as file:
                for line in file:
                    match = re.search(r'property "VERSION" "([^"]+)"', line)
                    if match:
                        version = match.group(1)
                        return version
        except:
            pass
        return None

    def genarate_stackup_info(self, temp_dir, board_file, project_name):
        name = os.path.join(temp_dir, project_name)
        stack = self.get_stackup_info(board_file)
        if stack is None or len(stack) < 1:
            raise RuntimeError("Configure the PCB stack.")

        writer = pd.ExcelWriter(name + ".xlsx")
        fmt = writer.book.add_format({"font_name": "Calibri", "font_size": "18"})
        df1 = pd.DataFrame(stack)
        df1.to_excel(
            writer,
            sheet_name="Stackup",
            index=False,
            na_rep=" ",
        )

        for column in df1:
            column_width = max(df1[column].astype(str).map(len).max(), len(column))
            col_idx = df1.columns.get_loc(column)
            writer.sheets["Stackup"].set_column(col_idx, col_idx, column_width * 1.5, fmt)

        writer.close()

    def generate_archive(self, temp_dir, temp_file, project_name):
        """Generate the files."""
        temp_file = shutil.make_archive(project_name, "zip", temp_dir)
        temp_file = shutil.move(temp_file, temp_dir)
        return temp_file

    def _get_lcsc_pn_from_footprint(self, footprint):
        """'Get the MPN/LCSC stock code from standard symbol fields."""
        keys = ["LCSC_Part", "JLCPCB Part"]
        fallback_keys = ["LCSC", "JLC", "MPN", "Mpn", "mpn"]

        for key in keys:
            return footprint.GetFieldText(key)

        for key in fallback_keys:
            return footprint.GetFieldText(key)

    def _get_mfr_name_from_footprint(self, footprint):
        keys = ["Mfr_Name"]

        for key in keys:
            return footprint.GetFieldText(key)

    def _get_mfr_pn_from_footprint(self, footprint):
        """'Get the MPN/LCSC stock code from standard symbol fields."""
        keys = ["Mfr_Part_Number"]

        for key in keys:
            return footprint.GetFieldText(key)

    def _get_link_from_footprint(self, footprint):
        """'Get the MPN/LCSC stock code from standard symbol fields."""
        keys = ["Link"]

        for key in keys:
            return footprint.GetFieldText(key)

    def _get_unit_price_from_footprint(self, footprint):
        """'Get the MPN/LCSC stock code from standard symbol fields."""
        keys = ["Unit price"]

        for key in keys:
            return footprint.GetFieldText(key)

    def _get_rotation_offset_from_footprint(self, footprint) -> float:
        """Get the rotation from standard symbol fields."""
        keys = ["JLCPCB Rotation Offset"]
        fallback_keys = ["JlcRotOffset", "JLCRotOffset"]

        offset = None

        try:
            for key in keys + fallback_keys:
                offset = footprint.GetFieldText(key)
                break
        except:
            pass

        if offset is None or offset == "":
            return 0
        else:
            try:
                return float(offset)
            except ValueError:
                raise RuntimeError("Rotation offset of {} is not a valid number".format(footprint.GetReference()))

    def _get_position_offset_from_footprint(self, footprint):
        keys = ["JLCPCB Position Offset"]
        fallback_keys = ["JlcPosOffset", "JLCPosOffset"]

        offset = None

        try:
            for key in keys + fallback_keys:
                offset = footprint.GetFieldText(key)
                break
        except:
            pass

        if offset is None or offset == "":
            return (0, 0)
        else:
            try:
                return (float(offset.split(",")[0]), float(offset.split(",")[1]))
            except ValueError:
                raise RuntimeError(
                    "Position offset of {} is not a valid pair of numbers".format(footprint.GetReference())
                )

    def _normalize_footprint_name(self, footprint):
        # replace footprint names of resistors, capacitors, inductors, diodes, LEDs, fuses etc, with the footprint size only
        pattern = re.compile(r"^(\w*_SMD:)?\w{1,4}_(\d+)_\d+Metric.*$")

        return pattern.sub(r"\2", footprint)
