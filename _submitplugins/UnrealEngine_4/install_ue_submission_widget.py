import os
import unreal
from shutil import copyfile


def install_ue_wdg():
    """Install the widget from the plugin path to current UE project directory"""
    
    try:
        rr_root = os.environ["RR_ROOT"]
    except KeyError:
        unreal.log_error("Could not locate RR_ROOT, please check RR_Install")
        dialog = unreal.EditorDialog()
        dialog.show_message("RR_ROOT not found", "Please check RR_Install", unreal.AppMsgType.OK)
        return
    
    bp_file_name = "RR_Utils.uasset"

    plugin_path = os.path.join(rr_root, "render_apps", "_submitplugins", "UnrealEngine_4", "Content", bp_file_name)

    prj_dir = unreal.SystemLibrary().get_project_directory()
    plugin_copy_path = os.path.join(prj_dir, "Content", bp_file_name)
    plugin_copy_path = os.path.normpath(plugin_copy_path)

    if not os.path.isfile(plugin_copy_path):
        copyfile(plugin_path, plugin_copy_path)

    if not os.path.isfile(plugin_copy_path):
        unreal.log_error("Could not copy RR submission blueprint to Game, please contact support")
        dialog = unreal.EditorDialog()
        dialog.show_message("Failed to copy RR_Utils", "Could not copy RR submission blueprint to Game, please contact support")
        return

    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(True)

    split_name = os.path.splitext(bp_file_name)[0]
    asset_path = f"/Game/{split_name}"
    
    checked = unreal.EditorAssetLibrary.does_asset_exist(asset_path)
    
    if not checked:
        unreal.log_warning(f"'{asset_path}' RR submission blueprint copied to Game, but not found in Content. Please restart UE editor and re-execute")
        dialog = unreal.EditorDialog()
        dialog.show_message("RR Asset not found", "RR submission blueprint copied to Game, but not found in Content. Please restart UE editor and re-execute", unreal.AppMsgType.OK)
        return

    asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
    asset =  asset_data.get_asset()
    subsystem = unreal.EditorUtilitySubsystem()
    subsystem.spawn_and_register_tab(asset)


if __name__ == '__main__':
    install_ue_wdg()
