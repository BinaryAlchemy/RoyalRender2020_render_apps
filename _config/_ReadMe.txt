This folder contains all render commandline for all applications that are supported by RR.


CHANGE SETTINGS:
There are two options to change settings.
No matter which way you choose, you should leave the files in the folder as they are.
Place your files into the folder render_apps\_config_inhouse\ instead.
That is a twin folder.
If there is any filename that exists in this folder \_config\ and in \_config_inhouse\, 
then the one in \_config_inhouse\ overwrites the file in \_config\.

1) Add/overwrite settings.
All render config files have a setting line to include __inhouse files.
They are read just as if they are inside the render config file.
You can add any rrJob setting or other render config file setting in your inhouse file.
If a settings existed in the original config file, it is overwritten.

2) Some settings like commandline cannot be changed via inhouse files.
You could only add commandline, but not overwrite other ones.
In this special case, copy the render config from this folder into the _config_inhouse and do your changes.



MODIFICATIONS:
If you want to change any custom default setting (The syntax is the same as in the submitter defaults files), please use .inc file.
This way you will keep getting updates for the render config, but you keep your settings for the submission.
At the end of each render config you will find at least 2 include files for your inhouse changes:
The file 3D02__Maya2009__Arnold.cfg has for examples these includes:
::include(3D02__Maya____global_kso.inc)    #1) Settings for all Maya render configs. 
::include(r_Arnold.inc)                    #2) Arnold specific settings
::include(3D00__3D_global.inc)             #3) Settings for all 3D apps
::include(<ConfigFileName>__inhouse.inc)   #4) Your inhouse file to override settings for this render app and renderer only

Note that include lines 1-3 have include lines of their own.
So if you want to change for example some setting for all Maya jobs, then the file 3D02__Maya____global_kso.inc has this include line:
::include(3D02__Maya____global_kso__inhouse.inc)
If you want to change settings for all 3D jobs, then 3D00__3D_global.inc has the include line:
::include(<ConfigFileName>__inhouse.inc)


"*.inc" include files:
An include file is inserted into a render config at the exact location of the include command. (You can even include in the middle of a line)
Comment lines starting with # are deleted before insert (Exception: They have a [ in the line).


CREATE NEW RENDER CONFIG:
If you want to create a new one, please check rrHelp section Customization / Renderer / 



