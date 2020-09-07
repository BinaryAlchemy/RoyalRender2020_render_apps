#python
# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Settings script for Blender
# Author:  Royal Render, Paolo Acampora
# Last Change: %rrVersion%
# 
######################################################################

import bpy


def enable_gpu_devices():
    v_major, v_minor, _ = bpy.app.version

    if v_major != 2:
        print("RR - GPU auto enable: blender {0} not supported".format(v_major))
        return

    if v_minor > 79:
        prefs = bpy.context.preferences
    else:
        prefs = bpy.context.user_preferences

    cprefs = prefs.addons['cycles'].preferences

    # Attempt to set GPU device types if available
    for compute_device_type in ('CUDA', 'OPENCL', 'NONE'):
        try:
            cprefs.compute_device_type = compute_device_type
            break
        except TypeError:
            print("Failed to enable gpu")
            raise

    # Enable all CPU and GPU devices
    print("GPU set to", cprefs.compute_device_type)

    for device in cprefs.get_devices(bpy.context):
        for dev_entry in device:
            print("\tenabling device", dev_entry.name)
            dev_entry.use = True


if __name__ == "__main__":
    print("RR - enable cycles GPU at startup")
    enable_gpu_devices()
