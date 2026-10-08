Attribute VB_Name = "modLoader"
' Carga de las cuatro hojas del Excel exportado al libro, sin interpretar los valores
' (resurtido/loader.py). El archivo de origen nunca se modifica.
Option Explicit

Private Const SIGNATURE_NAME As String = "FirmaPedidos"

' Carga el inventario de `path`. Regresa "OK <resumen>" o "ERROR: <detalle>"; no muestra
' dialogos, para que la usen el boton y la prueba de paridad. Si algo falla antes de
' escribir, la carga anterior queda igual.
Public Function LoadFrom(ByVal path As String) As String
    Dim source As Workbook, openedHere As Boolean, problem As String
    Dim sheetName As Variant, lastRows(0 To 3) As Long, i As Long, summary As String

    On Error GoTo Failed
    problem = OpenSource(path, source, openedHere)
    If Len(problem) = 0 Then problem = CheckSource(source)
    If Len(problem) > 0 Then
        CloseSource source, openedHere
        LoadFrom = "ERROR: " & problem
        Exit Function
    End If

    Application.ScreenUpdating = False
    For Each sheetName In DataSheetNames()
        lastRows(i) = CopySheet(source.Worksheets(CStr(sheetName)), CStr(sheetName))
        i = i + 1
    Next sheetName
    CloseSource source, openedHere
    ResetResults

    summary = FileName(path) & ": " & _
        CountRows(SHEET_STOCK, lastRows(0)) & " productos en Existencias, " & _
        CountRows(SHEET_LIMITS, lastRows(1)) & " en Minimos, " & _
        CountRows(SHEET_PRODUCT_SUPPLIER, lastRows(2)) & " en Producto_Proveedor y " & _
        CountRows(SHEET_SUPPLIERS, lastRows(3)) & " proveedores"
    SetStatus "StatusLoaded", summary & " (" & Format$(Now, "yyyy-mm-dd hh:nn") & ")"
    Application.ScreenUpdating = True
    LoadFrom = "OK " & summary
    Exit Function

Failed:
    problem = Err.Description
    Application.ScreenUpdating = True
    CloseSource source, openedHere
    LoadFrom = "ERROR: " & problem
End Function

Public Function HasLoadedData() As Boolean
    HasLoadedData = ThisWorkbook.Worksheets(SHEET_STOCK).Range("A1").Value <> EmptyTitle()
End Function

Public Function EmptyTitle() As String
    EmptyTitle = U("Sin datos: usa el bot\u00f3n Cargar inventario de la hoja Inicio.")
End Function

' Ultimo renglon con algun valor en las columnas de datos (al menos la fila de encabezado).
Public Function LastDataRow(ByVal ws As Worksheet, ByVal columnCount As Long) As Long
    Dim col As Long, row As Long, found As Long
    found = DATA_HEADER_ROW
    For col = 1 To columnCount
        row = ws.Cells(ws.Rows.Count, col).End(xlUp).row
        If row > found Then found = row
    Next col
    LastDataRow = found
End Function

' Si el archivo ya esta abierto en Excel se usa esa copia, siempre que no tenga cambios
' sin guardar: lo que se carga debe ser lo que esta en el disco.
Private Function OpenSource(ByVal path As String, ByRef source As Workbook, _
                            ByRef openedHere As Boolean) As String
    Dim wb As Workbook, exists As Boolean
    On Error Resume Next
    exists = Len(Dir(path)) > 0
    On Error GoTo 0
    If Not exists Then
        OpenSource = "No existe el archivo de entrada: " & path
        Exit Function
    End If

    For Each wb In Workbooks
        If StrComp(wb.FullName, path, vbTextCompare) = 0 Then
            If Not wb.Saved Then
                OpenSource = FileName(path) & U(" est\u00e1 abierto con cambios sin guardar. " & _
                    "Gu\u00e1rdalo o ci\u00e9rralo y vuelve a cargarlo.")
                Exit Function
            End If
            Set source = wb
            Exit Function
        ElseIf StrComp(wb.Name, FileName(path), vbTextCompare) = 0 Then
            OpenSource = U("Ya hay otro libro abierto con el nombre ") & wb.Name & _
                U(". Ci\u00e9rralo y vuelve a cargar el inventario.")
            Exit Function
        End If
    Next wb

    On Error Resume Next
    Application.DisplayAlerts = False
    Set source = Workbooks.Open(Filename:=path, ReadOnly:=True, UpdateLinks:=0, AddToMru:=False)
    Application.DisplayAlerts = True
    On Error GoTo 0
    If source Is Nothing Then
        OpenSource = "No se pudo leer como Excel: " & path
    Else
        openedHere = True
    End If
End Function

Private Sub CloseSource(ByVal source As Workbook, ByVal openedHere As Boolean)
    If openedHere And Not source Is Nothing Then source.Close SaveChanges:=False
End Sub

' Mismos mensajes que resurtido/cli.py y resurtido/loader.py.
Private Function CheckSource(ByVal source As Workbook) As String
    Dim sheetName As Variant, missing As String, column As Variant, ws As Worksheet
    For Each sheetName In DataSheetNames()
        If Not SheetExists(source, CStr(sheetName)) Then
            missing = missing & IIf(Len(missing) > 0, ", ", "") & sheetName
        End If
    Next sheetName
    If Len(missing) > 0 Then
        CheckSource = "Faltan hojas en el Excel: " & missing
        Exit Function
    End If
    For Each sheetName In DataSheetNames()
        Set ws = source.Worksheets(CStr(sheetName))
        missing = ""
        For Each column In DataColumns(CStr(sheetName))
            If HeaderColumn(ws, CStr(column)) = 0 Then
                missing = missing & IIf(Len(missing) > 0, ", ", "") & column
            End If
        Next column
        If Len(missing) > 0 Then
            CheckSource = "En la hoja " & sheetName & " falta la columna: " & missing
            Exit Function
        End If
    Next sheetName
End Function

Private Function SheetExists(ByVal wb As Workbook, ByVal sheetName As String) As Boolean
    Dim ws As Worksheet
    For Each ws In wb.Worksheets
        If ws.Name = sheetName Then
            SheetExists = True
            Exit Function
        End If
    Next ws
End Function

' Columna (1..n) del encabezado en la fila 2, comparando sin espacios a los lados; 0 si no esta.
Private Function HeaderColumn(ByVal ws As Worksheet, ByVal header As String) As Long
    Dim lastCol As Long, col As Long
    lastCol = ws.Cells(DATA_HEADER_ROW, ws.Columns.Count).End(xlToLeft).column
    For col = 1 To lastCol
        If Trim$(CStr(ws.Cells(DATA_HEADER_ROW, col).Value)) = header Then
            HeaderColumn = col
            Exit Function
        End If
    Next col
End Function

' Copia el titulo y las columnas esperadas, en su orden, a la hoja del libro y a su copia
' oculta, en las mismas filas que el origen. Regresa el ultimo renglon con datos.
Private Function CopySheet(ByVal source As Worksheet, ByVal sheetName As String) As Long
    Dim headers As Variant, i As Long, sourceCols() As Long, lastRow As Long, row As Long
    Dim target As Worksheet, loaded As Worksheet, values As Variant
    headers = DataColumns(sheetName)
    ReDim sourceCols(0 To UBound(headers))
    For i = 0 To UBound(headers)
        sourceCols(i) = HeaderColumn(source, CStr(headers(i)))
        row = source.Cells(source.Rows.Count, sourceCols(i)).End(xlUp).row
        If row > lastRow Then lastRow = row
    Next i
    If lastRow < DATA_HEADER_ROW Then lastRow = DATA_HEADER_ROW

    Set target = ThisWorkbook.Worksheets(sheetName)
    Set loaded = ThisWorkbook.Worksheets(LOADED_PREFIX & sheetName)
    target.Unprotect
    ClearData target
    loaded.Cells.Clear
    values = AsCellText(source.Range("A1").Value)
    target.Range("A1").Value = values
    loaded.Range("A1").Value = values
    For i = 0 To UBound(headers)
        loaded.Cells(DATA_HEADER_ROW, i + 1).Value = headers(i)
        If lastRow >= DATA_FIRST_ROW Then
            values = ColumnValues(source, sourceCols(i), lastRow)
            target.Range(target.Cells(DATA_FIRST_ROW, i + 1), target.Cells(lastRow, i + 1)).Value = values
            loaded.Range(loaded.Cells(DATA_FIRST_ROW, i + 1), loaded.Cells(lastRow, i + 1)).Value = values
        End If
    Next i
    SetEditableRows target, lastRow
    ProtectSheet target
    CopySheet = lastRow
End Function

' Valores de una columna como arreglo (filas x 1). El texto se guarda con apostrofo para
' que Excel no lo convierta: "1,250" debe seguir siendo texto, como en el archivo.
Private Function ColumnValues(ByVal ws As Worksheet, ByVal column As Long, _
                              ByVal lastRow As Long) As Variant
    Dim raw As Variant, values() As Variant, i As Long, count As Long
    count = lastRow - DATA_FIRST_ROW + 1
    ReDim values(1 To count, 1 To 1)
    If count = 1 Then
        values(1, 1) = AsCellValue(ws.Cells(DATA_FIRST_ROW, column).Value)
    Else
        raw = ws.Range(ws.Cells(DATA_FIRST_ROW, column), ws.Cells(lastRow, column)).Value
        For i = 1 To count
            values(i, 1) = AsCellValue(raw(i, 1))
        Next i
    End If
    ColumnValues = values
End Function

Public Function AsCellValue(ByVal value As Variant) As Variant
    If VarType(value) = vbString Then
        If Len(value) = 0 Then
            AsCellValue = Empty
        Else
            AsCellValue = "'" & value
        End If
    Else
        AsCellValue = value
    End If
End Function

Public Function AsCellText(ByVal value As Variant) As Variant
    AsCellText = AsCellValue(value)
    If IsEmpty(AsCellText) Then AsCellText = "'"
End Function

Private Sub ClearData(ByVal ws As Worksheet)
    ws.Range("A1").ClearContents
    ws.Range(ws.Rows(DATA_FIRST_ROW), ws.Rows(ws.Rows.Count)).ClearContents
End Sub

Private Function CountRows(ByVal sheetName As String, ByVal lastRow As Long) As Long
    Dim ws As Worksheet, row As Long, columnCount As Long
    Set ws = ThisWorkbook.Worksheets(sheetName)
    columnCount = UBound(DataColumns(sheetName)) + 1
    For row = DATA_FIRST_ROW To lastRow
        If Application.WorksheetFunction.CountA(ws.Range(ws.Cells(row, 1), _
                                                         ws.Cells(row, columnCount))) > 0 Then
            CountRows = CountRows + 1
        End If
    Next row
End Function

' Una carga nueva invalida la revision, los pedidos y los correos anteriores.
Private Sub ResetResults()
    Dim sheetName As Variant
    For Each sheetName In Array(SHEET_EXCEPTIONS, SHEET_CORRECTIONS, SHEET_SUMMARY, SHEET_DETAIL)
        ClearTable ThisWorkbook.Worksheets(CStr(sheetName))
    Next sheetName
    SetStatus "StatusReviewed", "Pendiente"
    SetStatus "StatusExceptions", "Pendiente"
    SetStatus "StatusOrders", "Pendiente"
    SetStatus "StatusEmails", "Pendiente"
    ClearSignature
End Sub

Public Function FileName(ByVal path As String) As String
    FileName = Mid$(path, InStrRev(path, Application.PathSeparator) + 1)
End Function

' --- Firma de los datos: detecta si las hojas cambiaron desde Preparar pedidos ---


' Suma de verificacion del contenido de las cuatro hojas de datos (tipo y valor de cada celda).
Public Function DataSignature() As String
    Const MODULUS As Double = 2147483629#
    Dim sheetName As Variant, ws As Worksheet, columnCount As Long, lastRow As Long
    Dim values As Variant, r As Long, c As Long, text As String, i As Long, h As Double
    Dim length As Double
    For Each sheetName In DataSheetNames()
        Set ws = ThisWorkbook.Worksheets(CStr(sheetName))
        columnCount = UBound(DataColumns(CStr(sheetName))) + 1
        lastRow = LastDataRow(ws, columnCount)
        text = sheetName & "#" & lastRow
        If lastRow >= DATA_FIRST_ROW Then
            values = ws.Range(ws.Cells(DATA_FIRST_ROW, 1), ws.Cells(lastRow, columnCount)).Value
            For r = 1 To UBound(values, 1)
                For c = 1 To columnCount
                    If IsError(values(r, c)) Then
                        text = text & "|E" & ErrorText(values(r, c))
                    Else
                        text = text & "|" & VarType(values(r, c)) & ":" & PyStr(values(r, c))
                    End If
                Next c
            Next r
        End If
        For i = 1 To Len(text)
            h = h * 31 + (AscW(Mid$(text, i, 1)) And &HFFFF&)
            h = h - Int(h / MODULUS) * MODULUS
        Next i
        length = length + Len(text)
    Next sheetName
    DataSignature = IntText(h) & "-" & IntText(length)
End Function

Public Sub SaveSignature(ByVal signature As String)
    ThisWorkbook.Names.Add Name:=SIGNATURE_NAME, RefersTo:="=""" & signature & """", Visible:=False
End Sub

Public Function StoredSignature() As String
    Dim formula As String
    On Error Resume Next
    formula = ThisWorkbook.Names(SIGNATURE_NAME).RefersTo
    On Error GoTo 0
    If Len(formula) > 3 Then StoredSignature = Mid$(formula, 3, Len(formula) - 3)
End Function

Public Sub ClearSignature()
    On Error Resume Next
    ThisWorkbook.Names(SIGNATURE_NAME).Delete
    On Error GoTo 0
End Sub
