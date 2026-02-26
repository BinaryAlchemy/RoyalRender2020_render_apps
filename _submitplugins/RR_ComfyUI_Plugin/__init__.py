# Royal Render Plugin for ComfyUI
# Author: Royal Render, Holger Schoenberger, Binary Alchemy
# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy
#
# Installation:
# Please copy the RR_ComfyUI_Plugin folder into your custom_nodes folder of ComfyUI.
# Note: If the RR_ROOT environment variable ist not defined (created when installing something via rrWorkstationInstaller), 
# then you need to edit the function "def getRR_Root()" top update the path to RR.
#


from . import rrWorkflow
from . import rrSubmit
from . import rrNodes
from server import PromptServer
from aiohttp import web
import asyncio
import traceback
import sys



@PromptServer.instance.routes.post("/rr/submit")
async def submit_handler(request):
    try:
        data = await request.json()
        workflowHybrid = data.get("workflow") # This is the dict from the browser
        filename = data.get("filename", "unknown_workflow")
        submit_node_id = data.get("submit_node_id", -1)

        # Safety Fallback: Check if UI mode is even possible
        # It is not possible if the Comfy webserver is located "in the basement" and I am at my workstation.
        client_ip = request.remote   # Get the IP address of the user's browser
        is_local = client_ip in ("127.0.0.1", "localhost", "::1")  # Check if the user is local (Workstation)
        settings = rrSubmit.get_workflow_settings(workflowHybrid["ui"], rrSubmit.getRR_Root())
        if settings.get("ui_submit") and not is_local:
            raise Exception(
                f"UI rrSubmitter is only available if the Comfy webserver runs on your Workstation (Localhost). "
                f"Your access via an other machine {client_ip} requires Commandline mode."
            )


        # Use run_in_executor to prevent the 10-second EXE call 
        # from freezing the entire ComfyUI server.
        loop = asyncio.get_event_loop()
        
        # Execute your existing function in a separate thread
        result = await loop.run_in_executor(
            None, rrSubmit.submit_workflow, workflowHybrid, filename, submit_node_id
        )
        submit_success, processed_workflow = result

        # Prepare the base response
        response_data = {
            "status": "success" if submit_success else "error",
            "message": "Job processed successfully." if submit_success else "Submission failed."
        }

        # Only attach the workflow if the user setting is enabled
        if settings.get("load_farm_workflow", False):
            print("[rrSubmit-submit_handler] Adding workflow to response")
            response_data["workflow"] = processed_workflow
        else:
            print("[rrSubmit-submit_handler] No workflow requested")

        return web.json_response(
            response_data, 
            status=200 if submit_success else 500
        )

    except Exception as e:
        error_msg = str(e)
        if "Line:" in error_msg:
            pass
        else:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            line_number = exc_tb.tb_lineno
            func_name = exc_tb.tb_frame.f_code.co_name
            error_details = f"Error: {e} | Line: {line_number} | Function: {func_name}"
            error_msg=f"[rrSubmit] submit_job_to_royalrender failed:  {error_details}"
            full_stack = traceback.format_exc()
            print(error_msg)
            print(f"[rrSubmit-submit_handler] FULL DEBUG STACK:\n{full_stack}")
        
        return web.json_response({
            "status": "error", 
            "message": str(error_msg)
        }, status=500)
    
#send settings struct to webserver/JS
@PromptServer.instance.routes.get("/rr/get_schema")
async def get_schema_handler(request):
    try:
        schema = []
        for key, info in rrSubmit.SETTINGS_FIELDS.items():
            schema.append({
                "id": key,
                "label": info.get("label", key),
                "type": info.get("type", "str"),
                "choices": info.get("choices", []),
                "default": rrWorkflow.settings_compute_default(key, rrSubmit.getRR_Root()),
                "section": info.get("section", "left") 
            })
        
        print(f"[rrSubmit] API: Sending schema with {len(schema)} fields.")
        return web.json_response(schema)
    except Exception as e:
        print(f"[rrSubmit] API Error: {str(e)}")
        return web.json_response([])
    
    
# Den Endpoint registrieren
@PromptServer.instance.routes.post("/royalrender/add_seed")
async def add_seed_endpoint(request):
    json_data = await request.json()
    workflow = json_data.get("workflow")
    
    # Deine Logik ausführen
    modified_workflow = rrSubmit.add_rrSeed(workflow)
    
    return web.json_response(modified_workflow)

    

# This tells ComfyUI to look into the 'js' folder and serve it to the browser
WEB_DIRECTORY = "./js"

NODE_CLASS_MAPPINGS = rrNodes.NODE_CLASS_MAPPINGS
NODE_DISPLAY_NAME_MAPPINGS = rrNodes.NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
