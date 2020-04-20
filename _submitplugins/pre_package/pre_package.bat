@echo off
rem Package submitplugins to application bundle

echo --- Rhino Installer
set rhinoSubmitDir=%~dp0\rrSubmit_Rhino_5.0+ {1bd0715b-307c-4050-b28d-2018e53cffd3}\dev
set rhinoSubmitRhi=%~dp0\..\rrSubmit_Rhino_5.0+.rhi

del "%rhinoSubmitRhi%" >nul 2>&1
powershell.exe -nologo -noprofile -command "& { Add-Type -A 'System.IO.Compression.FileSystem'; [IO.Compression.ZipFile]::CreateFromDirectory('%rhinoSubmitDir%', '%rhinoSubmitRhi%'); }
echo     ..\rrSubmit_Rhino_5.0+.rhi
