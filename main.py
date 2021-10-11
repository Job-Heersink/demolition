import bpy
import sys
from math import radians, sqrt, cos, sin
from mathutils import Matrix, Vector

sys.path.append('/home/job/.local/lib/python3.7/site-packages')

bpy.app.debug_wm = False

materials = {"concrete": {"type": "ACTIVE", "density": 12, "friction": 0.7},  #TODO these values are not correct yet
             "metal": {"type": "ACTIVE", "density": 12, "friction": 0.7},
             "dish": {"type": "ACTIVE", "density": 5, "friction": 0.8},
             "ground": {"type": "PASSIVE", "friction": 1}}

def calc_physics(mytool):
    bpy.ops.ptcache.free_bake_all()
    bpy.context.scene.rigidbody_world.time_scale = mytool.dem_speed_float
    bpy.context.scene.rigidbody_world.substeps_per_frame = int(mytool.dem_substeps_float)
    bpy.context.scene.rigidbody_world.solver_iterations = int(mytool.dem_solver_iter_float)
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 100
    bpy.ops.ptcache.bake_all(bake=True)

# linear function
def eval(x):
        return x if x >= 0 and x <= 1 else 0
    
def find_position_sides(obj): #TODO test this for actual rotation
    xRot = obj.rotation_euler[0]
    yRot = obj.rotation_euler[1]
    zRot = obj.rotation_euler[2]
    
    xrot_matrix = Matrix.Rotation(xRot, 3, 'X')
    yrot_matrix = Matrix.Rotation(yRot, 3, 'Y')
    zrot_matrix = Matrix.Rotation(zRot, 3, 'Z')
                            
    end_point1 = Vector((0,0,obj.scale[2]))
    end_point2 = Vector((0,0,-obj.scale[2])) #add more than just the z endpoints, also add x and y.
    
    end_point1 = end_point1 @ xrot_matrix @ yrot_matrix @ zrot_matrix
    end_point2 = end_point2 @ xrot_matrix @ yrot_matrix @ zrot_matrix
    
    end_point1 = obj.matrix_world.translation+end_point1
    end_point2 = obj.matrix_world.translation+end_point2
    
    return end_point1, end_point2, obj.location
    
def find_closest_object(this_obj):
    threshold = 1
    assert(this_obj.name.startswith("hinge"))
    
    for obj in bpy.context.scene.objects:
        for m in materials:
            if m == "ground" or this_obj == obj or this_obj.parent == obj:
                continue
            
            if obj.name.startswith(m):
        
                poss = find_position_sides(obj)
                
                for p in poss:
                    if -threshold < (this_obj.matrix_world.translation-p).length < threshold:
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
    radius_eval = eval(max_radius/(hard_max_radius*2))
    height_eval = eval(max_height/(hard_max_height*2))
    
    print(f"eval radius {radius_eval}")
    print(f"eval height {height_eval}")
    
    return radius_eval, height_eval


# define the sliders of the UI window
class MyProperties(bpy.types.PropertyGroup):
        dem_threshold_float: bpy.props.FloatProperty(name="Breaking threshold", soft_min=0, soft_max=50, default=10, step=0.1,
                                               precision=2)
        dem_substeps_float: bpy.props.FloatProperty(name="Substeps Per Frame", soft_min=0, soft_max=100, default=10, step=1)
        dem_solver_iter_float: bpy.props.FloatProperty(name="Solver Iterations", soft_min=0, soft_max=100, default=10, step=1)
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
        layout.operator("demolition.op_initialize")
        layout.operator("demolition.op_reset")
        layout.prop(mytool, "dem_threshold_float")
        layout.label(text="animation")
        layout.prop(mytool, "dem_substeps_float")
        layout.prop(mytool, "dem_solver_iter_float")
        layout.prop(mytool, "dem_speed_float")
        layout.operator("demolition.op_start")
        layout.operator("demolition.op_stop")
        layout.label(text="find optimal demolition")
        layout.operator("demolition.op_genetic")


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
                bpy.context.object.rigid_body_constraint.breaking_threshold = mytool.dem_threshold_float
                
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

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool

        ##THIS IS FOR YOU SYTSE!!!
        print("insert genetic algorithm here")
        
        ##I MADE A START FOR YOU TO GET URSELF UNDERWAY
        iter = 1
        for i in range(iter):
            #remove some object from the structure
            #INSERT CODE HERE
            
            #calculate the physics using the function i made for u
            calc_physics(mytool)
            
            #goto the last frame
            bpy.context.scene.frame_set(previous_keyframe)
            
            #and evaluate
            hard_max_radius = 100 #fill these in yourself
            hard_max_height = 100 #fill these in yourself
            r,h = evaluate_demolition(scene, hard_max_radius, hard_max_height)
            
            #Do some genetic algorithm magic
            #INSERT CODE HERE
            
            #add the removed object back again
            #INSERT CODE HERE
        
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = None

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
            if obj.name.startswith("hinge"):
                bpy.context.view_layer.objects.active = obj
                obj.select_set(True)

                bpy.ops.rigidbody.constraint_remove()

                obj.select_set(False)
                bpy.context.view_layer.objects.active = None


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
classes = [MyProperties, DEMOLITION_PT_main_panel, DEMOLITION_OT_start, DEMOLITION_OT_stop, DEMOLITION_OT_initialize,
           DEMOLITION_OT_reset,DEMOLITION_OT_genetic]


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
