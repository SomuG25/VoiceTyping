' Voice Typing - Hidden Launcher (No Console Window)
' This VBS script runs the Python app silently in the background using the venv Python.

Set objFSO = CreateObject("Scripting.FileSystemObject")
scriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Use the venv Python (where all deps are installed)
pythonExe = scriptDir & "\.venv\Scripts\pythonw.exe"

If Not objFSO.FileExists(pythonExe) Then
    ' Fallback: try system pythonw
    Set objExec = CreateObject("WScript.Shell").Exec("where pythonw")
    pythonExe = ""
    If Not objExec.StdOut.AtEndOfStream Then
        pythonExe = Trim(objExec.StdOut.ReadLine())
    End If
    If pythonExe = "" Then
        MsgBox "Python not found! Run: .venv\Scripts\python -m pip install -r requirements.txt", vbCritical, "Voice Typing Error"
        WScript.Quit 1
    End If
End If

' Run hidden (0 = no window), don't wait for exit
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = scriptDir
WshShell.Run """" & pythonExe & """ """ & scriptDir & "\main.py""", 0, False
