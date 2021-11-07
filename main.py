import bpy
import sys
import time
from random import seed
from random import randint
from random import random
from math import radians, sqrt, cos, sin
from mathutils import Matrix, Vector
import os

sys.path.append('/home/job/.local/lib/python3.7/site-packages')

bpy.app.debug_wm = False

materials = {
    "metal": {"type": "ACTIVE", "density": 7500, "friction": 0.42, "collision_shape": "CONVEX_HULL"},
    "dish": {"type": "ACTIVE", "density": 2710, "friction": 1.4, "collision_shape": "CONVEX_HULL"},
    "ground": {"type": "PASSIVE", "friction": 1}}

max_chromosome_size = 10
# pool_size must be a mutiple of 4 due to function mutatechromosomes()
chromosome_pool_size = 8
chromosomes_idxs = [[]] * chromosome_pool_size
chromosome_fitness = [0] * chromosome_pool_size
generation = 0

accept_new_block = 0.8
mutation_rate = 0.35

hinge_set = []
displayed_demolition = []
physics_added = False


def init_hinge_set():
    """
    set the global hinge_set list to contain all the hinge object names
    """

    for obj in bpy.context.scene.objects:
        if obj.name.startswith("hinge"):
            hinge_set.append(obj.name)


def get_hinge_set_idx(hinge_name):
    """
    get the index of the hinge_name in the global hinge_set list

    :param hinge_name: name of the index that is returned
    :return: index of the hinge_name
    """

    for idx in range(0, len(hinge_set)):
        if hinge_name == hinge_set[idx]:
            return idx

    return -1


def calc_physics(mytool):
    """
    computes the animation of the current configuration.
    """

    bpy.ops.ptcache.free_bake_all()
    bpy.context.scene.rigidbody_world.time_scale = mytool.dem_speed_float
    bpy.context.scene.rigidbody_world.substeps_per_frame = int(mytool.dem_substeps_float)
    bpy.context.scene.rigidbody_world.solver_iterations = int(mytool.dem_solver_iter_float)
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 100
    bpy.ops.ptcache.bake_all(bake=True)


def get_closest_hinges(hinge_idx):
    """
    computes the hinges close to the hinge of hinge_idx. These hinges should be
    within a radius of 1 distance unit.

    :param hinge_idx: idx of the hinge to consider
    :return: a list with indexes of hinges close to the hinge with hinge_idx
    """

    hinge = bpy.context.scene.objects[hinge_set[hinge_idx]]

    radius = 0.5
    closest_hinges = []
    for obj in bpy.context.scene.objects:
        if obj.name.startswith("hinge"):
            delta_x = hinge.matrix_world.translation[0] - obj.matrix_world.translation[0]
            delta_y = hinge.matrix_world.translation[1] - obj.matrix_world.translation[1]
            delta_z = hinge.matrix_world.translation[2] - obj.matrix_world.translation[2]

            dist = sqrt(delta_x ** 2 + delta_y ** 2 + delta_z ** 2)
            if dist < radius:
                closest_hinges.append(get_hinge_set_idx(obj.name))

    return closest_hinges


def find_position_sides(obj):
    """
    find the position of the outermost ends of the object

    :param obj: the object to find the sides for
    :return: the location of the sides
    """

    x_rot = obj.rotation_euler[0]
    y_rot = obj.rotation_euler[1]
    z_rot = obj.rotation_euler[2]

    x_rot_matrix = Matrix.Rotation(x_rot, 3, 'X')
    y_rot_matrix = Matrix.Rotation(y_rot, 3, 'Y')
    z_rot_matrix = Matrix.Rotation(z_rot, 3, 'Z')

    end_point1 = Vector((0, 0, obj.scale[2]))
    end_point2 = Vector((0, 0, -obj.scale[2]))  # add more than just the z endpoints, also add x and y.

    end_point1 = end_point1 @ x_rot_matrix @ y_rot_matrix @ z_rot_matrix
    end_point2 = end_point2 @ x_rot_matrix @ y_rot_matrix @ z_rot_matrix

    end_point1 = obj.matrix_world.translation + end_point1
    end_point2 = obj.matrix_world.translation + end_point2

    return end_point1, end_point2, obj.location


def find_closest_object(this_obj):
    """
    get the neurest neighbour of the given object

    :param obj: the object to find the neighbour of
    :return: the neighbouring object
    """

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
def evaluate_demolition(removed_clusters, w_r=3, w_h=5, w_d=1, hard_max_removed_clusters=36, hard_max_radius=50,
                        hard_max_height=50):
    """
    evaluates the demolition of the current selected frame

    :param w_d: weight factor for imploded objects
    :param w_h: weight factor for height
    :param w_r: weight factor for radius
    :param removed_clusters: number of objects that were removed in the simulation
    :param hard_max_removed_clusters: maximum number of objects that can be removed in the simulation
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
                                 max_radius)

    r_norm = max_radius / hard_max_radius
    h_norm = max_height / hard_max_height
    d_norm = removed_clusters / hard_max_removed_clusters
    r_norm = 1 if r_norm > 1 else r_norm
    h_norm = 1 if h_norm > 1 else h_norm
    d_norm = 1 if d_norm > 1 else d_norm

    print(f"r{max_radius}")
    print(f"h {max_height}")
    print(f"d {removed_clusters}")
    print(f"r_norm {r_norm}")
    print(f"h_norm {h_norm}")
    print(f"d_norm {d_norm}")

    result = (w_r * (1 - r_norm) + w_h * (1 - h_norm) ** 3 + w_d * (1 - d_norm)) / (w_r + w_h + w_d)
    return result


def add_physics_all_object(breaking_threshold):
    """
    set the appropriate physics properties to each object in the scene

    :param breaking_threshold: The threshold to which the hinges should break
    """

    global physics_added
    for obj in bpy.context.scene.objects:
        bpy.ops.object.select_all(action='DESELECT')
        for m_key in materials:
            if obj.name.startswith(m_key):
                add_material_properties(obj.name, materials[m_key])
                break
        bpy.ops.object.select_all(action='DESELECT')

    for obj in bpy.context.scene.objects:
        bpy.ops.object.select_all(action='DESELECT')
        if obj.name.startswith("hinge"):
            add_hinge_properties(obj.name, breaking_threshold)

        bpy.ops.object.select_all(action='DESELECT')

    physics_added = True


def remove_physics_all_object():
    """
    removes the physics of all objects
    """

    global physics_added
    for obj in bpy.context.scene.objects:
        bpy.ops.object.select_all(action='DESELECT')
        for m_key in materials:
            if obj.name.startswith(m_key):
                remove_material_properties(obj.name)
                break

    for obj in bpy.context.scene.objects:
        bpy.ops.object.select_all(action='DESELECT')
        if obj.name.startswith("hinge"):
            remove_hinge_properties(obj.name)
        bpy.ops.object.select_all(action='DESELECT')

    physics_added = False


def add_material_properties(object_name, mat):
    """
    adds the appropriate physics properties to an object with name object_name according to its material,
    which is specified in the name itself. If an object starts with the name 'metal' we will give it metal properties.

    :param object_name: The name of the object to apply physics properties to.
    :param mat: the material to apply to the object
    """

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
        bpy.ops.rigidbody.mass_calculate(material='Custom', density=mat["density"])

    if "friction" in mat:
        obj.rigid_body.friction = mat["friction"]

    if "restitution" in mat:
        obj.rigid_body.restitution = mat["restitution"]

    obj.select_set(False)
    bpy.context.view_layer.objects.active = None


def add_hinge_properties(object_name, breaking_threshold):
    """
    add physics properties to the given hinge

    :param object_name: the hinge object
    :param breaking_threshold: the breaking threshold of the hinge
    """

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
    bpy.context.object.rigid_body_constraint.breaking_threshold = breaking_threshold

    obj.select_set(False)
    bpy.context.view_layer.objects.active = None


def remove_material_properties(object_name):
    """
    remove the physics properties of an object

    :param object_name: name of the object
    :return:
    """
    obj = bpy.context.scene.objects[object_name]
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bpy.ops.rigidbody.object_remove()
    bpy.ops.object.modifier_remove(modifier="Collision")

    obj.select_set(False)
    bpy.context.view_layer.objects.active = None


def remove_hinge_properties(object_name):
    """
    remove the physics properties of a hinge

    :param object_name: name of the hinge
    :return:
    """
    obj = bpy.context.scene.objects[object_name]
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bpy.ops.rigidbody.constraint_remove()

    obj.select_set(False)
    bpy.context.view_layer.objects.active = None


def random_chromosome():
    """
    Generates a random chromosome based on some global parameters. A chromosome
    contains a number of hinge clusters(genes) that are removed from the
    standard model.

    :param max_chromosome_size: the maximum number of hinge clusters that are removed
    :param accept_new_block: a threshold for which random block are accepted
    :return: a chromosome, a list of hinge clusters.
    """
    chromosome = []
    for idx in range(0, max_chromosome_size):
        if random() < accept_new_block:
            not_in_chromosome = True
            obj_idx = randint(0, len(hinge_set) - 1)
            for idxs in chromosome:
                if obj_idx in idxs:
                    not_in_chromosome = False

            if not_in_chromosome:
                chromosome.append(get_closest_hinges(obj_idx))
    print(chromosome)
    return chromosome


def crossover(parent1, parent2):
    """
    Generates a new chromosome based on the 2 parent chromosomes. It randomly
    selects genes from the first or second parents and puts these together in
    the new chromosome

    :param parent1: first parent used in the crossover
    :param parent2: second parent used in the crossover
    :return: a new chromosome base on parent1 and parent2
    """
    chromosome = []
    max_size = max(len(parent1), len(parent2))
    for idx in range(0, max_size):
        if random() < 0.5:
            if idx < len(parent1):
                chromosome.append(parent1[idx])
        else:
            if idx < len(parent2):
                chromosome.append(parent2[idx])
    return chromosome


def random_mutations(chromosome):
    """
    Randomly mutates the input chromosome. By replacing a gene based on the
    global parameter mutation_rate.

    :param chromosome: chromosome that is mutated
    :return: a new mutated chromosome based
    """
    new_chromosome = []
    for idx in range(0, len(chromosome)):
        if random() < mutation_rate:
            while True:
                obj_idx = randint(0, len(hinge_set) - 1)
                not_in_chromosome = True
                for idxs in chromosome:
                    if obj_idx in idxs:
                        not_in_chromosome = False

                if not_in_chromosome:
                    chromosome.append(get_closest_hinges(obj_idx))
                    break
        else:
            new_chromosome.append(chromosome[idx])
    return new_chromosome


def init_chromosomes():
    """
    creates a pool of random chromosomes and saves them in the global parameter
    chromosomes_idxs
    """

    for chromosome_idx in range(0, chromosome_pool_size):
        chromosomes_idxs[chromosome_idx] = random_chromosome()


def mutate_chromosomes():
    """
    This function will mutate the current pool of chromosomes. It has 4
    different mutation strategies that all come up with an equal number of new
    chromosomes.
    1. Take the two best chromosomes in the pool and create children using the
    crossover function.
    2. Take the two best chromosomes in the pool and create children using the
    crossover function but also perform random mutations on these children.
    3. Create new random chromosomes
    4. Use the two best chromosomes in the pool and mutate those.

    The new chromosomes are saved in the global variable chromosomes_idxs.
    """
    global chromosomes_idxs
    score_dict = {}
    for idx in range(0, len(chromosome_fitness)):
        score_dict[idx] = chromosome_fitness[idx]

    sorted_dict = sorted(score_dict.items(), key=lambda item: item[1], reverse=True)
    parent1 = chromosomes_idxs[sorted_dict[0][0]]
    parent2 = chromosomes_idxs[sorted_dict[1][0]]

    new_chromosomes = []
    for x in range(0, chromosome_pool_size // 2):
        new_chromosome = crossover(parent1, parent2)
        if x % 2:
            new_chromosome = random_mutations(new_chromosome)
        new_chromosomes.append(new_chromosome)

    for x in range(0, chromosome_pool_size // 4):
        new_chromosomes.append(random_chromosome())

    for x in range(0, chromosome_pool_size // 4):
        if x % 2:
            new_chromosomes.append(random_mutations(parent1))
        else:
            new_chromosomes.append(random_mutations(parent2))

    chromosomes_idxs = new_chromosomes


def remove_physics_hinge(hinge_idxs):
    for i in hinge_idxs:
        remove_hinge_properties(hinge_set[i])


def add_physics_hinge(hinge_idxs, my_tool):
    for i in hinge_idxs:
        add_hinge_properties(hinge_set[i], my_tool.dem_threshold_float)


def evaluate_chromosome(chromosome, context):
    """
    Runs the simulations of a single chromosome and evaluates it.

    :param chromosome: the chromosome that is evaluated.
    :return : The fitness score of the chromosome
    """
    scene = context.scene
    # ensure there are no duplicates in the list
    chromosome_1d = list(dict.fromkeys(sum(chromosome, [])))

    bpy.context.scene.frame_set(frame=0)
    remove_physics_hinge(chromosome_1d)
    calc_physics(scene.my_tool)

    bpy.context.scene.frame_set(frame=98)
    score = evaluate_demolition(len(chromosome))

    bpy.context.scene.frame_set(frame=0)
    # add_physics_hinge(chromosome_1d, scene.my_tool)
    add_physics_all_object(scene.my_tool.dem_threshold_float)

    return score


def run_generation(context):
    """
    Runs the simulations of a single generation of chromosomes and evaluates
    those.
    """
    global generation
    print("run generation " + str(generation))
    if generation == 0:
        init_chromosomes()
    else:
        mutate_chromosomes()

    global chromosome_fitness

    for idx in range(0, chromosome_pool_size):
        chromosome_fitness[idx] = evaluate_chromosome(chromosomes_idxs[idx], context)

    generation += 1

    # print results
    avg_score = 0
    min_score = 1
    max_score = 0
    print("chromosome scores:")
    for fitness in chromosome_fitness:
        min_score = min(min_score, fitness)
        max_score = max(max_score, fitness)
        avg_score += fitness
        print(fitness)

    avg_score = avg_score / len(chromosome_fitness)

    print("avg: " + str(avg_score))
    print("min: " + str(min_score))
    print("max: " + str(max_score))

    return {"avg": avg_score, "min": min_score, "max": max_score}


# define the sliders of the UI window
class MyProperties(bpy.types.PropertyGroup):
    dem_threshold_float: bpy.props.FloatProperty(name="Breaking threshold", soft_min=0, soft_max=10000, default=4000,
                                                 step=1)
    dem_substeps_float: bpy.props.FloatProperty(name="Substeps Per Frame", soft_min=0, soft_max=100, default=30, step=1)
    dem_solver_iter_float: bpy.props.FloatProperty(name="Solver Iterations", soft_min=0, soft_max=100, default=30,
                                                   step=1)
    dem_speed_float: bpy.props.FloatProperty(name="Speed", soft_min=0, soft_max=10, default=3, step=0.1, precision=2)


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


# blender start button
class DEMOLITION_OT_start(bpy.types.Operator):
    bl_label = "Run best model"
    bl_idname = "demolition.op_start"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool

        global displayed_demolition
        if len(displayed_demolition) == 0:
            bpy.context.scene.frame_set(frame=0)
            bpy.ops.object.select_all(action='DESELECT')
            best_score = -10000
            index = -1
            for idx in range(0, len(chromosome_fitness)):
                if (best_score < chromosome_fitness[idx]):
                    best_score = chromosome_fitness[idx]
                    index = idx

            # otherwise there is no good score
            assert (index != -1)

            displayed_demolition = sum(chromosomes_idxs[index].copy(), [])
            print(f"chr: {chromosomes_idxs[index]}")
            print(f"disp: {displayed_demolition}")

            bpy.context.scene.frame_set(frame=0)
            remove_physics_hinge(displayed_demolition)

            calc_physics(mytool)

            bpy.context.scene.frame_set(frame=0)
            add_physics_hinge(displayed_demolition, scene.my_tool)

        print(f"disp ready: {displayed_demolition}")
        bpy.ops.screen.animation_play()

        return {'FINISHED'}


# blender stop button
class DEMOLITION_OT_stop(bpy.types.Operator):
    bl_label = "Stop"
    bl_idname = "demolition.op_stop"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool

        bpy.ops.screen.animation_cancel(restore_frame=False)
        bpy.ops.object.select_all(action='DESELECT')
        global displayed_demolition, hinge_set
        print(f"displayed_demolition: {displayed_demolition}")
        bpy.context.scene.frame_set(frame=99)
        score = evaluate_demolition(7)
        for idx in displayed_demolition:
            print(hinge_set[idx])
            objectToSelect = bpy.data.objects[hinge_set[idx]]
            objectToSelect.select_set(True)

        return {'FINISHED'}


# Genetic round button
class DEMOLITION_OT_genetic_round(bpy.types.Operator):
    bl_label = "Genetic Round"
    bl_idname = "demolition.op_genetic_round"

    def execute(self, context):
        global displayed_demolition
        global physics_added

        scene = context.scene
        mytool = scene.my_tool

        bpy.context.scene.frame_set(frame=0)
        if len(displayed_demolition) != 0:
            bpy.ops.screen.animation_cancel()
            bpy.ops.object.select_all(action='DESELECT')
            add_physics_hinge(displayed_demolition, mytool)
            displayed_demolition = []

        add_physics_all_object(mytool.dem_threshold_float)

        run_generation(context)

        return {'FINISHED'}


# genetic algorithm button
class DEMOLITION_OT_genetic(bpy.types.Operator):
    bl_label = "Genetic algorithm"
    bl_idname = "demolition.op_genetic"

    def execute(self, context):
        global physics_added
        global displayed_demolition

        scene = context.scene
        mytool = scene.my_tool
        bpy.context.scene.frame_set(frame=0)
        if len(displayed_demolition) != 0:
            bpy.ops.screen.animation_cancel()
            bpy.ops.object.select_all(action='DESELECT')
            add_physics_hinge(displayed_demolition, mytool)
            displayed_demolition = []

        add_physics_all_object(mytool.dem_threshold_float)
        results = []
        for x in range(0, 10):
            results.append(run_generation(context))
        print(results)

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
    init_hinge_set()
    add_material_properties("ground.000", materials["ground"])
    register()
