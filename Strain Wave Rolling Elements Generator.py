import adsk.core, adsk.fusion, traceback
import math

handlers = []

class CycloidCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            cmd = args.command
            inputs = cmd.commandInputs

            # Input parameters (in mm, converted to internal cm)
            inputs.addValueInput('roller_diameter_mm', 'Roller Diameter (mm)', 'mm', adsk.core.ValueInput.createByReal(5.0 / 10.0))
            inputs.addIntegerSpinnerCommandInput('rollers_num', 'Number of Rollers', 3, 100, 1, 12)
            inputs.addValueInput('cycloid_outer_diameter_mm', 'Cycloid Outer Diameter (mm)', 'mm', adsk.core.ValueInput.createByReal(60.0 / 10.0))
            inputs.addValueInput('input_shaft_diameter_mm', 'Input Shaft Diameter (mm)', 'mm', adsk.core.ValueInput.createByReal(5.0 / 10.0))

            # Display calculated values (read-only)
            inputs.addTextBoxCommandInput('ecc_display', 'Eccentricity (mm)', '', 1, False)
            inputs.addTextBoxCommandInput('cav_num_display', 'Number of Cavities', '', 1, False)
            inputs.addTextBoxCommandInput('cy_r_min_display', 'Min Cycloid Radius (mm)', '', 1, False)
            inputs.addTextBoxCommandInput('wave_gen_r_display', 'Wave Generator Radius (mm)', '', 1, False)
            inputs.addTextBoxCommandInput('roll_r_display', 'Roller Radius (mm)', '', 1, False)

            # Add InputChanged event
            on_input_changed = CycloidInputChangedHandler()
            cmd.inputChanged.add(on_input_changed)
            handlers.append(on_input_changed)

            # Add Execute handler
            on_execute = CycloidCommandExecuteHandler()
            cmd.execute.add(on_execute)
            handlers.append(on_execute)

        except:
            app = adsk.core.Application.get()
            ui = app.userInterface
            ui.messageBox('Failed in CommandCreated: {}'.format(traceback.format_exc()))

class CycloidInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            inputs = args.firingEvent.sender.commandInputs

            # Get user input values
            roller_diameter = inputs.itemById('roller_diameter_mm').value
            rollers_num = inputs.itemById('rollers_num').value
            cycloid_outer_diameter = inputs.itemById('cycloid_outer_diameter_mm').value
            input_shaft_diameter = inputs.itemById('input_shaft_diameter_mm').value

            # Recalculate
            ecc = 0.2 * roller_diameter
            cav_num = rollers_num + 1
            cy_r_min = (1.1 * roller_diameter) / math.sin(math.pi / cav_num) + 2 * ecc
            wave_gen_r = (cycloid_outer_diameter / 2.0 - 2 * ecc) - roller_diameter
            roll_r = roller_diameter / 2.0

            # Update display
            inputs.itemById('ecc_display').text = f"{ecc * 10:.3f} mm"
            inputs.itemById('cav_num_display').text = str(cav_num)
            inputs.itemById('cy_r_min_display').text = f"{cy_r_min * 10:.3f} mm"
            inputs.itemById('wave_gen_r_display').text = f"{wave_gen_r * 10:.3f} mm"
            inputs.itemById('roll_r_display').text = f"{roll_r * 10:.3f} mm"

        except:
            app = adsk.core.Application.get()
            ui = app.userInterface
            ui.messageBox(f'Failed in InputChanged: {traceback.format_exc()}')

class CycloidCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface
            design = adsk.fusion.Design.cast(app.activeProduct)
            rootComp = design.rootComponent
            sketches = rootComp.sketches
            xyPlane = rootComp.xYConstructionPlane
            sketch = sketches.add(xyPlane)

            inputs = args.firingEvent.sender.commandInputs

            # Inputs (Fusion internal units are cm)
            roller_diameter = inputs.itemById('roller_diameter_mm').value
            rollers_num = inputs.itemById('rollers_num').value
            cycloid_outer_diameter = inputs.itemById('cycloid_outer_diameter_mm').value
            input_shaft_diameter = inputs.itemById('input_shaft_diameter_mm').value

            # Calculated values
            ecc = 0.2 * roller_diameter
            cav_num = rollers_num + 1
            cy_r_min = (1.1 * roller_diameter) / math.sin(math.pi / cav_num) + 2 * ecc
            cy_r = max(cycloid_outer_diameter / 2.0, cy_r_min)
            wave_gen_r = (cy_r - 2 * ecc) - roller_diameter
            roll_r = roller_diameter / 2.0

            points = cycloid_points(ecc, roll_r, wave_gen_r, rollers_num, cav_num)
            for i in range(len(points) - 1):
                sketch.sketchCurves.sketchLines.addByTwoPoints(points[i], points[i+1])

            theta = [2 * math.pi * i / rollers_num for i in range(rollers_num)]
            for t in theta:
                s_rol = math.sqrt((roll_r + wave_gen_r) ** 2 - (ecc * math.sin(cav_num * t)) ** 2)
                l_rol = ecc * math.cos(cav_num * t) + s_rol
                x = l_rol * math.sin(t)
                y = l_rol * math.cos(t)
                draw_circle(sketch, (x, y), roll_r)

            sep_width = 2.2 * ecc
            sep_middle_radius = wave_gen_r + roll_r
            sep_outer_radius = sep_middle_radius + sep_width / 2
            sep_inner_radius = sep_middle_radius - sep_width / 2
            draw_circle(sketch, (0, 0), sep_outer_radius)
            draw_circle(sketch, (0, 0), sep_inner_radius)

            draw_circle(sketch, (0, ecc), wave_gen_r)
            draw_circle(sketch, (0, 0), input_shaft_diameter / 2)

            ui.messageBox("Wave Gear sketch generated successfully.")
            adsk.terminate()

        except:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def cycloid_points(ecc, roll_r, wave_gen_r, rollers_num, cav_num, res=500):
    points = []
    for i in range(res):
        theta = (i / res) * 2 * math.pi
        s_rol = math.sqrt((roll_r + wave_gen_r) ** 2 - (ecc * math.sin(cav_num * theta)) ** 2)
        l_rol = ecc * math.cos(cav_num * theta) + s_rol
        xi = math.atan2(ecc * cav_num * math.sin(cav_num * theta), s_rol)

        x = l_rol * math.sin(theta) + roll_r * math.sin(theta + xi)
        y = l_rol * math.cos(theta) + roll_r * math.cos(theta + xi)
        points.append(adsk.core.Point3D.create(x, y, 0))
    points.append(points[0])
    return points

def draw_circle(sketch, center, radius):
    origin = adsk.core.Point3D.create(center[0], center[1], 0)
    sketch.sketchCurves.sketchCircles.addByCenterRadius(origin, radius)

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        cmdDefs = ui.commandDefinitions
        cmdId = 'CycloidGearCmdId'

        existingCmd = cmdDefs.itemById(cmdId)
        if existingCmd:
            existingCmd.deleteMe()

        cmdDef = cmdDefs.addButtonDefinition(cmdId, 'Cycloid Gear Generator', 'Generate a cycloid gear with user inputs.')

        onCommandCreated = CycloidCommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        handlers.append(onCommandCreated)

        cmdDef.execute()

        adsk.autoTerminate(False)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
