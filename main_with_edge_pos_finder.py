import bpy
import sys
from math import radians, sqrt, cos, sin
from mathutils import Matrix, Vector

sys.path.append('/home/job/.local/lib/python3.7/site-packages')

bpy.app.debug_wm = False

materials = {"concrete": {"type": "ACTIVE", "density": 12, "friction": 0.7},  #TODO these values are not correct yet
             "metal": {"type": "ACTIVE", "density": 12, "friction": 0.7},
             "ground": {"type": "PASSIVE", "friction": 1}}

def eval(x):
    if x >= 0 and x <= 1:
        return -0.5*(2*x-1)**3+0.5
    else:
        return 0
    
def find_position_sides(obj):
    xRot = obj.rotation_euler[0]
    yRot = obj.rotation_euler[1]
    zRot = obj.rotation_euler[2]
    
    xrot_matrix = Matrix(   Vector((1,0,0)),
                            Vector((0, cos(xRot), -sin(xRot))),
                            Vector((0, sin(xRot), cos(xRot))))
    yrot_matrix = Matrix(   Vector(( cos(yRot), 0, sin(yRot))),
                            Vector(( 0, 1, 0))
                            Vector((-sin(yRot),0,cos(yRot))))
    zrot_matrix = Matrix(   Vector(( cos(zRot), sin(zRot), 0)),
                            Vector(( -sin(zRot), cos(zRot), 0)),
                            Vector((0,0,1)))
                            
    end_point1 = Vector(0,0,obj.scale[2]/2)
    end_point2 = Vector(0,0,-obj.scale[2]/2) #add more than just the z endpoints, also add x and y.
    
    end_point1 = end_point1*xrot_matrix*yrot_matrix*zrot_matrix
    end_point2 = end_point2*xrot_matrix*yrot_matrix*zrot_matrix
    
    end_point1 = obj.location+end_point1
    end_point2 = obj.location+end_point2
    
    print(end_point1)
    print(end_point2)
    
    return end_point1, end_point2, obj.location
    
def find_closest_object(this_obj):
    threshold = 0.1
    
    for obj in bpy.context.scene.objects:
        if this_obj == obj:
            continue
        
        poss = find_position_sides(obj)
        
        for p in poss:
            if -threshold < (this_obj.location-p).length < threshold:
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
    radius_eval = eval(max_radius/hard_max_radius)
    height_eval = eval(max_height/hard_max_height)
    
    print(f"eval radius {radius_eval}")
    print(f"eval height {height_eval}")
    
    return (radius_eval+height_eval)/2
    
    #print(bpy.ops.mesh.primitive_circle_add(location=(0,0,0.01), radius=max_radius))
    
    


# define the sliders of the UI window
class MyProperties(bpy.types.PropertyGroup):
    my_float_property: bpy.props.FloatProperty(name="Power %", soft_min=0, soft_max=100, default=50, step=2,
                                               precision=1)


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
        layout.operator("demolition.op_initialize")
        layout.operator("demolition.op_reset")
        layout.label(text="animation")
        layout.operator("demolition.op_start")
        layout.operator("demolition.op_stop")


class DEMOLITION_OT_initialize(bpy.types.Operator):
    bl_label = "Initialize"
    bl_idname = "demolition.op_initialize"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool
        bpy.ops.object.select_all(action='DESELECT')

        for obj in bpy.context.scene.objects:
            for m in materials:
                if obj.name.startswith(m):
                    mat = materials[m]
                    bpy.context.view_layer.objects.active = obj
                    obj.select_set(True)

                    bpy.ops.rigidbody.object_add(type=mat["type"] if mat["type"] else "ACTIVE")
                    bpy.ops.rigidbody.shape_change(type='CONVEX_HULL')  # todo: maybe not mesh? its very slow
                    bpy.ops.object.modifier_add(type='COLLISION')

                    if "density" in mat:
                        bpy.ops.rigidbody.mass_calculate(density=mat["density"])

                    if "friction" in mat:
                        obj.rigid_body.friction = mat["friction"]

                    if "restitution" in mat:
                        obj.rigid_body.restitution = mat["restitution"]
                
            if obj.name.startswith("hinge"):
                bpy.context.view_layer.objects.active = obj
                obj.select_set(True)
                
                bpy.ops.rigidbody.constraint_add()
                bpy.context.object.rigid_body_constraint.type = 'HINGE'
                bpy.context.object.rigid_body_constraint.disable_collisions = False
                bpy.context.object.rigid_body_constraint.use_breaking = True
                bpy.context.object.rigid_body_constraint.object1 = obj.parent
                next_paired_obj = find_closest_object(obj)
                if next_paired_obj is not None:
                    bpy.context.object.rigid_body_constraint.object2 = next_paired_obj
                bpy.context.object.rigid_body_constraint.breaking_threshold = 3
                
            obj.select_set(False)
            bpy.context.view_layer.objects.active = None

        return {'FINISHED'}


class DEMOLITION_OT_start(bpy.types.Operator):
    bl_label = "Start"
    bl_idname = "demolition.op_start"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool

        bpy.ops.object.select_all(action='DESELECT')
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


class DEMOLITION_OT_reset(bpy.types.Operator):
    bl_label = "Reset"
    bl_idname = "demolition.op_reset"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool

        bpy.ops.screen.animation_cancel()
        bpy.ops.object.select_all(action='DESELECT')
        
        to_be_deleted = []

        for obj in bpy.context.scene.objects:
            for m in materials:
                if obj.name.startswith(m):
                    bpy.context.view_layer.objects.active = obj
                    obj.select_set(True)

                    bpy.ops.rigidbody.object_remove()
                    bpy.ops.object.modifier_remove(modifier="Collision")
                    
            if obj.name.startswith("hinge"):
                bpy.context.view_layer.objects.active = obj
                obj.select_set(True)

                bpy.ops.rigidbody.constraint_remove()

                obj.select_set(False)
                bpy.context.view_layer.objects.active = None


        return {'FINISHED'}


# required blender specific functions
classes = [MyProperties, DEMOLITION_PT_main_panel, DEMOLITION_OT_start, DEMOLITION_OT_stop, DEMOLITION_OT_initialize,
           DEMOLITION_OT_reset]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        bpy.types.Scene.my_tool = bpy.props.PointerProperty(type=MyProperties)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
        del bpy.types.Scene.my_tool


if __name__ == "__main__":
    register()
