Set ws = CreateObject("WScript.Shell")
ws.Run Chr(34) & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\shells\start.bat" & Chr(34), 0, False
