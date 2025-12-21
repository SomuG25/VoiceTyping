# Create shortcut in Windows Startup folder
$WshShell = New-Object -ComObject WScript.Shell
$StartupPath = [System.Environment]::GetFolderPath('Startup')
$ShortcutPath = Join-Path $StartupPath "VoiceTyping.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "E:\Ai agents\VoiceTyping\VoiceTyping_Hidden.vbs"
$Shortcut.WorkingDirectory = "E:\Ai agents\VoiceTyping"
$Shortcut.Description = "Voice Typing"
$Shortcut.Save()

Write-Host "SUCCESS! Shortcut created at: $ShortcutPath"
Write-Host ""
Write-Host "Voice Typing will now start automatically when you log into Windows!"
