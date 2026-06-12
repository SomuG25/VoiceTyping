' File Transcriber - Hidden Launcher (No Console Window)
' Opens the File Transcriber UI directly (standalone, no tray needed).
' Uses the same faster-whisper backend as the Voice Typing app.

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
        MsgBox "Python not found! Please run: .venv\Scripts\python -m pip install -r requirements.txt", vbCritical, "File Transcriber Error"
        WScript.Quit 1
    End If
End If

Dim targetScript
targetScript = scriptDir & "\file_transcriber_ui.py"

If Not objFSO.FileExists(targetScript) Then
    MsgBox "file_transcriber_ui.py not found in:" & vbCrLf & scriptDir, vbCritical, "File Transcriber Error"
    WScript.Quit 1
End If

' Run hidden (0 = no console window), don't wait for exit
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = scriptDir
WshShell.Run """" & pythonExe & """ """ & targetScript & """", 0, False
