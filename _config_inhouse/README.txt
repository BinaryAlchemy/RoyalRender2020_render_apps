
This folder required an RR ver 9 license.

The intention of this folder is to make it easier for you to track changes that you have made to render configurations.
No need to change anything in the main _config folder, place all new .cfg files and _inhouse.inc files into here.

How does it work:
This folder is handled exactly the same as the /_config folder.
It does not matter if you place a file into the /_config or into this /_config_inhouse folder.
These folders are joined into one folder before RR reads the config files.

Special note:
If the same filename exists in /_config and /_config_inhouse, the one in /_config_inhouse  "overwrites" the one in /_config (in the memory of the RR application).