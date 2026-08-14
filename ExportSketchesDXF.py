"""
================================================================================
EXPORT SKETCHES DXF - FUSION ADD-IN
================================================================================

Command Name:    Export Sketches as DXF
Author:          Rohit Bapat via Autodesk Assistant
Version:         1.0
Description:     Export sketches and flat patterns from Fusion designs to DXF
                 format with comprehensive options for batch processing, unit
                 conversion, and geometric feature control.

Features:
- Export sketches from active design and child components
- Export flat patterns from sheet metal components
- Batch selection with preview counts
- Unit override (mm, cm, m, in, ft, or document units)
- Spline-to-polyline conversion option
- Center lines and extent lines for flat patterns
- Organized subfolder output structure
- Live status updates and error handling

Usage:
1. Open a Fusion design with sketches or sheet metal flat patterns
2. Run the add-in from Tools → Scripts and Add-Ins
3. Right click on any component and find "Export Sketches as DXF" at the bottom of the menu
4. Configure export options in the dialog
5. Select output folder and click Export

================================================================================
"""
import adsk.core
import adsk.fusion
import os
import traceback

_app      = None
_ui       = None
_handlers = []
_CMD_ID   = "ExportSketchesDXF_Cmd"
_CMD_NAME = "Export Sketches as DXF"

# _UNITS: (display label, DistanceUnits enum value or None for document default)
# Populated at run() time once adsk.fusion is available
_UNITS = []

# Populate unit labels and Fusion DistanceUnits values for the command UI.
def _init_units():
    global _UNITS
    du = adsk.fusion.DistanceUnits
    _UNITS = [
        ("Document Units", None),
        ("Millimeters",    du.MillimeterDistanceUnits),
        ("Centimeters",    du.CentimeterDistanceUnits),
        ("Meters",         du.MeterDistanceUnits),
        ("Inches",         du.InchDistanceUnits),
        ("Feet",           du.FootDistanceUnits),
    ]

# Return a filename-safe version of a Fusion object or occurrence name.
def _make_safe(name):
    # Keep alphanumerics, spaces, underscores, hyphens, and brackets.
    # Replace all other filesystem-unsafe characters with underscores.
    safe_chars = " _-[]{}()"
    return "".join(c if (c.isalnum() or c in safe_chars) else "_" for c in name).strip()

# Collect exportable sketches and flat patterns from a component hierarchy.
def _collect(component, occ_name, only_visible, include_children):
    results = []
    for i in range(component.sketches.count):
        sk = component.sketches.item(i)
        if only_visible and not sk.isLightBulbOn:
            continue
        results.append({"inst": occ_name, "type": "sketch", "obj": sk})
    try:
        fp = component.flatPattern
        if fp is not None:
            results.append({"inst": occ_name, "type": "flatpattern", "obj": fp})
    except Exception:
        pass
    if include_children:
        for i in range(component.occurrences.count):
            child_occ = component.occurrences.item(i)
            if only_visible and not child_occ.isLightBulbOn:
                continue
            results.extend(_collect(
                child_occ.component, child_occ.name,
                only_visible, include_children))
    return results

# Build the export-item list from the current dialog selections and options.
def _get_items(inputs):
    only_visible     = _find_input(inputs, "sketch_filter").selectedItem.index == 1
    include_children = _find_input(inputs, "opt_children").value
    inc_fp           = _find_input(inputs, "opt_flatpattern").value
    design           = adsk.fusion.Design.cast(_app.activeProduct)
    sel_input        = _find_input(inputs, "sel_components")
    items = []
    if sel_input and sel_input.selectionCount > 0:
        for i in range(sel_input.selectionCount):
            sel = sel_input.selection(i)
            occ = adsk.fusion.Occurrence.cast(sel.entity)
            if occ:
                items.extend(_collect(occ.component, occ.name, only_visible, include_children))
            else:
                comp = adsk.fusion.Component.cast(sel.entity)
                if comp:
                    items.extend(_collect(comp, comp.name, only_visible, include_children))
    else:
        items.extend(_collect(design.rootComponent, design.rootComponent.name, only_visible, include_children))
    if not inc_fp:
        items = [x for x in items if x["type"] != "flatpattern"]
    return items

# Recursively search for an input by ID, including inputs inside groups.
def _find_input(inputs, input_id):
    found = inputs.itemById(input_id)
    if found:
        return found
    for i in range(inputs.count):
        item = inputs.item(i)
        if hasattr(item, 'children'):
            found = _find_input(item.children, input_id)
            if found:
                return found
    return None

# Display status messages in the command dialog and process pending UI events.
def _set_log(inputs, lines):
    tb = _find_input(inputs, "status_log")
    if tb:
        tb.formattedText = "<br>".join(lines)
        tb.isFullWidth = True
    adsk.doEvents()

# Prompt for an output folder and export all currently selected DXF items.
def _run_export(inputs):
    try:
        unit_idx       = _find_input(inputs, "unit_override").selectedItem.index
        unit_val       = _UNITS[unit_idx][1]  # None = document default, else DistanceUnits enum
        use_subfolders = _find_input(inputs, "opt_subfolders").value
        inc_points     = _find_input(inputs, "opt_points").value
        inc_projected  = _find_input(inputs, "opt_projected").value
        inc_constr     = _find_input(inputs, "opt_construction").value
        do_spline       = _find_input(inputs, "opt_spline").value
        spline_tol      = _find_input(inputs, "opt_spline_tol").value
        inc_centerlines = _find_input(inputs, "opt_centerlines").value
        inc_extentlines = _find_input(inputs, "opt_extentlines").value

        design     = adsk.fusion.Design.cast(_app.activeProduct)
        export_mgr = design.exportManager
        items      = _get_items(inputs)

        if not items:
            _set_log(inputs, ["No items found to export."])
            return

        folder_dlg = _ui.createFolderDialog()
        folder_dlg.title = "Select Output Folder for DXF Files"
        if folder_dlg.showDialog() != adsk.core.DialogResults.DialogOK:
            _set_log(inputs, ["Export cancelled."])
            return
        out_root = folder_dlg.folder

        total     = len(items)
        exported  = 0
        failed    = 0
        log_lines = ["Output : " + out_root, "Total  : " + str(total), ""]
        _set_log(inputs, log_lines)

        for idx, item in enumerate(items):
            inst_name = item["inst"]
            item_type = item["type"]
            obj       = item["obj"]
            safe_inst = _make_safe(inst_name)
            prefix    = "[" + str(idx+1) + "/" + str(total) + "]  "

            if use_subfolders:
                out_folder = os.path.join(out_root, safe_inst)
                os.makedirs(out_folder, exist_ok=True)
            else:
                out_folder = out_root

            if item_type == "sketch":
                if use_subfolders:
                    filename = _make_safe(obj.name) + ".dxf" # Do not include Component name if subfolders are created for each component
                else:
                    filename = safe_inst + "_" + _make_safe(obj.name) + ".dxf"
            else:
                filename = safe_inst + "_FlatPattern.dxf"

            filepath = os.path.join(out_folder, filename)

            try:
                if item_type == "sketch":
                    opts = export_mgr.createDXFSketchExportOptions(filepath, obj)
                    opts.isPointsExported            = inc_points
                    opts.isProjectedGeometryExported = inc_projected
                    opts.isConstructionExported      = inc_constr
                    if unit_val is not None:
                        opts.units = unit_val
                else:
                    opts = export_mgr.createDXFFlatPatternExportOptions(filepath, obj)
                    opts.isSplineConvertedToPolyline = do_spline
                    if do_spline:
                        opts.convertToPolylineTolerance = spline_tol
                    opts.isCenterLinesExported = inc_centerlines
                    opts.isExtentLinesExported = inc_extentlines
                    if unit_val is not None:
                        opts.units = unit_val
                export_mgr.execute(opts)
                exported += 1
                log_lines.append(prefix + "OK    " + filename)
            except Exception as exc:
                failed += 1
                log_lines.append(prefix + "FAIL  " + filename + "  ->  " + str(exc))

            _set_log(inputs, log_lines)

        log_lines.extend(["", "--- Done ---",
            "Exported : " + str(exported),
            "Failed   : " + str(failed)])
        _set_log(inputs, log_lines)

    except Exception:
        _ui.messageBox("Export error:\n" + traceback.format_exc())

# ---------------------------------------------------------------------------
# Add this add-in's command to Fusion's linear marking menu.
class _MarkingMenuHandler(adsk.core.MarkingMenuEventHandler):
    # Initialize the Fusion marking-menu event handler.
    def __init__(self):
        super().__init__()

    # Add the command definition when Fusion displays the marking menu.
    def notify(self, args):
        try:
            menu_args = adsk.core.MarkingMenuEventArgs.cast(args)
            cmd_def = _ui.commandDefinitions.itemById(_CMD_ID)
            if cmd_def:
                menu_args.linearMarkingMenu.controls.addCommand(cmd_def, "", True)
        except Exception:
            _ui.messageBox("Marking menu error:\n" + traceback.format_exc())

# Recount available items and refresh the status log.
def _update_preview(inputs):
    try:
        items     = _get_items(inputs)
        sk_count  = sum(1 for x in items if x["type"] == "sketch")
        fp_count  = sum(1 for x in items if x["type"] == "flatpattern")
        sel       = _find_input(inputs, "sel_components")
        sel_count = sel.selectionCount if sel else 0
        comp_label = str(sel_count) + " component(s) selected" if sel_count > 0 else "Root component"
        _set_log(inputs, [
            "Components    : " + comp_label,
            "Sketches      : " + str(sk_count),
            "Flat Patterns : " + str(fp_count),
            "Total items   : " + str(len(items)),
            "",
            "Click Export to choose output folder and start."
        ])
    except Exception:
        _ui.messageBox("Preview error:\n" + traceback.format_exc())

# ---------------------------------------------------------------------------
# Handle dialog changes by refreshing previews or starting an export.
class _InputChangedHandler(adsk.core.InputChangedEventHandler):
    # Initialize the Fusion input-changed event handler.
    def __init__(self):
        super().__init__()

    # Respond to export-button clicks and changes to export configuration.
    def notify(self, args):
        try:
            changed_input = args.input
            # Use the command's full commandInputs so grouped inputs are accessible
            inputs = args.input.parentCommand.commandInputs
            if changed_input.id == "btn_export":
                _run_export(inputs)
            elif changed_input.id != "status_log":
                _update_preview(inputs)
        except Exception:
            _ui.messageBox("InputChanged error:\n" + traceback.format_exc())

# ---------------------------------------------------------------------------
# Build the DXF export command dialog when Fusion creates the command.
class _CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    # Initialize the Fusion command-created event handler.
    def __init__(self):
        super().__init__()

    # Create dialog inputs and register the dialog input-change handler.
    def notify(self, args):
        try:
            cmd = args.command
            cmd.isRepeatable = False
            cmd.cancelButtonText = "Close"
            cmd.isOKButtonVisible = False
            inputs = cmd.commandInputs

            # Component selection (multi-select)
            sel = inputs.addSelectionInput(
                "sel_components", "Components",
                "Select components to export (leave empty for root)")
            sel.addSelectionFilter(adsk.core.SelectionFilters.Occurrences)
            sel.addSelectionFilter(adsk.core.SelectionFilters.RootComponents)
            sel.setSelectionLimits(0, 0)

            # ---- Options - General (expanded by default) ----
            grp_gen = inputs.addGroupCommandInput("grp_general", "Options - General")
            grp_gen.isExpanded = True
            grp_gen.isEnabledCheckBoxDisplayed = False
            g = grp_gen.children

            dd = g.addDropDownCommandInput(
                "sketch_filter", "Sketches to export",
                adsk.core.DropDownStyles.LabeledIconDropDownStyle)
            dd.listItems.add("All Sketches", True,  "")
            dd.listItems.add("Only Visible", False, "")

            ud = g.addDropDownCommandInput(
                "unit_override", "DXF Units",
                adsk.core.DropDownStyles.LabeledIconDropDownStyle)
            for label, _ in _UNITS:
                ud.listItems.add(label, label == "Document Units", "")

            g.addBoolValueInput("opt_children",
                "Include Sketches from Child Components", True, "", False)
            g.addBoolValueInput("opt_flatpattern",
                "Include Flat Patterns",                  True, "", True)
            g.addBoolValueInput("opt_subfolders",
                "Create Subfolder per Component",         True, "", False)
            g.addBoolValueInput("opt_points",
                "Include Points",                True, "", True)
            g.addBoolValueInput("opt_projected",
                "Include Projected Geometry",    True, "", True)
            g.addBoolValueInput("opt_construction",
                "Include Construction Geometry", True, "", True)

            # ---- Options - Flat Pattern (collapsed by default) ----
            grp_fp = inputs.addGroupCommandInput("grp_flatpattern", "Options - Flat Pattern")
            grp_fp.isExpanded = False
            grp_fp.isEnabledCheckBoxDisplayed = False
            f = grp_fp.children

            f.addBoolValueInput("opt_spline",
                "Convert Splines to Polylines", True, "", False)
            f.addValueInput("opt_spline_tol", "Polyline Tolerance",
                "mm", adsk.core.ValueInput.createByReal(0.1))
            f.addBoolValueInput("opt_centerlines",
                "Include Bend Center Lines", True, "", True)
            f.addBoolValueInput("opt_extentlines",
                "Include Bend Extent Lines", True, "", True)

            # Export button (outside groups, triggers export without closing dialog)
            inputs.addBoolValueInput("btn_export",
                "Export", False, "", False)

            # Expandable Status group
            grp = inputs.addGroupCommandInput("status_group", "Status")
            grp.isExpanded = True
            grp.isEnabledCheckBoxDisplayed = False
            tb = grp.children.addTextBoxCommandInput(
                "status_log", "",
                "Select components (or leave empty for root) then click Export.",
                10, True)
            tb.isFullWidth = True

            input_changed_h = _InputChangedHandler()
            cmd.inputChanged.add(input_changed_h)
            _handlers.append(input_changed_h)

        except Exception:
            _ui.messageBox("Command created error:\n" + traceback.format_exc())

# ---------------------------------------------------------------------------
# Register the DXF export command and its Fusion event handlers.
def run(context):
    global _app, _ui
    try:
        _app = adsk.core.Application.get()
        _ui  = _app.userInterface
        _init_units()  # populate _UNITS with proper DistanceUnits enum values
        cmd_def = _ui.commandDefinitions.itemById(_CMD_ID)
        if not cmd_def:
            cmd_def = _ui.commandDefinitions.addButtonDefinition(
                _CMD_ID, _CMD_NAME,
                "Export sketches and flat patterns as DXF.", "")
        on_created = _CommandCreatedHandler()
        cmd_def.commandCreated.add(on_created)
        _handlers.append(on_created)
        on_menu = _MarkingMenuHandler()
        _ui.markingMenuDisplaying.add(on_menu)
        _handlers.append(on_menu)
    except Exception:
        if _ui:
            _ui.messageBox("Start error:\n" + traceback.format_exc())

# Remove the DXF export command and release registered event handlers.
def stop(context):
    global _app, _ui
    try:
        _app = adsk.core.Application.get()
        _ui  = _app.userInterface
        cmd_def = _ui.commandDefinitions.itemById(_CMD_ID)
        if cmd_def:
            cmd_def.deleteMe()
        _handlers.clear()
    except Exception:
        if _ui:
            _ui.messageBox("Stop error:\n" + traceback.format_exc())
