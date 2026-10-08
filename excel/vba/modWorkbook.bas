Attribute VB_Name = "modWorkbook"
' Hojas, formatos, botones y proteccion del libro. BuildWorkbook lo ejecuta excel/build.py
' al armarlo; los demas modulos usan los nombres de hoja y las columnas de aqui.
Option Explicit

Public Const APP_TITLE As String = "Resurtido semanal"

Public Const SHEET_HOME As String = "Inicio"
Public Const SHEET_EXCEPTIONS As String = "Excepciones"
Public Const SHEET_CORRECTIONS As String = "Correcciones"
Public Const SHEET_SUMMARY As String = "Resumen"
Public Const SHEET_DETAIL As String = "Detalle"
Public Const SHEET_STOCK As String = "Existencias"
Public Const SHEET_LIMITS As String = "Minimos"
Public Const SHEET_PRODUCT_SUPPLIER As String = "Producto_Proveedor"
Public Const SHEET_SUPPLIERS As String = "Proveedores"

' Copia oculta de cada hoja tal como se cargo, para la hoja Correcciones.
Public Const LOADED_PREFIX As String = "_Cargado_"

' Hojas de datos: fila 1 titulo, fila 2 encabezado, datos desde la fila 3 (como el Excel exportado).
Public Const DATA_HEADER_ROW As Long = 2
Public Const DATA_FIRST_ROW As Long = 3
' Renglones vacios editables despues del ultimo dato, para agregar registros.
Public Const DATA_SPARE_ROWS As Long = 200

Private Const XL_SHEET_VERY_HIDDEN As Long = 2
Private Const SHAPE_ROUNDED_RECTANGLE As Long = 5
Private Const ALIGN_CENTER As Long = 2
Private Const ANCHOR_MIDDLE As Long = 3
Private Const XL_MOVE As Long = 2

Private Const COLOR_PRIMARY As Long = 7949855    ' RGB(31, 78, 121)
Private Const COLOR_HEADER As Long = 15917529    ' RGB(217, 225, 242)
Private Const COLOR_MUTED As Long = 8421504      ' RGB(128, 128, 128)
Private Const COLOR_DATA_TAB As Long = 12566463  ' RGB(191, 191, 191)

Public Function DataSheetNames() As Variant
    DataSheetNames = Array(SHEET_STOCK, SHEET_LIMITS, SHEET_PRODUCT_SUPPLIER, SHEET_SUPPLIERS)
End Function

' Columnas que debe traer cada hoja del Excel exportado (resurtido/loader.py: SHEET_COLUMNS).
Public Function DataColumns(ByVal sheetName As String) As Variant
    Select Case sheetName
        Case SHEET_STOCK
            DataColumns = Array("Codigo", "Descripcion", "Existencia", "Unidad", "Estatus")
        Case SHEET_LIMITS
            DataColumns = Array("Codigo", "Minimo", "Maximo")
        Case SHEET_PRODUCT_SUPPLIER
            DataColumns = Array("Codigo", "Proveedor_ID", "Costo_unitario_MXN", "Empaque_multiplo")
        Case SHEET_SUPPLIERS
            DataColumns = Array("Proveedor_ID", "Nombre", "Correo", "Pedido_minimo_MXN")
    End Select
End Function

Public Function ExceptionColumns() As Variant
    ExceptionColumns = Array("Hoja", "Fila", U("C\u00f3digo"), "Tipo", "Detalle", _
        "Valor original", U("Decisi\u00f3n"), "Grupo", "Ir a la celda")
End Function

Public Function CorrectionColumns() As Variant
    CorrectionColumns = Array("Hoja", "Celda", U("C\u00f3digo"), "Valor cargado", "Valor actual")
End Function

' Mismas columnas que pedidos.xlsx (resurtido/report.py: SUMMARY_COLUMNS y DETAIL_COLUMNS).
Public Function SummaryColumns() As Variant
    SummaryColumns = Array("Proveedor_ID", "Proveedor", "Correo", "Productos", "Total_MXN", _
        "Pedido_minimo_MXN", "Estado")
End Function

Public Function DetailColumns() As Variant
    DetailColumns = Array("Proveedor_ID", "Proveedor", "Codigo", "Descripcion", "Existencia", _
        "Minimo", "Maximo", "Empaque_multiplo", "Cantidad", "Costo_unitario_MXN", "Importe_MXN", _
        "Estado_pedido", "Revisar")
End Function

Public Sub BuildWorkbook()
    Dim wb As Workbook, item As Variant
    Set wb = ThisWorkbook
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    Do While wb.Worksheets.Count > 1
        wb.Worksheets(wb.Worksheets.Count).Delete
    Loop
    Application.DisplayAlerts = True

    wb.Worksheets(1).Name = SHEET_HOME
    BuildHome wb.Worksheets(1)
    BuildTable AddSheet(wb, SHEET_EXCEPTIONS), ExceptionColumns(), _
        Array(20, 7, 12, 32, 50, 24, 50, 16, 14)
    BuildTable AddSheet(wb, SHEET_CORRECTIONS), CorrectionColumns(), Array(20, 9, 12, 24, 24)
    BuildTable AddSheet(wb, SHEET_SUMMARY), SummaryColumns(), Array(13, 32, 28, 11, 15, 19, 24)
    BuildTable AddSheet(wb, SHEET_DETAIL), DetailColumns(), _
        Array(13, 32, 11, 30, 11, 9, 9, 17, 10, 19, 15, 24, 9)
    For Each item In DataSheetNames()
        BuildDataSheet AddSheet(wb, CStr(item)), CStr(item)
    Next item
    For Each item In DataSheetNames()
        AddSheet(wb, LOADED_PREFIX & item).Visible = XL_SHEET_VERY_HIDDEN
    Next item

    For Each item In Array(SHEET_HOME, SHEET_EXCEPTIONS, SHEET_CORRECTIONS, SHEET_SUMMARY, _
                           SHEET_DETAIL, SHEET_STOCK, SHEET_LIMITS, SHEET_PRODUCT_SUPPLIER, _
                           SHEET_SUPPLIERS)
        ProtectSheet wb.Worksheets(CStr(item))
    Next item
    wb.Worksheets(SHEET_HOME).Activate
    Application.ScreenUpdating = True
End Sub

' Cada macro que escribe en una hoja la desprotege y al terminar llama a ProtectSheet.
' Sin contrasena: la proteccion evita errores, no es seguridad.
Public Sub ProtectSheet(ByVal ws As Worksheet)
    Select Case ws.Name
        Case SHEET_HOME
            ws.Protect DrawingObjects:=True, Contents:=True
        Case SHEET_STOCK, SHEET_LIMITS, SHEET_PRODUCT_SUPPLIER, SHEET_SUPPLIERS
            ws.Protect DrawingObjects:=True, Contents:=True, AllowFormattingColumns:=True, _
                AllowInsertingRows:=False, AllowDeletingRows:=False, _
                AllowInsertingColumns:=False, AllowDeletingColumns:=False
        Case Else
            ws.Protect DrawingObjects:=True, Contents:=True, AllowFormattingColumns:=True, _
                AllowFiltering:=True
    End Select
End Sub

' Deja editables las celdas de datos y DATA_SPARE_ROWS renglones vacios al final.
Public Sub SetEditableRows(ByVal ws As Worksheet, ByVal lastDataRow As Long)
    Dim columnCount As Long
    columnCount = UBound(DataColumns(ws.Name)) + 1
    ws.Cells.Locked = True
    ws.Range(ws.Cells(DATA_FIRST_ROW, 1), _
             ws.Cells(Application.Max(lastDataRow, DATA_FIRST_ROW) + DATA_SPARE_ROWS, columnCount)) _
        .Locked = False
End Sub

Private Function AddSheet(ByVal wb As Workbook, ByVal sheetName As String) As Worksheet
    Set AddSheet = wb.Worksheets.Add(After:=wb.Worksheets(wb.Worksheets.Count))
    AddSheet.Name = sheetName
End Function

Private Sub BuildHome(ByVal ws As Worksheet)
    ws.Activate
    ws.Cells.Font.Size = 12
    ws.Columns("A").ColumnWidth = 2
    ws.Columns("B").ColumnWidth = 5
    ws.Columns("C").ColumnWidth = 26
    ws.Columns("D").ColumnWidth = 95
    ws.Tab.Color = COLOR_PRIMARY

    With ws.Range("B2")
        .Value = "Resurtido semanal - Ferretera Garza"
        .Font.Size = 20
        .Font.Bold = True
        .Font.Color = COLOR_PRIMARY
    End With
    With ws.Range("B3")
        .Value = U("Sigue los pasos en orden. El Excel que exporta el sistema nunca se modifica.")
        .Font.Color = COLOR_MUTED
    End With

    AddStep ws, 5, 1, "Cargar inventario", "LoadInventory", _
        U("Elige el Excel que exporta el sistema. Se copian sus cuatro hojas a este libro.")
    AddStep ws, 7, 2, "Revisar datos", "ReviewData", _
        U("Llena la hoja Excepciones. Corrige en las hojas de datos y vuelve a revisar; " & _
          "cada cambio queda en Correcciones.")
    AddStep ws, 9, 3, "Preparar pedidos", "PrepareOrders", _
        U("Calcula los pedidos por proveedor en Resumen y Detalle. En Detalle puedes " & _
          "ajustar la Cantidad.")
    AddStep ws, 11, 4, "Generar correos", "GenerateEmails", _
        U("Deja un borrador por pedido en la carpeta correos, junto a este libro. " & _
          "No env\u00eda nada.")

    With ws.Range("B14")
        .Value = "Estado"
        .Font.Bold = True
        .Font.Size = 14
    End With
    AddStatus ws, 15, "Inventario cargado", "StatusLoaded"
    AddStatus ws, 16, U("Revisi\u00f3n de datos"), "StatusReviewed"
    AddStatus ws, 17, "Excepciones", "StatusExceptions"
    AddStatus ws, 18, "Pedidos", "StatusOrders"
    AddStatus ws, 19, "Correos", "StatusEmails"

    ActiveWindow.DisplayGridlines = False
End Sub

Private Sub AddStep(ByVal ws As Worksheet, ByVal row As Long, ByVal number As Long, _
                    ByVal caption As String, ByVal macroName As String, ByVal instruction As String)
    Dim cell As Range, button As Shape
    ws.Rows(row).RowHeight = 34
    With ws.Cells(row, 2)
        .Value = number
        .Font.Size = 18
        .Font.Bold = True
        .Font.Color = COLOR_PRIMARY
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
    End With
    With ws.Cells(row, 4)
        .Value = instruction
        .VerticalAlignment = xlCenter
    End With

    Set cell = ws.Cells(row, 3)
    Set button = ws.Shapes.AddShape(SHAPE_ROUNDED_RECTANGLE, cell.Left + 2, cell.Top + 2, _
                                    cell.Width - 8, cell.Height - 4)
    button.Name = "btn" & macroName
    button.Fill.ForeColor.RGB = COLOR_PRIMARY
    button.Line.Visible = False
    button.Placement = XL_MOVE
    With button.TextFrame2
        .VerticalAnchor = ANCHOR_MIDDLE
        .TextRange.Text = caption
        .TextRange.ParagraphFormat.Alignment = ALIGN_CENTER
        .TextRange.Font.Bold = True
        .TextRange.Font.Size = 13
        .TextRange.Font.Fill.ForeColor.RGB = vbWhite
    End With
    button.OnAction = "modUI." & macroName
End Sub

' Cada valor de estado tiene un nombre definido para que los botones lo actualicen.
Private Sub AddStatus(ByVal ws As Worksheet, ByVal row As Long, ByVal label As String, _
                      ByVal rangeName As String)
    ws.Cells(row, 3).Value = label
    ws.Cells(row, 3).Font.Color = COLOR_MUTED
    ws.Cells(row, 4).Value = "Pendiente"
    ws.Parent.Names.Add Name:=rangeName, RefersTo:="='" & ws.Name & "'!" & _
        ws.Cells(row, 4).Address
End Sub

Private Sub BuildTable(ByVal ws As Worksheet, ByVal headers As Variant, ByVal widths As Variant)
    Dim i As Long
    For i = 0 To UBound(headers)
        ws.Cells(1, i + 1).Value = headers(i)
        ws.Columns(i + 1).ColumnWidth = widths(i)
    Next i
    StyleHeader ws.Range(ws.Cells(1, 1), ws.Cells(1, UBound(headers) + 1))
    FreezeBelow ws, 1
End Sub

Private Sub BuildDataSheet(ByVal ws As Worksheet, ByVal sheetName As String)
    Dim headers As Variant, i As Long
    headers = DataColumns(sheetName)
    ws.Tab.Color = COLOR_DATA_TAB
    ws.Cells(1, 1).Value = EmptyTitle()
    ws.Cells(1, 1).Font.Color = COLOR_MUTED
    For i = 0 To UBound(headers)
        ws.Cells(DATA_HEADER_ROW, i + 1).Value = headers(i)
        ws.Columns(i + 1).ColumnWidth = 18
    Next i
    StyleHeader ws.Range(ws.Cells(DATA_HEADER_ROW, 1), ws.Cells(DATA_HEADER_ROW, UBound(headers) + 1))
    FreezeBelow ws, DATA_HEADER_ROW
    SetEditableRows ws, DATA_FIRST_ROW - 1
End Sub

' Escribe un valor del bloque Estado de la hoja Inicio.
Public Sub SetStatus(ByVal rangeName As String, ByVal text As String)
    Dim home As Worksheet
    Set home = ThisWorkbook.Worksheets(SHEET_HOME)
    home.Unprotect
    ThisWorkbook.Names(rangeName).RefersToRange.Value = text
    ProtectSheet home
End Sub

' Borra todo debajo del encabezado de una hoja de resultados.
Public Sub ClearTable(ByVal ws As Worksheet)
    ws.Unprotect
    If ws.AutoFilterMode Then ws.AutoFilterMode = False
    ws.Range(ws.Rows(2), ws.Rows(ws.Rows.Count)).Clear
    ProtectSheet ws
End Sub

Public Sub StyleHeader(ByVal header As Range)
    header.Font.Bold = True
    header.Interior.Color = COLOR_HEADER
End Sub

Private Sub FreezeBelow(ByVal ws As Worksheet, ByVal row As Long)
    ws.Activate
    ActiveWindow.FreezePanes = False
    ActiveWindow.SplitColumn = 0
    ActiveWindow.SplitRow = row
    ActiveWindow.FreezePanes = True
End Sub
