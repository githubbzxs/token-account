Option Explicit

Dim i, cmd, shell

If WScript.Arguments.Count < 1 Then
  MsgBox "Missing batch file path argument.", vbExclamation, "open-report"
  WScript.Quit 1
End If

cmd = """" & WScript.Arguments(0) & """"
For i = 1 To WScript.Arguments.Count - 1
  cmd = cmd & " """ & Replace(WScript.Arguments(i), """", """""") & """"
Next

Set shell = CreateObject("WScript.Shell")
shell.Run cmd, 0, False
