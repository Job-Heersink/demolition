import bpy
import sys
import time
from random import seed
from random import randint
from random import random
from math import radians, sqrt, cos, sin
from mathutils import Matrix, Vector

sys.path.append('/home/job/.local/lib/python3.7/site-packages')

bpy.app.debug_wm = False

materials = {#"concrete": {"type": "ACTIVE", "density": 7500, "friction": 0.7,"collision_shape": "CONVEX_HULL"},  #TODO these values are not correct yet
             "metal": {"type": "ACTIVE", "density": 7500, "friction": 0.42,"collision_shape": "CYLINDER"},
             "dish": {"type": "ACTIVE", "density": 2710, "friction": 1.4,"collision_shape": "CONVEX_HULL"},
             "ground": {"type": "PASSIVE", "friction": 1}}

max_gene_size = 15
gene_pool_size = 4
gene_pool = [[]] * gene_pool_size
gene_fitness = [0] * gene_pool_size
generation = 0

accept_new_block = 0.6
mutation_rate = 0.35

object_names = []
displayed_demolition = []

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

def calc_physics(mytool):
    bpy.ops.ptcache.free_bake_all()
    bpy.context.scene.rigidbody_world.time_scale = mytool.dem_speed_float
    bpy.context.scene.rigidbody_world.substeps_per_frame = int(mytool.dem_substeps_float)
    bpy.context.scene.rigidbody_world.solver_iterations = int(mytool.dem_solver_iter_float)
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 300
    bpy.ops.ptcache.bake_all(bake=True)

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
def evaluate_demolition(imploded_objects, hard_max_imploded_objects, hard_max_radius, hard_max_height=50):
    """
    evaluates the demolition of the current selected frame

    :param imploded_objects: number of objects that were removed in the simulation
    :param hard_max_imploded_objects: maximum number of objects that can be removed in the simulation
    :param hard_max_radius: maximum demolition radius.
    :param hard_max_height: maximum height of the building (default is the height of the building aka 50 meters)
    :return: the resulting evaluation between [0,1]
    """
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

    r_norm = max_radius / hard_max_radius
    h_norm = max_height / hard_max_height
    d_norm = imploded_objects / hard_max_imploded_objects

    result = ((1-r_norm)+(1-h_norm)**3+(1-d_norm))/3
    return result

def addMaterialProperties(object_name, mat):
    obj = bpy.context.scene.objects[object_name]
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.rigidbody.object_add(type=mat["type"] if mat["type"] else "ACTIVE")
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

# assumes that the obj_names are sorted such that all hinges are at the back
# of the list
def setObjectProperties(obj_names, breaking_threshold):
    bpy.ops.object.select_all(action='DESELECT')
    for object_name in obj_names:
        if object_name.startswith("dis"):
            addMaterialProperties(object_name, materials["dish"])
        elif object_name.startswith("metal"):
            addMaterialProperties(object_name, materials["metal"])
        else:
            addHingeProperies(object_name, breaking_threshold)

    bpy.ops.object.select_all(action='DESELECT')

# assumes that the obj_names are sorted such that all hinges are at the front
# of the list
def removeObjectProperties(obj_names):
    bpy.ops.object.select_all(action='DESELECT')

    for object_name in obj_names:
        if object_name.startswith("dish"):
            removeMaterialProperties(object_name)
        elif object_name.startswith("metal"):
            removeMaterialProperties(object_name)
        else:
            removeHingeProperties(object_name)

    bpy.ops.object.select_all(action='DESELECT')

def randomGene():
    gene = []
    for idx in range(0, max_gene_size):
        if random() > accept_new_block:
            objIdx = randint(0, len(object_names) - 1)
            if objIdx not in gene:
                gene.append(objIdx)
    return gene

def crossover(parent1, parent2):
    gene = []
    maxSize = max(len(parent1), len(parent2))
    for idx in range(0, maxSize):
        if random() < 0.5:
            if idx < len(parent1):
                gene.append(parent1[idx])
        else:
            if idx < len(parent2):
                gene.append(parent2[idx])
    return gene

def randomMutations(gene):
    newGene = []
    for idx in range(0, len(gene)):
        if random() < mutation_rate:
            while True:
                objIdx = randint(0, len(object_names) - 1)
                if objIdx not in newGene and objIdx not in gene:
                    newGene.append(objIdx)
                    break
        else:
            newGene.append(gene[idx])
    return newGene

def initGenes():
    for gene_idx in range(0, gene_pool_size):
        gene_pool[gene_idx] = randomGene()

def mutateGenes():
    scoreDict = {}
    for idx in range(0, len(gene_fitness)):
        scoreDict[idx] = gene_fitness[idx]

    sortedDict =  sorted(scoreDict.items(), key=lambda item: item[1])
    parent1 = gene_pool[sortedDict[0][0]]
    parent2 = gene_pool[sortedDict[1][0]]

    newGenes = []
    for x in range(0, gene_pool_size // 2):
        newGene = crossover(parent1, parent2)
        if x % 2:
            newGene = randomMutations(newGene)
        newGenes.append(newGene)

    for x in range(0, gene_pool_size // 4):
        newGenes.append(randomGene())

    for x in range(0, gene_pool_size // 4):
        if x % 2:
            newGenes.append(randomMutations(parent1))
        else:
            newGenes.append(randomMutations(parent2))

    return newGenes


def calculateSetup(setupIdxs, mytool):
    obj_names = object_names.copy()

    for idx in setupIdxs:
        bpy.context.scene.objects[object_names[idx]].location += Vector((0.0, 0.0, -50.0))
        obj_names.remove(object_names[idx])

    setObjectProperties(obj_names, mytool.dem_threshold_float);

    calc_physics(mytool)

def resetSetup(setupIdxs):
    obj_names = object_names.copy()

    for idx in setupIdxs:
        obj_names.remove(object_names[idx])

    obj_names.reverse()
    removeObjectProperties(obj_names);

    for idx in setupIdxs:
        bpy.context.scene.objects[object_names[idx]].location += Vector((0.0, 0.0, 50.0))


def evaluateGene(gene, context):
    scene = context.scene

    calculateSetup(gene, scene.my_tool)

    bpy.context.scene.frame_set(frame = 198)
    score = evaluate_demolition(len(gene), max_gene_size, 50, 5)

    resetSetup(gene)

    return score

def runGeneration(context):
    global generation
    print("run generation " + str(generation))
    if generation == 0:
        initGenes()
    else:
        mutateGenes()

    global gene_fitness

    for idx in range(0, gene_pool_size):
        print("evaluating gene " + str(idx))
        gene_fitness[idx] = evaluateGene(gene_pool[idx], context)

    generation += 1

    # print results
    avg_score = 0
    min_score = 1
    print("gene scores:")
    for fitness in gene_fitness:
        min_score = min (min_score, fitness)
        avg_score += fitness
        print(fitness)

    avg_score = avg_score / len(gene_fitness)

    print("avg: " + str(avg_score))
    print("min: " + str(min_score))


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

        layout.label(text="parameters")
        layout.prop(mytool, "dem_threshold_float")
        layout.label(text="animation")
        layout.prop(mytool, "dem_substeps_float")
        layout.prop(mytool, "dem_solver_iter_float")
        layout.prop(mytool, "dem_speed_float")
        layout.label(text="find optimal demolition")
        layout.operator("demolition.op_genetic")
        layout.operator("demolition.op_genetic_round")
        layout.label(text="control animation")
        layout.operator("demolition.op_start")
        layout.operator("demolition.op_stop")

class DEMOLITION_OT_start(bpy.types.Operator):
    bl_label = "Run best model"
    bl_idname = "demolition.op_start"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool

        global displayed_demolition
        if len(displayed_demolition) == 0:
            bpy.context.scene.frame_set(frame = 0)
            bpy.ops.object.select_all(action='DESELECT')
            best_score = 10000
            index = -1
            for idx in range(0, len(gene_fitness)):
                if (best_score > gene_fitness[idx]):
                    best_score = gene_fitness[idx]
                    index = idx

            # otherwise there is no good score
            assert(index != -1)

            displayed_demolition = gene_pool[index].copy()

            calculateSetup(displayed_demolition, mytool)


        bpy.ops.screen.animation_play()

        return {'FINISHED'}


class DEMOLITION_OT_stop(bpy.types.Operator):
    bl_label = "Stop"
    bl_idname = "demolition.op_stop"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool

        bpy.ops.screen.animation_cancel(restore_frame=False)
        bpy.ops.object.select_all(action='DESELECT')

        return {'FINISHED'}


class DEMOLITION_OT_genetic_round(bpy.types.Operator):
    bl_label = "Genetic Round"
    bl_idname = "demolition.op_genetic_round"


    def execute(self, context):
        bpy.context.scene.frame_set(frame = 0)
        global displayed_demolition
        if len(displayed_demolition) != 0:
            bpy.ops.screen.animation_cancel()
            bpy.ops.object.select_all(action='DESELECT')
            resetSetup(displayed_demolition)
            displayed_demolition = []

        runGeneration(context)

        return {'FINISHED'}


class DEMOLITION_OT_genetic(bpy.types.Operator):
    bl_label = "Genetic algorithm"
    bl_idname = "demolition.op_genetic"

    def execute(self, context):
        bpy.context.scene.frame_set(frame = 0)
        global displayed_demolition
        if len(displayed_demolition) != 0:
            bpy.ops.screen.animation_cancel()
            bpy.ops.object.select_all(action='DESELECT')
            resetSetup(displayed_demolition)
            displayed_demolition = []

        for x in range(0, 10):
            runGeneration(context)

        return {'FINISHED'}


# required blender specific functions
classes = [MyProperties, DEMOLITION_PT_main_panel, DEMOLITION_OT_start, DEMOLITION_OT_stop,
           DEMOLITION_OT_genetic, DEMOLITION_OT_genetic_round]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        bpy.types.Scene.my_tool = bpy.props.PointerProperty(type=MyProperties)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
        del bpy.types.Scene.my_tool


if __name__ == "__main__":
    seed(1)
    initObjectNames()
    addMaterialProperties("ground.000", materials["ground"])
    register()
