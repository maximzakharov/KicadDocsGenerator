# KicadDocsGenerator

[![CI](https://github.com/maximzakharov/KicadDocsGenerator/actions/workflows/release.yml/badge.svg)](https://github.com/maximzakharov/KicadDocsGenerator/actions/workflows/release.yml)

This repository contains a plugin for KiCad that automates the creation of all necessary documentation for PCB manufacturing

## Installation

To install this plugin via a file, follow these steps:

1. **Download the Plugin File**

   Download the latest version of the plugin from the [releases page](https://github.com/maximzakharov/KicadDocsGenerator/releases).

2. **Open KiCad Plugin Manager**

4. **Install Plugin from File**

   - In the Plugin and Content Manager, click on the **Install from File...** button.
   - Locate and select the downloaded plugin `.zip` file.

5. **Install Required Python Modules**

   This plugin requires the following Python modules:
   - `pandas`
   - `openpyxl`
   - `xlsxwriter`
   - `pymupdf`

   You can install them using pip. Open a terminal or command prompt and run:
   ```bash
   pip install pandas openpyxl xlsxwriter pymupdf

6. **Restart KiCad**

   Restart KiCad to ensure the plugin is loaded correctly.

7. **Verify Installation**

   Open KiCad and navigate to the **Tools** menu. You should see the new plugin listed. If not, double-check that you have installed the plugin correctly.


## Problem with Ubuntu and possibly other Linux distros

When PyMuPDF (fitz) is installed with pip, KiCad crashes with a segmentation fault when Plugin is loaded. Plugin loads when the PCB Editor loads, so the crash happens directly when the PCB Editor is started. If this happens:
 `sudo apt install python3-fitz`
