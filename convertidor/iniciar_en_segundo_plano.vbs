' Arranca el servidor SIN ventana negra. Lo usa el inicio automatico de Windows.
' Requiere haber abierto iniciar.bat al menos una vez (para crear el entorno).
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
q = Chr(34)
base = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Convertidor"
py = base & "\venv\Scripts\python.exe"
registro = base & "\servidor.log"

If Not fso.FileExists(py) Then
  MsgBox "Primero abri iniciar.bat una vez para preparar la app.", 48, "Convertidor"
  WScript.Quit 1
End If

sh.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run "cmd /c " & q & q & py & q & " server.py > " & q & registro & q & " 2>&1" & q, 0, False
