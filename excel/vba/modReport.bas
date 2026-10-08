Attribute VB_Name = "modReport"
' Salidas en el formato del programa de Python (resurtido/report.py), para la prueba de paridad.
Option Explicit

Public Const EXCEPTIONS_FILE As String = "excepciones.csv"

Private Const COLOR_CORRECTED As Long = 14348258  ' RGB(226, 239, 218)
Private Const COLOR_WARNING As Long = 13431551    ' RGB(255, 242, 204)
Private Const COLOR_EXCLUDED As Long = 14083324   ' RGB(252, 228, 214)
Private Const COLOR_PURCHASE As Long = 16247773   ' RGB(221, 235, 247)
Private Const COLOR_EDITABLE As Long = 13434879   ' RGB(255, 255, 204)
Private Const MONEY_FORMAT As String = """$""#,##0.00"

' Mismo archivo que write_exceptions: UTF-8 con BOM y las columnas de EXCEPTION_COLUMNS.
Public Sub WriteExceptionsCsv(ByVal folder As String)
    Dim text As String, i As Long
    text = CsvLine(Array("hoja", "fila_excel", "codigo", "tipo", "detalle", "valor_original", "decision"))
    For i = 1 To ExceptionCount
        With Exceptions(i)
            text = text & CsvLine(Array(.Hoja, CStr(.Fila), .Codigo, U(.Tipo), .Detalle, .Valor, _
                                        DecisionText(.Tipo)))
        End With
    Next i
    WriteUtf8File JoinPath(folder, EXCEPTIONS_FILE), text, True
End Sub

' Pedidos en CSV con las columnas de pedidos.xlsx (hojas Resumen y Detalle), para la prueba.
Public Sub WriteOrdersCsv(ByVal folder As String)
    Dim summary As String, detail As String, i As Long, k As Long, line As OrderLine
    summary = CsvLine(SummaryColumns())
    detail = CsvLine(DetailColumns())
    For i = 1 To OrderCount
        With Orders(i)
            summary = summary & CsvLine(Array(Suppliers(.SupplierIndex).Id, _
                Suppliers(.SupplierIndex).Nombre, Suppliers(.SupplierIndex).Correo, _
                CStr(.LineCount), MoneyText(.Total, False), _
                NumberText(Suppliers(.SupplierIndex).PedidoMinimo), U(.Estado)))
            For k = .FirstLine To .FirstLine + .LineCount - 1
                line = OrderLines(k)
                With Products(line.ProductIndex)
                    detail = detail & CsvLine(Array(Suppliers(Orders(i).SupplierIndex).Id, _
                        Suppliers(Orders(i).SupplierIndex).Nombre, .Codigo, .Descripcion, _
                        NumberText(.Existencia), NumberText(.Minimo), NumberText(.Maximo), _
                        CStr(.Multiplo), CStr(line.Cantidad), NumberText(.Costo), _
                        MoneyText(line.Importe, False), U(Orders(i).Estado), _
                        IIf(.Revisar, U("S\u00ed"), "")))
                End With
            Next k
        End With
    Next i
    WriteUtf8File JoinPath(folder, "resumen.csv"), summary, True
    WriteUtf8File JoinPath(folder, "detalle.csv"), detail, True
End Sub

Private Function NumberText(ByVal value As Double) As String
    If value = Int(value) Then NumberText = IntText(value) Else NumberText = FloatRepr(value)
End Function

' --- Hojas Excepciones y Correcciones (boton Revisar datos) ---


' Reescribe la hoja Excepciones con la ultima validacion: un renglon por excepcion, su
' grupo con color y un enlace a la celda del problema.
Public Sub WriteExceptionsSheet()
    Dim ws As Worksheet, values() As Variant, i As Long, columnCount As Long
    Set ws = ThisWorkbook.Worksheets(SHEET_EXCEPTIONS)
    ClearTable ws
    ws.Unprotect
    columnCount = UBound(ExceptionColumns()) + 1
    If ExceptionCount > 0 Then
        ReDim values(1 To ExceptionCount, 1 To columnCount)
        For i = 1 To ExceptionCount
            With Exceptions(i)
                values(i, 1) = AsCellText(.Hoja)
                values(i, 2) = .Fila
                values(i, 3) = AsCellText(.Codigo)
                values(i, 4) = AsCellText(U(.Tipo))
                values(i, 5) = AsCellText(.Detalle)
                values(i, 6) = AsCellText(.Valor)
                values(i, 7) = AsCellText(DecisionText(.Tipo))
                values(i, 8) = AsCellText(U(ExceptionGroup(.Tipo)))
            End With
        Next i
        Trace "excepciones: escribir valores"
        ws.Range(ws.Cells(2, 1), ws.Cells(ExceptionCount + 1, columnCount)).Value = values
        Trace "excepciones: valores escritos"
        For i = 1 To ExceptionCount
            With Exceptions(i)
                Trace "excepciones: renglon " & i & " color"
                ws.Range(ws.Cells(i + 1, 1), ws.Cells(i + 1, columnCount)).Interior.Color = _
                    GroupColor(ExceptionGroup(.Tipo))
                Trace "excepciones: renglon " & i & " enlace"
                ws.Hyperlinks.Add Anchor:=ws.Cells(i + 1, columnCount), Address:="", _
                    SubAddress:=CellReference(.Hoja, .Fila, TargetColumn(.Hoja, .Tipo)), _
                    TextToDisplay:="Ir a la celda"
            End With
        Next i
        Trace "excepciones: alineacion"
        ws.Range(ws.Cells(2, 1), ws.Cells(ExceptionCount + 1, columnCount)).VerticalAlignment = xlTop
        Trace "excepciones: filtro"
        AddFilter ws.Range(ws.Cells(1, 1), ws.Cells(ExceptionCount + 1, columnCount))
    End If
    ProtectSheet ws
End Sub

' El filtro es una comodidad: si Excel no lo permite (pasa en Mac), se omite sin detener nada.
Private Sub AddFilter(ByVal table As Range)
    On Error Resume Next
    table.AutoFilter
    If Err.Number <> 0 Then Trace "filtro omitido: " & Err.Description
    On Error GoTo 0
End Sub

Public Function GroupColor(ByVal grupo As String) As Long
    Select Case grupo
        Case GROUP_CORRECTED: GroupColor = COLOR_CORRECTED
        Case GROUP_WARNING: GroupColor = COLOR_WARNING
        Case GROUP_PURCHASE: GroupColor = COLOR_PURCHASE
        Case Else: GroupColor = COLOR_EXCLUDED
    End Select
End Function

' Columna de la celda que causo la excepcion, para el enlace "Ir a la celda".
Public Function TargetColumn(ByVal hoja As String, ByVal tipo As String) As Long
    TargetColumn = 1
    Select Case hoja
        Case SHEET_STOCK
            Select Case tipo
                Case EXISTENCIA_TEXTO, EXISTENCIA_NO_NUMERICA, EXISTENCIA_VACIA, EXISTENCIA_NEGATIVA
                    TargetColumn = 3
                Case UNIDAD_INCONSISTENTE, POSIBLE_DUPLICADO
                    TargetColumn = 2
                Case PRODUCTO_INACTIVO
                    TargetColumn = 5
            End Select
        Case SHEET_LIMITS
            If tipo = MINIMO_INVALIDO Or tipo = MINIMO_MAYOR_MAXIMO Then TargetColumn = 2
        Case SHEET_PRODUCT_SUPPLIER
            Select Case tipo
                Case PROVEEDOR_INEXISTENTE: TargetColumn = 2
                Case COSTO_INVALIDO: TargetColumn = 3
                Case MULTIPLO_INVALIDO: TargetColumn = 4
            End Select
        Case SHEET_SUPPLIERS
            Select Case tipo
                Case CORREO_INVALIDO: TargetColumn = 3
                Case PEDIDO_MINIMO_INVALIDO, PEDIDO_MINIMO_NO_ALCANZADO: TargetColumn = 4
            End Select
    End Select
End Function

Private Function CellReference(ByVal sheetName As String, ByVal row As Long, ByVal column As Long) As String
    CellReference = "'" & sheetName & "'!" & _
        ThisWorkbook.Worksheets(sheetName).Cells(row, column).Address(False, False)
End Function

' Reescribe la hoja Correcciones comparando cada hoja de datos contra su copia oculta
' de cuando se cargo. Regresa cuantas celdas cambiaron.
Public Function WriteCorrectionsSheet() As Long
    Dim ws As Worksheet, sheetName As Variant, found As New Collection, item As Variant
    Dim values() As Variant, i As Long, c As Long
    For Each sheetName In DataSheetNames()
        CompareSheet CStr(sheetName), found
    Next sheetName

    Set ws = ThisWorkbook.Worksheets(SHEET_CORRECTIONS)
    ClearTable ws
    ws.Unprotect
    If found.Count > 0 Then
        ReDim values(1 To found.Count, 1 To 5)
        i = 0
        For Each item In found
            i = i + 1
            For c = 1 To 5
                values(i, c) = AsCellText(item(c - 1))
            Next c
        Next item
        ws.Range(ws.Cells(2, 1), ws.Cells(found.Count + 1, 5)).Value = values
        AddFilter ws.Range(ws.Cells(1, 1), ws.Cells(found.Count + 1, 5))
    End If
    ProtectSheet ws
    WriteCorrectionsSheet = found.Count
End Function

Private Sub CompareSheet(ByVal sheetName As String, ByVal found As Collection)
    Dim ws As Worksheet, loaded As Worksheet, columnCount As Long, lastRow As Long
    Dim current As Variant, original As Variant, r As Long, c As Long, code As String
    Set ws = ThisWorkbook.Worksheets(sheetName)
    Set loaded = ThisWorkbook.Worksheets(LOADED_PREFIX & sheetName)
    columnCount = UBound(DataColumns(sheetName)) + 1
    lastRow = Application.Max(LastDataRow(ws, columnCount), LastDataRow(loaded, columnCount))
    If lastRow < DATA_FIRST_ROW Then Exit Sub
    current = ws.Range(ws.Cells(DATA_FIRST_ROW, 1), ws.Cells(lastRow, columnCount)).Value
    original = loaded.Range(loaded.Cells(DATA_FIRST_ROW, 1), loaded.Cells(lastRow, columnCount)).Value
    For r = 1 To UBound(current, 1)
        For c = 1 To columnCount
            If Not SameValue(current(r, c), original(r, c)) Then
                code = DisplayValue(current(r, 1))
                If Len(code) = 0 Then code = DisplayValue(original(r, 1))
                found.Add Array(sheetName, _
                    ws.Cells(DATA_FIRST_ROW + r - 1, c).Address(False, False), code, _
                    DisplayValue(original(r, c)), DisplayValue(current(r, c)))
            End If
        Next c
    Next r
End Sub

' Igualdad estricta: el texto "4" y el numero 4 son distintos, como para Python.
Private Function SameValue(ByVal a As Variant, ByVal b As Variant) As Boolean
    If IsError(a) Then a = ErrorText(a)
    If IsError(b) Then b = ErrorText(b)
    If IsEmptyValue(a) Or IsEmptyValue(b) Then
        SameValue = IsEmptyValue(a) And IsEmptyValue(b)
    ElseIf IsNum(a) And IsNum(b) Then
        SameValue = CDbl(a) = CDbl(b)
    ElseIf VarType(a) <> VarType(b) Then
        SameValue = False
    Else
        SameValue = a = b
    End If
End Function

Private Function IsEmptyValue(ByVal value As Variant) As Boolean
    If IsEmpty(value) Then
        IsEmptyValue = True
    ElseIf VarType(value) = vbString Then
        IsEmptyValue = Len(value) = 0
    End If
End Function

Private Function DisplayValue(ByVal value As Variant) As String
    If IsError(value) Then
        DisplayValue = ErrorText(value)
    Else
        DisplayValue = PyStr(value)
    End If
End Function

' --- Hojas Resumen y Detalle (boton Preparar pedidos) ---

' Escribe Resumen y Detalle con el ultimo calculo. En Detalle la cantidad es valor editable;
' el importe, el total por proveedor y su estado son formulas que se recalculan solas.
Public Sub WriteOrderSheets()
    Dim summary As Worksheet, detail As Worksheet, i As Long, k As Long, row As Long
    Dim summaryRows As Long, lastDetail As Long, item As OrderLine
    Set summary = ThisWorkbook.Worksheets(SHEET_SUMMARY)
    Set detail = ThisWorkbook.Worksheets(SHEET_DETAIL)
    ClearTable summary
    ClearTable detail
    summary.Unprotect
    detail.Unprotect
    detail.Cells.FormatConditions.Delete

    row = 1
    For i = 1 To OrderCount
        With Orders(i)
            For k = .FirstLine To .FirstLine + .LineCount - 1
                item = OrderLines(k)
                row = row + 1
                With Products(item.ProductIndex)
                    detail.Cells(row, 1).Value = AsCellText(Suppliers(Orders(i).SupplierIndex).Id)
                    detail.Cells(row, 2).Value = AsCellText(Suppliers(Orders(i).SupplierIndex).Nombre)
                    detail.Cells(row, 3).Value = AsCellText(.Codigo)
                    detail.Cells(row, 4).Value = AsCellText(.Descripcion)
                    detail.Cells(row, 5).Value = .Existencia
                    detail.Cells(row, 6).Value = .Minimo
                    detail.Cells(row, 7).Value = .Maximo
                    detail.Cells(row, 8).Value = .Multiplo
                    detail.Cells(row, 9).Value = item.Cantidad
                    detail.Cells(row, 10).Value = .Costo
                    detail.Cells(row, 11).Formula = "=ROUND(ROUND(J" & row & ",2)*I" & row & ",2)"
                    detail.Cells(row, 12).Formula = "=IFERROR(INDEX(" & QuotedSheet(SHEET_SUMMARY) & _
                        "!G:G,MATCH(A" & row & "," & QuotedSheet(SHEET_SUMMARY) & "!A:A,0)),"""")"
                    If .Revisar Then detail.Cells(row, 13).Value = U("S\u00ed")
                End With
            Next k
        End With
    Next i
    lastDetail = row

    For i = 1 To OrderCount
        row = i + 1
        With Suppliers(Orders(i).SupplierIndex)
            summary.Cells(row, 1).Value = AsCellText(.Id)
            summary.Cells(row, 2).Value = AsCellText(.Nombre)
            summary.Cells(row, 3).Value = AsCellText(.Correo)
            summary.Cells(row, 6).Value = .PedidoMinimo
        End With
        summary.Cells(row, 4).Formula = "=COUNTIFS(" & DetailColumn("A") & ",A" & row & "," & _
            DetailColumn("I") & ","">0"")"
        summary.Cells(row, 5).Formula = "=ROUND(SUMIF(" & DetailColumn("A") & ",A" & row & "," & _
            DetailColumn("K") & "),2)"
        summary.Cells(row, 7).Formula = "=IF(D" & row & "=0,""" & U(SIN_PRODUCTOS) & """,IF(E" & _
            row & "<ROUND(F" & row & ",2),""" & U(NO_SE_ENVIA) & """,""" & U(SE_ENVIA) & """))"
    Next i
    summaryRows = OrderCount + 1

    If summaryRows > 1 Then
        summary.Range(summary.Cells(2, 5), summary.Cells(summaryRows, 6)).NumberFormat = MONEY_FORMAT
        AddFilter summary.Range(summary.Cells(1, 1), summary.Cells(summaryRows, 7))
    End If
    If lastDetail > 1 Then
        detail.Range(detail.Cells(2, 10), detail.Cells(lastDetail, 11)).NumberFormat = MONEY_FORMAT
        With detail.Range(detail.Cells(2, 9), detail.Cells(lastDetail, 9))
            .Locked = False
            .Interior.Color = COLOR_EDITABLE
            .FormatConditions.Add Type:=xlExpression, Formula1:="=MOD(I2,H2)<>0"
            .FormatConditions(1).Interior.Color = COLOR_EXCLUDED
        End With
        AddFilter detail.Range(detail.Cells(1, 1), detail.Cells(lastDetail, 13))
    End If
    ProtectSheet summary
    ProtectSheet detail
End Sub

Private Function QuotedSheet(ByVal sheetName As String) As String
    QuotedSheet = "'" & sheetName & "'"
End Function

Private Function DetailColumn(ByVal letter As String) As String
    DetailColumn = QuotedSheet(SHEET_DETAIL) & "!" & letter & ":" & letter
End Function
