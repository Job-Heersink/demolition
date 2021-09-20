import bpy
import sys

sys.path.append('/home/job/.local/lib/python3.7/site-packages')

from math import radians
from mathutils import Vector, Euler, Quaternion
from tensorflow import keras
import tensorflow as tf
import serial
import requests
import numpy as np
from threading import Thread
import time

bpy.app.debug_wm = False

# define the sliders of the UI window
class MyProperties(bpy.types.PropertyGroup):
    my_float_property: bpy.props.FloatProperty(name="Power %", soft_min=0, soft_max=100, default=50, step=2,
                                               precision=1)

# initiate the UI panel
class Demolition_PT_main_panel(bpy.types.Panel):
    bl_label = "Demolition Controller"
    bl_idname = "Demolition_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Demolition"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool

        layout.operator("demolition.op_initialize")
        layout.operator("demolition.op_start")
        layout.operator("demolition.op_stop")


class Demolition_OT_start(bpy.types.Operator):
    bl_label = "Start"
    bl_idname = "demolition.op_start"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool

        bpy.ops.object.select_all(action='DESELECT')

        return {'FINISHED'}


class Demolition_OT_stop(bpy.types.Operator):
    bl_label = "Stop"
    bl_idname = "demolition.op_stop"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool
        
        bpy.ops.object.select_all(action='DESELECT')

        return {'FINISHED'}


class Demolition_OT_initialize(bpy.types.Operator):
    bl_label = "Initialize"
    bl_idname = "demolition.op_initialize"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool

        return {'FINISHED'}


# required blender specific functions
classes = [MyProperties, Demolition_PT_main_panel, Demolition_OT_start, Demolition_OT_stop, Demolition_OT_initialize]


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
