

These files set environment variables for the render.
And they might cache plugins onto the local drive of the rrClient.


There are 2 different .rrEnv files for each render application:

1) 
The RR factory files named <renderAppLowercase>.rrEnv.

These files should NOT be changed by your company.
These files can be updated if you update RR.
If there is a new feature or if a render app or renderer requires new  environment variables, we add it.
Do NOT edit these files.


2) 
The inhouse files named <renderAppLowercase>__inhouse.rrEnv.
This file is indented for you.
Change them as you like, add what you like.
Use the application RR/bin/.../baEnvFile_Editor to edit the file (or use any text editor if you know the syntax).

If this file does not exist, just create it.
The rrClients load changed files when they start a new render job.





