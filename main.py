import bpy
import sys
import time
from random import seed
from random import randint
from math import radians, sqrt, cos, sin
from mathutils import Matrix, Vector

sys.path.append('/home/job/.local/lib/python3.7/site-packages')

bpy.app.debug_wm = False

materials = {#"concrete": {"type": "ACTIVE", "density": 7500, "friction": 0.7,"collision_shape": "CONVEX_HULL"},  #TODO these values are not correct yet
             "metal": {"type": "ACTIVE", "density": 7500, "friction": 0.42,"collision_shape": "CYLINDER"},
             "dish": {"type": "ACTIVE", "density": 2710, "friction": 1.4,"collision_shape": "CONVEX_HULL"},
             "ground": {"type": "PASSIVE", "friction": 1}}

object_names = []

def calc_physics(mytool):
    bpy.ops.ptcache.free_bake_all()
    bpy.context.scene.rigidbody_world.time_scale = mytool.dem_speed_float
    bpy.context.scene.rigidbody_world.substeps_per_frame = int(mytool.dem_substeps_float)
    bpy.context.scene.rigidbody_world.solver_iterations = int(mytool.dem_solver_iter_float)
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 300
    bpy.ops.ptcache.bake_all(bake=True)


# linear function
def eval(x):
    return x if x >= 0 and x <= 1 else 0

def initObjectNames():
    for obj in bpy.context.scene.objects:
        if obj.name.startswith("dish"):
            object_names.append(obj.name)

    for obj in bpy.context.scene.objects:
        if obj.name.startswith("metal"):
            object_names.append(obj.name)

    for obj in bpy.context.scene.objects:
        if obj.name.startswith("hinge"):
            object_names.append(obj.name)


def find_position_sides(obj):  # TODO test this for actual rotation
    xRot = obj.rotation_euler[0]
    yRot = obj.rotation_euler[1]
    zRot = obj.rotation_euler[2]

    xrot_matrix = Matrix.Rotation(xRot, 3, 'X')
    yrot_matrix = Matrix.Rotation(yRot, 3, 'Y')
    zrot_matrix = Matrix.Rotation(zRot, 3, 'Z')

    end_point1 = Vector((0, 0, obj.scale[2]))
    end_point2 = Vector((0, 0, -obj.scale[2]))  # add more than just the z endpoints, also add x and y.

    end_point1 = end_point1 @ xrot_matrix @ yrot_matrix @ zrot_matrix
    end_point2 = end_point2 @ xrot_matrix @ yrot_matrix @ zrot_matrix

    end_point1 = obj.matrix_world.translation + end_point1
    end_point2 = obj.matrix_world.translation + end_point2

    return end_point1, end_point2, obj.location


def find_closest_object(this_obj):
    threshold = 1
    assert (this_obj.name.startswith("hinge"))

    for obj in bpy.context.scene.objects:
        for m in materials:
            if m == "ground" or this_obj == obj or this_obj.parent == obj:
                continue

            if obj.name.startswith(m):

                poss = find_position_sides(obj)

                for p in poss:
                    if -threshold < (this_obj.matrix_world.translation - p).length < threshold:
                        return obj

    return None


# before executing this script. MAKE SURE YOUR BUILD IS CENTERED AROUND ITS ORIGIN.
# otherwise the evaluation might not work properly

def evaluate_demolition(scene, hard_max_radius, hard_max_height):
    max_radius = 0
    max_height = 0
    for obj in bpy.context.scene.objects:
        for m in materials:
            if m == "ground":
                continue
            if obj.name.startswith(m):
                loc = obj.matrix_world.translation
                max_height = max(loc[2], max_height)
                max_radius = max(sqrt(loc[0] ** 2 + loc[1] ** 2),
                                 max_radius)  # todo: this treats the center of an object as its location, but in reality we want to check its edges

    print(f"max radius {max_radius}")
    print(f"max height {max_height}")
    print(f"hard max radius {hard_max_radius}")
    print(f"hard max height {hard_max_height}")
    radius_eval = eval(max_radius / (hard_max_radius * 2))
    height_eval = eval(max_height / (hard_max_height * 2))

    print(f"eval radius {radius_eval}")
    print(f"eval height {height_eval}")

    return radius_eval, height_eval

def addMaterialProperties(object_name, mat):
    obj = bpy.context.scene.objects[object_name]
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.rigidbody.object_add(type=mat["type"] if mat["type"] else "ACTIVE")
    if "collision_shape" in mat:
        bpy.ops.rigidbody.shape_change(type=mat["collision_shape"])
    else:
        bpy.ops.rigidbody.shape_change(type='CONVEX_HULL')
    bpy.ops.object.modifier_add(type='COLLISION')

    if "density" in mat:
        bpy.ops.rigidbody.mass_calculate(material='Custom',density=mat["density"])

    if "friction" in mat:
        obj.rigid_body.friction = mat["friction"]

    if "restitution" in mat:
        obj.rigid_body.restitution = mat["restitution"]

    obj.select_set(False)
    bpy.context.view_layer.objects.active = None

def addHingeProperies(object_name, breaking_threshold):
    print(object_name)
    obj = bpy.context.scene.objects[object_name]
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.rigidbody.constraint_add()
    bpy.context.object.rigid_body_constraint.type = 'HINGE'
    bpy.context.object.rigid_body_constraint.disable_collisions = False
    bpy.context.object.rigid_body_constraint.use_breaking = True
    bpy.context.object.rigid_body_constraint.object1 = obj.parent
    next_paired_obj = find_closest_object(obj)
    if next_paired_obj is not None:
        bpy.context.object.rigid_body_constraint.object2 = next_paired_obj
    bpy.context.object.rigid_body_constraint.breaking_threshold = breaking_threshold  # TODO: breaking threshold

    obj.select_set(False)
    bpy.context.view_layer.objects.active = None

def removeMaterialProperties(object_name):
    obj = bpy.context.scene.objects[object_name]
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bpy.ops.rigidbody.object_remove()
    bpy.ops.object.modifier_remove(modifier="Collision")

    obj.select_set(False)
    bpy.context.view_layer.objects.active = None

def removeHingeProperties(object_name):
    obj = bpy.context.scene.objects[object_name]
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bpy.ops.rigidbody.constraint_remove()

    obj.select_set(False)
    bpy.context.view_layer.objects.active = None

def alreadyInitialized():
    obj = bpy.context.scene.objects["dish.001"]
    if obj.rigid_body is None:
        return True

    return obj.rigid_body.friction != 0


def setObjectProperties(obj_names, breaking_threshold):
    if not alreadyInitialized():
       return

    bpy.ops.object.select_all(action='DESELECT')

    for object_name in obj_names:
        if object_name.startswith("dis"):
            addMaterialProperties(object_name, materials["dish"])
        elif object_name.startswith("metal"):
            addMaterialProperties(object_name, materials["metal"])
        else:
            addHingeProperies(object_name, breaking_threshold)

    bpy.ops.object.select_all(action='DESELECT')

def removeObjectProperties(obj_names):
    if alreadyInitialized():
       return

    bpy.ops.object.select_all(action='DESELECT')

    for object_name in obj_names:
        print(object_name)
        if object_name.startswith("dish"):
            removeMaterialProperties(object_name)
        elif object_name.startswith("metal"):
            removeMaterialProperties(object_name)
        else:
            removeHingeProperties(object_name)

    bpy.ops.object.select_all(action='DESELECT')

# define the sliders of the UI window
class MyProperties(bpy.types.PropertyGroup):
    dem_threshold_float: bpy.props.FloatProperty(name="Breaking threshold", soft_min=0, soft_max=50, default=10,
                                                 step=0.1,
                                                 precision=2)
    dem_substeps_float: bpy.props.FloatProperty(name="Substeps Per Frame", soft_min=0, soft_max=100, default=10, step=1)
    dem_solver_iter_float: bpy.props.FloatProperty(name="Solver Iterations", soft_min=0, soft_max=100, default=10,
                                                   step=1)
    dem_speed_float: bpy.props.FloatProperty(name="Speed", soft_min=0, soft_max=10, default=1, step=0.1, precision=2)


# initiate the UI panel
class DEMOLITION_PT_main_panel(bpy.types.Panel):
    bl_label = "Demolition Controller"
    bl_idname = "DEMOLITION_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Demolition"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool

        layout.label(text="setup")
        # layout.operator("demolition.op_initialize")
        # layout.operator("demolition.op_reset")
        layout.prop(mytool, "dem_threshold_float")
        layout.label(text="animation")
        layout.prop(mytool, "dem_substeps_float")
        layout.prop(mytool, "dem_solver_iter_float")
        layout.prop(mytool, "dem_speed_float")
        # layout.operator("demolition.op_start")
        # layout.operator("demolition.op_stop")
        layout.label(text="find optimal demolition")
        layout.operator("demolition.op_genetic")


class DEMOLITION_OT_initialize(bpy.types.Operator):
    bl_label = "Initialize"
    bl_idname = "demolition.op_initialize"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool

        setObjectProperties(object_names, mytool.dem_threshold_float)

        return {'FINISHED'}


class DEMOLITION_OT_start(bpy.types.Operator):
    bl_label = "Start"
    bl_idname = "demolition.op_start"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool

        bpy.ops.object.select_all(action='DESELECT')
        calc_physics(mytool)
        bpy.ops.screen.animation_play()

        return {'FINISHED'}


class DEMOLITION_OT_stop(bpy.types.Operator):
    bl_label = "Stop"
    bl_idname = "demolition.op_stop"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool

        evaluate_demolition(scene, 5, 1)

        bpy.ops.screen.animation_cancel()
        bpy.ops.object.select_all(action='DESELECT')

        return {'FINISHED'}


class DEMOLITION_OT_genetic(bpy.types.Operator):
    bl_label = "Genetic algorithm"
    bl_idname = "demolition.op_genetic"

    max_gene_size = 50
    removable_object_names = []
    gene = []

    def initialize(self, objects):
        seed(1)

        for idx in range(0, self.max_gene_size):
            objIdx = randint(0, len(object_names) - 1)
            if objIdx not in self.gene:
                self.gene.append(objIdx)


    def evaluateGene(self, gene, mytool):
        obj_names = object_names.copy()
        for idx in gene:
            print(str(idx) + "," + str(len(object_names)))
            bpy.context.scene.objects[object_names[idx]].location += Vector((0.0, 0.0, -50.0))
            obj_names.remove(object_names[idx])

        setObjectProperties(obj_names, mytool.dem_threshold_float);
        calc_physics(mytool)
        bpy.ops.screen.animation_play()

        removeObjectProperties(obj_names);

        for idx in gene:
            bpy.context.scene.objects[object_names[idx]].location += Vector((0.0, 0.0, 50.0))

        self.resetModel(gene)

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool

        self.initialize(bpy.context.scene.objects)

        self.evaluateGene(self.gene, mytool)

        return {'FINISHED'}


class DEMOLITION_OT_reset(bpy.types.Operator):
    bl_label = "Reset"
    bl_idname = "demolition.op_reset"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool

        bpy.ops.screen.animation_cancel()
        bpy.ops.object.select_all(action='DESELECT')

        removeObjectProperties(object_names);

        return {'FINISHED'}


# required blender specific functions
classes = [MyProperties, DEMOLITION_PT_main_panel, DEMOLITION_OT_start, DEMOLITION_OT_stop, DEMOLITION_OT_initialize,
           DEMOLITION_OT_reset, DEMOLITION_OT_genetic]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        bpy.types.Scene.my_tool = bpy.props.PointerProperty(type=MyProperties)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
        del bpy.types.Scene.my_tool


if __name__ == "__main__":
    initObjectNames()
    addMaterialProperties("ground.000", materials["ground"])
    register()
