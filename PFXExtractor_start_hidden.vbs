Option Explicit

Dim fso
Dim shell
Dim projectDir
Dim workDir
Dim logFile
Dim serverLog
Dim command

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

projectDir = fso.GetParentFolderName(WScript.ScriptFullName)
workDir = projectDir & "\work"
logFile = workDir & "\startup.log"
serverLog = workDir & "\server.log"

If Not fso.FolderExists(workDir) Then
    fso.CreateFolder(workDir)
End If

command = "%ComSpec% /c " & _
    """cd /d """ & projectDir & """ && " & _
    "echo [%date% %time%] Startup check >> """ & logFile & """ && " & _
    "netstat -ano | findstr "":7862"" | findstr ""LISTENING"" >nul && " & _
    "(echo [%date% %time%] PFX Extractor already running on port 7862. >> """ & logFile & """) || " & _
    "(echo [%date% %time%] Starting PFX Extractor... >> """ & logFile & """ && " & _
    """.venv\Scripts\python.exe"" ""app_local.py"" >> """ & serverLog & """ 2>&1)" & _
    """"

shell.Run command, 0, False
