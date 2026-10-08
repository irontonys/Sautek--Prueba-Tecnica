Attribute VB_Name = "Constructor"
' Arma excel/Resurtido.xlsm a partir de los modulos de excel/vba. Solo para desarrollo:
' vive en excel/tools/constructor.xlsm y lo ejecuta excel/build.py.
' Necesita "Confiar en el acceso al modelo de objetos de proyectos de VBA".
' Sin acentos: el editor de VBA no importa bien UTF-8.
Option Explicit

Private Const TARGET_NAME As String = "Resurtido.xlsm"
Private Const XL_OPEN_XML_WORKBOOK_MACRO_ENABLED As Long = 52

' Regresa "OK <ruta>" o "ERROR: <detalle>"; nunca deja un dialogo abierto.
Public Function Build(ByVal excelDir As String) As String
    Dim sep As String, vbaDir As String, target As String
    Dim modules As Collection, item As Variant, wb As Workbook
    sep = Application.PathSeparator
    vbaDir = excelDir & sep & "vba"
    target = excelDir & sep & TARGET_NAME

    On Error GoTo Failed
    Set modules = ModuleFiles(vbaDir, sep)
    If modules.Count = 0 Then
        Build = "ERROR: no hay modulos .bas en " & vbaDir
        Exit Function
    End If
    If Not GrantAccess(excelDir, vbaDir, target, modules) Then
        Build = "ERROR: Excel no tiene permiso para leer " & excelDir
        Exit Function
    End If
    CloseIfOpen TARGET_NAME

    Application.DisplayAlerts = False
    Set wb = Workbooks.Add
    For Each item In modules
        wb.VBProject.VBComponents.Import CStr(item)
    Next item
    Application.Run "'" & wb.Name & "'!modWorkbook.BuildWorkbook"
    wb.SaveAs Filename:=target, FileFormat:=XL_OPEN_XML_WORKBOOK_MACRO_ENABLED
    wb.Close SaveChanges:=False
    Application.DisplayAlerts = True
    Build = "OK " & target
    Exit Function

Failed:
    Build = "ERROR: " & Err.Description & " (" & Err.Number & ")"
    Application.DisplayAlerts = False
    If Not wb Is Nothing Then wb.Close SaveChanges:=False
    Application.DisplayAlerts = True
End Function

' Dir con comodines no funciona en Mac: se listan todos y se filtra por extension.
Private Function ModuleFiles(ByVal folder As String, ByVal sep As String) As Collection
    Dim found As New Collection, name As String
    name = Dir(folder & sep)
    Do While Len(name) > 0
        If LCase$(Right$(name, 4)) = ".bas" Then found.Add folder & sep & name
        name = Dir()
    Loop
    Set ModuleFiles = found
End Function

' Excel para Mac corre en sandbox: pide permiso una vez para la carpeta y los archivos.
Private Function GrantAccess(ByVal excelDir As String, ByVal vbaDir As String, _
                             ByVal target As String, ByVal modules As Collection) As Boolean
#If Mac Then
    Dim paths() As String, i As Long, item As Variant
    ReDim paths(0 To modules.Count + 2)
    paths(0) = excelDir
    paths(1) = vbaDir
    paths(2) = target
    i = 3
    For Each item In modules
        paths(i) = CStr(item)
        i = i + 1
    Next item
    GrantAccess = GrantAccessToMultipleFiles(paths)
#Else
    GrantAccess = True
#End If
End Function

Private Sub CloseIfOpen(ByVal name As String)
    Dim wb As Workbook
    For Each wb In Workbooks
        If StrComp(wb.Name, name, vbTextCompare) = 0 Then
            wb.Close SaveChanges:=False
            Exit Sub
        End If
    Next wb
End Sub
