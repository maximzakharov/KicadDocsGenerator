import pcbnew

netlistFileName = "netlist.ipc"
designatorsFileName = "designators.csv"
placementDir = "Pick Place"
placementFileName = "positions.csv"
bomFileDir = "BOM"
bomFileName = "bom.csv"
gerberDir = "Gerber"
drillDir = "Drill"
gerberArchiveName = "gerber.zip"
outputFolder = "production"
stackFileDir = "Report Board Stack"

# for gerber files
plotPlan = [
    ("F.Cu", pcbnew.F_Cu, "Top Layer"),
    ("B.Cu", pcbnew.B_Cu, "Bottom Layer"),
    ("In1.Cu", pcbnew.In1_Cu, "Internal plane 1"),
    ("In2.Cu", pcbnew.In2_Cu, "Internal plane 2"),
    ("In3.Cu", pcbnew.In3_Cu, "Internal plane 3"),
    ("In4.Cu", pcbnew.In4_Cu, "Internal plane 4"),
    ("F.SilkS", pcbnew.F_SilkS, "Top Silkscreen"),
    ("B.SilkS", pcbnew.B_SilkS, "Bottom Silkscreen"),
    ("F.Mask", pcbnew.F_Mask, "Top Soldermask"),
    ("B.Mask", pcbnew.B_Mask, "Bottom Soldermask"),
    ("F.Paste", pcbnew.F_Paste, "Top Paste (Stencil)"),
    ("B.Paste", pcbnew.B_Paste, "Bottom Paste (Stencil)"),
    ("Edge.Cuts", pcbnew.Edge_Cuts, "Board Outline"),
    ("User.Eco1", pcbnew.Eco1_User, "User layer"),
    ("User.Eco2", pcbnew.Eco2_User, "User layer"),
]

# for plot Job
layersJob = {
    "Top": {
        "mirrored": False,
        "tented": False,
        "enabled_layers": "User.1,F.Fab,F.Paste,F.Mask,Edge.Cuts,F.Silkscreen,User.9",
        "frame": "User.9",
        "layers": {
            "F.Cu": "#F0F0F0",
            "F.Paste": "#00CD66",
            "F.Mask": "#3FD3F2",
            "Edge.Cuts": "#575757",
            "User.Eco1": "#000000",
            "F.Silkscreen": "#000000",
            "F.Fab": "#000000",
            "F.Courtyard": "#000000",
            "User.1": "#000000",
            "B.Silkscreen": "#000000",
        },
        "layers_negative": {},
    },
    "Bottom": {
        "mirrored": True,
        "tented": False,
        "enabled_layers": "Edge.Cuts,B.Fab,B.Mask,B.Paste,B.Silkscreen,User.9,User.1",
        "frame": "User.9",
        "layers": {
            "B.Cu": "#F0F0F0",
            "B.Paste": "#00CD66",
            "B.Mask": "#3FD3F2",
            "Edge.Cuts": "#575757",
            "B.Fab": "#000000",
            "B.Silkscreen": "#000000",
            "B.Courtyard": "#000000",
            "User.1": "#000000",
        },
        "layers_negative": {},
    },
}
