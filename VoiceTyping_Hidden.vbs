' Voice Typing - Hidden Launcher (No Console Window)
' This VBS script runs the Python app silently in the background
' Perfect for Windows startup

Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Get Python path
Set objExec = WshShell.Exec("where pythonw")
pythonPath = ""
If Not objExec.StdOut.AtEndOfStream Then
    pythonPath = Trim(objExec.StdOut.ReadLine())
End If

' Fallback to python if pythonw not found
If pythonPath = "" Then
    Set objExec = WshShell.Exec("where python")
    If Not objExec.StdOut.AtEndOfStream Then
        pythonPath = Trim(objExec.StdOut.ReadLine())
    End If
End If

If pythonPath = "" Then
    MsgBox "Python not found! Please install Python and add to PATH.", vbCritical, "Voice Typing Error"
    WScript.Quit 1
End If

' Run the application hidden (0 = hidden window)
scriptPath = WshShell.CurrentDirectory & "\main.py"
WshShell.Run """" & pythonPath & """ """ & scriptPath & """", 0, False
