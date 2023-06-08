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

    if v_major > 2 or v_minor > 79:
        prefs = bpy.context.preferences
    else:
        prefs = bpy.context.user_preferences

    cycles_prefs = prefs.addons['cycles'].preferences

    # Attempt to set GPU device types if available
    for compute_device_type in ('CUDA', 'OPENCL', 'OPTIX', 'HIP', 'ONEAPI', 'NONE'):
        try:
            cycles_prefs.compute_device_type = compute_device_type
            break
        except TypeError:
            print("Failed to enable gpu")
            raise

    # Enable all CPU and GPU devices
    print("GPU set to", cycles_prefs.compute_device_type)

    if v_major > 2:
        cycles_prefs.refresh_devices()
        devices = cycles_prefs.devices
        for device in devices:
            if device.type == 'CPU':
                continue
            print("\tenabling device", device.name)
            device.use = True
    else:
        devices = cycles_prefs.get_devices(bpy.context)
        for device in devices:
            for dev_entry in device:
                print("\tenabling device", dev_entry.name)
                dev_entry.use = True


if __name__ == "__main__":
    print("RR %rrVersion% - enable cycles GPU at startup")
    enable_gpu_devices()
