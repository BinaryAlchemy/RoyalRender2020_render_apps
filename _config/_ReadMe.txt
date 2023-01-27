This folder contains all render commandline for all applications that are supported by RR.

Versions:
3D01__Softimage__2011.cfg is not for Softimage 2011 only.
It is for Softimage 2011+, 2011 and up.  This means RR uses this config file for Softimage 2011.5, 2012, 2012.5, 2013, 2014, 2015, ...


render_apps\_config_inhouse\:
There is a twin folder _config_inhouse.
We highly recommend that you save all new or changed files in that folder.
The only reason is to keep this folder clean and it is waaaay easier for you to see what you have changed.



Modifications:
If you want to change any custom default setting (The syntax is the same as in the submitter defaults files), please use .inc file.
This way you will keep getting updates for the render config, but you keep your settings for the submission.
At the end of each render config you will find at least 2 include files for your inhouse changes:
::include(3D01__Softimage____global_inhouse.inc)
::include(<ConfigFileName>_inhouse.inc)

3D01__Softimage____global_inhouse.inc
   A global file from RR with all shared settings of this application, no matter the renderer:
<ConfigFileName>_inhouse.inc:
   A file for this render config only. <ConfigFileName> will be replaced by the name of the render config file (even if you use it in an include file)
   In this case the filename would be 3D01__Softimage__2011_inhouse.inc


If it does not exist, please create it.
As with all settings in a render config, the rule for two times the same setting is:
What comes at last, takes the place.


"*.inc" include files:
An include file is inserted into a render config at the exact location of the include command. (You can even include in the middle of a line)
Comment lines starting with # are deleted before insert (Exception: They have a [ in the line).



Create new render config:
If you want to create a new one, please check rrHelp section Customization / Renderer / 



