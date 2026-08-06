# ExportSketchesDXF — Fusion 360 Add-In

> Batch-export sketches and sheet metal flat patterns from any component directly to DXF — with live progress, full control over what gets included, and a dialog that stays open so you can export again without re-opening it.

---

## ✨ Features

- **Batch export** — right-click any component in the browser or canvas and export all its sketches and flat patterns in one go
- **Child component traversal** — optionally walk the entire component tree recursively and export sketches from every child
- **Flat pattern support** — automatically detects sheet metal flat patterns and exports them alongside sketches
- **Unit override** — choose the DXF output unit independently of the document units (mm, cm, m, inches, feet, or document default)
- **Sketch filter** — export all sketches or only the visible ones
- **DXF content control** — individually toggle Points, Projected Geometry, and Construction Geometry per export
- **Flat pattern options** — toggle Bend Center Lines, Bend Extent Lines, and Spline-to-Polyline conversion (with configurable tolerance)
- **Subfolder per component** — optionally organise output into subfolders named after each component instance
- **Multi-component batch** — select multiple components at once from the dialog for a single export run
- **Live status log** — watch each file export line by line inside the dialog with a running count of successes and failures
- **Dialog stays open** — export, adjust options, and export again without reopening the dialog

---

## 📁 Output Filename Format

_.dxf _FlatPattern.dxf

**Example**:
Wheel_1_Profile.dxf Wheel_1_FlatPattern.dxf Hub_1_Base_Sketch.dxf


---

## 🖥️ Dialog Overview

| Section | Controls |
|---|---|
| **Components** | Multi-select component picker (leave empty to use root) |
| **Options — General** | Sketch filter, DXF units, Child components, Flat patterns, Subfolders, Points, Projected & Construction geometry |
| **Options — Flat Pattern** | Spline-to-polyline, Polyline Tolerance, Bend Center Lines, Bend Extent Lines |
| **Export** | Triggers export without closing the dialog |
| **Status** | Expandable live log showing per-file progress and final summary |

---

## 🚀 Installation

1. Download or clone this repository
2. Copy the `ExportSketchesDXF` folder into your Fusion add-ins directory:
   - **Mac:** `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/`
   - **Windows:** `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\`
3. In Fusion, open **Tools → Scripts and Add-Ins** (or press **Shift+S**)
4. Switch to the **Add-Ins** tab, find **ExportSketchesDXF**, and click **Run**
5. Optionally enable **Run on Startup** so it loads automatically every session

---

## 🎯 How to Use

1. Open a Fusion design containing sketches or sheet metal components
2. **Right-click** any component in the browser or canvas
3. Select **Export Sketches as DXF** from the context menu
4. Configure your options in the dialog
5. Click **Export**, choose an output folder, and watch the live status log
6. Adjust options and export again — the dialog stays open

---

## ⚠️ Notes

- The `createDXFSketchExportOptions` API is a **preview feature** (introduced January 2025). Avoid distributing this add-in commercially until it moves to released status.
- Flat pattern export requires the component to be a sheet metal part with a valid flat pattern.
- If a sketch or flat pattern fails to export, the error reason is shown inline in the Status log — other items continue exporting.

---

## 📄 License

MIT License — free to use, modify, and distribute.

