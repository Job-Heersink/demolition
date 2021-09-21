import bpy
import sys

sys.path.append('/home/job/.local/lib/python3.7/site-packages')

bpy.app.debug_wm = False

materials = {"concrete": {"type":"ACTIVE","density":12,"friction":0.7}, #these values are not correct yet
            "metal":{},
            "ground": {"type":"PASSIVE","friction":1}}
            
def evaluate_demolition(scene, ideal_radius, ideal_height):
    max_radius = 0
    max_height = 0
    for obj in bpy.context.scene.objects: 
            for m in materials:
                if m == "ground":
                    continue
                if obj.name.startswith(m):
                    loc = obj.matrix_world.translation
                    max_height = max(loc[2], max_height)
                    max_radius = max(sqrt(loc[0]**2+loc[1]**2), max_radius) #todo: this treats the center of an object as its location, but in reality we want to check its edges
                    print(f"max radius {max_radius}")
                    print(f"max height {max_height}") 
                    print(obj.name+"  :  "+ str(loc))
       
    

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
                    bpy.ops.rigidbody.shape_change(type='CONVEX_HULL') #todo: maybe not mesh? its very slow
                    bpy.ops.object.modifier_add(type='COLLISION')
                    
                    if "density" in mat:
                        bpy.ops.rigidbody.mass_calculate(density=mat["density"])
                    
                    if "friction" in mat:
                        obj.rigid_body.friction = mat["friction"]
                        
                    if "restitution" in mat:
                        obj.rigid_body.restitution = mat["restitution"]
                    
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
        
        evaluate_demolition(scene,0,0)
        
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
        
        for obj in bpy.context.scene.objects: 
            for m in materials:
                if obj.name.startswith(m):
                    bpy.context.view_layer.objects.active = obj
                    obj.select_set(True)
                    
                    bpy.ops.rigidbody.object_remove()
                    bpy.ops.object.modifier_remove(modifier="Collision")
                    
                    obj.select_set(False)
                    bpy.context.view_layer.objects.active = None

        return {'FINISHED'}

# required blender specific functions
classes = [MyProperties, DEMOLITION_PT_main_panel, DEMOLITION_OT_start, DEMOLITION_OT_stop, DEMOLITION_OT_initialize, DEMOLITION_OT_reset]


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
