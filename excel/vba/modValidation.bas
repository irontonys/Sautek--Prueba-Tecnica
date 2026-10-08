Attribute VB_Name = "modValidation"
' Deteccion de problemas en los datos y decision de cada caso. Es la traduccion de
' resurtido/validation.py: mismas reglas, mismos textos y mismo orden. Si una regla
' cambia alla, se cambia aqui y la prueba de paridad lo confirma.
' Los tipos se guardan con sus acentos escapados (\uXXXX); U() los convierte al escribir.
Option Explicit

Public Const EXISTENCIA_TEXTO As String = "Existencia como texto"
Public Const EXISTENCIA_NO_NUMERICA As String = "Existencia no num\u00e9rica"
Public Const EXISTENCIA_VACIA As String = "Existencia vac\u00eda"
Public Const EXISTENCIA_NEGATIVA As String = "Existencia negativa"
Public Const CODIGO_VACIO As String = "C\u00f3digo vac\u00edo"
Public Const CODIGO_FORMATO As String = "C\u00f3digo con formato distinto"
Public Const CODIGO_NO_NORMALIZABLE As String = "C\u00f3digo no normalizable"
Public Const CODIGO_REPETIDO As String = "C\u00f3digo repetido en Existencias"
Public Const CODIGO_REPETIDO_REFERENCIA As String = "C\u00f3digo repetido en hoja de referencia"
Public Const PRODUCTO_INACTIVO As String = "Producto inactivo"
Public Const POSIBLE_DUPLICADO As String = "Mismo producto con dos c\u00f3digos"
Public Const UNIDAD_INCONSISTENTE As String = "Unidad distinta a la descripci\u00f3n"
Public Const CODIGO_SIN_EXISTENCIA As String = "C\u00f3digo ausente de Existencias"
Public Const SIN_MINIMO As String = "Producto sin m\u00ednimo"
Public Const SIN_PROVEEDOR As String = "Producto sin proveedor"
Public Const MINIMO_INVALIDO As String = "M\u00ednimo o m\u00e1ximo inv\u00e1lido"
Public Const MINIMO_MAYOR_MAXIMO As String = "M\u00ednimo mayor que m\u00e1ximo"
Public Const COSTO_INVALIDO As String = "Costo inv\u00e1lido"
Public Const MULTIPLO_INVALIDO As String = "M\u00faltiplo de empaque inv\u00e1lido"
Public Const PROVEEDOR_INEXISTENTE As String = "Proveedor inexistente"
Public Const PEDIDO_MINIMO_INVALIDO As String = "Pedido m\u00ednimo inv\u00e1lido"
Public Const CORREO_INVALIDO As String = "Correo inv\u00e1lido"
Public Const PEDIDO_MINIMO_NO_ALCANZADO As String = "Pedido m\u00ednimo no alcanzado"

Public Const GROUP_CORRECTED As String = "Se corrigi\u00f3"
Public Const GROUP_WARNING As String = "Advertencia"
Public Const GROUP_EXCLUDED As String = "No se proces\u00f3"
Public Const GROUP_PURCHASE As String = "Compra"

Public Type DataException
    Hoja As String
    Fila As Long
    Codigo As String
    Tipo As String
    Detalle As String
    Valor As String
End Type

Public Type SupplierRecord
    Id As String
    Nombre As String
    Correo As String
    PedidoMinimo As Double
    Fila As Long
End Type

Public Type ProductRecord
    Codigo As String
    Descripcion As String
    Existencia As Double
    Minimo As Double
    Maximo As Double
    ProveedorId As String
    Costo As Double
    Multiplo As Long
    Fila As Long
    Revisar As Boolean
End Type

' Resultado de la ultima validacion (ValidationResult de Python).
Public Exceptions() As DataException
Public ExceptionCount As Long
Public Products() As ProductRecord
Public ProductCount As Long
Public Suppliers() As SupplierRecord
Public SupplierCount As Long
Public RowsRead As Long
Public RepeatedCount As Long
Public ExcludedCount As Long

' Renglones con algun valor de una hoja de datos (pandas descarta los totalmente vacios).
Private Type SheetRows
    Count As Long
    Fila() As Long
    Values() As Variant
End Type

' Decisiones del autor (validation.py: DECISIONS). Un tipo que no esta aqui sale
' "Pendiente de decision" y excluye al producto.
Public Function DecisionText(ByVal tipo As String) As String
    Select Case tipo
        Case EXISTENCIA_TEXTO: DecisionText = U("Se convirti\u00f3 a n\u00famero y se procesa")
        Case EXISTENCIA_NO_NUMERICA: DecisionText = U("No se puede convertir a n\u00famero: no se procesa")
        Case EXISTENCIA_VACIA: DecisionText = "No se procesa"
        Case EXISTENCIA_NEGATIVA
            DecisionText = U("Se pide tomando existencia 0 y se marca para revisi\u00f3n del comprador")
        Case CODIGO_VACIO: DecisionText = "No se puede identificar el producto: no se procesa"
        Case CODIGO_FORMATO: DecisionText = U("Se normaliz\u00f3 el c\u00f3digo y se procesa")
        Case CODIGO_REPETIDO: DecisionText = U("Se conserva la primera aparici\u00f3n; este rengl\u00f3n se ignora")
        Case PRODUCTO_INACTIVO: DecisionText = "No se pide"
        Case POSIBLE_DUPLICADO
            DecisionText = U("No se procesa ning\u00fan c\u00f3digo del grupo hasta definir cu\u00e1l es el bueno")
        Case UNIDAD_INCONSISTENTE
            DecisionText = U("Se supone la misma unidad en existencia, m\u00ednimo y m\u00e1ximo (ver SUPUESTOS.md)")
        Case CODIGO_SIN_EXISTENCIA, SIN_MINIMO, SIN_PROVEEDOR, MINIMO_INVALIDO, MINIMO_MAYOR_MAXIMO
            DecisionText = "No se procesa"
        Case PEDIDO_MINIMO_NO_ALCANZADO
            DecisionText = U("No se env\u00eda el pedido; el comprador decide si lo completa")
        Case Else: DecisionText = U("Pendiente de decisi\u00f3n")
    End Select
End Function

Public Function Excludes(ByVal tipo As String) As Boolean
    Select Case tipo
        Case EXISTENCIA_TEXTO, EXISTENCIA_NEGATIVA, CODIGO_FORMATO, CODIGO_REPETIDO, _
             UNIDAD_INCONSISTENTE, PEDIDO_MINIMO_NO_ALCANZADO
            Excludes = False
        Case Else
            Excludes = True
    End Select
End Function

' Mismos grupos que la bandeja de excepciones de Odoo.
Public Function ExceptionGroup(ByVal tipo As String) As String
    If tipo = PEDIDO_MINIMO_NO_ALCANZADO Then
        ExceptionGroup = GROUP_PURCHASE
    ElseIf Excludes(tipo) Then
        ExceptionGroup = GROUP_EXCLUDED
    ElseIf tipo = EXISTENCIA_NEGATIVA Or tipo = UNIDAD_INCONSISTENTE Then
        ExceptionGroup = GROUP_WARNING
    Else
        ExceptionGroup = GROUP_CORRECTED
    End If
End Function

Public Sub AddException(ByVal hoja As String, ByVal fila As Long, ByVal codigo As String, _
                        ByVal tipo As String, ByVal detalle As String, Optional ByVal valor As String)
    If ExceptionCount = 0 Then
        ReDim Exceptions(1 To 16)
    ElseIf ExceptionCount = UBound(Exceptions) Then
        ReDim Preserve Exceptions(1 To ExceptionCount * 2)
    End If
    ExceptionCount = ExceptionCount + 1
    With Exceptions(ExceptionCount)
        .Hoja = hoja
        .Fila = fila
        .Codigo = codigo
        .Tipo = tipo
        .Detalle = detalle
        .Valor = valor
    End With
End Sub

Public Sub Validate()
    Dim stock As SheetRows, limitsSheet As SheetRows, pp As SheetRows, prov As SheetRows
    Dim stockCodes() As String, stockHas() As Boolean
    Dim firstRow As New Collection, stockIdx() As Long, stockCode() As String, stockN As Long
    Dim stockValue() As Double, stockKnown() As Boolean, review As New Collection
    Dim i As Long, k As Long, code As String, fila As Long, blankCodes As Long
    Dim estatus As String, unit As String, declared As String, needsReview As Boolean

    ResetResult
    stock = ReadSheet(SHEET_STOCK)
    limitsSheet = ReadSheet(SHEET_LIMITS)
    pp = ReadSheet(SHEET_PRODUCT_SUPPLIER)
    prov = ReadSheet(SHEET_SUPPLIERS)
    RowsRead = stock.Count

    ' Existencias: codigos, repetidos (se conserva el primero) y datos de cada producto.
    ReadCodes stock, SHEET_STOCK, "Codigo", stockCodes, stockHas
    If stock.Count > 0 Then
        ReDim stockIdx(1 To stock.Count)
        ReDim stockCode(1 To stock.Count)
    End If
    For i = 1 To stock.Count
        If stockHas(i) Then
            code = stockCodes(i)
            If Has(firstRow, code) Then
                RepeatedCount = RepeatedCount + 1
                AddException SHEET_STOCK, stock.Fila(i), code, CODIGO_REPETIDO, _
                    U("El c\u00f3digo ya aparece en la fila ") & firstRow(code)
            Else
                firstRow.Add stock.Fila(i), code
                stockN = stockN + 1
                stockIdx(stockN) = i
                stockCode(stockN) = code
            End If
        End If
    Next i
    blankCodes = stock.Count - RepeatedCount - stockN

    If stockN > 0 Then
        ReDim stockValue(1 To stockN)
        ReDim stockKnown(1 To stockN)
    End If
    For k = 1 To stockN
        i = stockIdx(k)
        code = stockCode(k)
        fila = stock.Fila(i)
        estatus = UCase$(PyStrip(AsText(stock.Values(i, 5))))
        If estatus <> "ACTIVO" Then
            AddException SHEET_STOCK, fila, code, PRODUCTO_INACTIVO, _
                "Estatus " & IIf(Len(estatus) > 0, estatus, U("vac\u00edo")), AsText(stock.Values(i, 5))
        End If
        stockKnown(k) = ReadStock(stock.Values(i, 3), code, fila, stockValue(k), needsReview)
        If needsReview Then review.Add True, code
        unit = UnitInDescription(AsText(stock.Values(i, 2)))
        declared = UCase$(PyStrip(AsText(stock.Values(i, 4))))
        If Len(unit) > 0 And UCase$(unit) <> declared Then
            AddException SHEET_STOCK, fila, code, UNIDAD_INCONSISTENTE, _
                U("La descripci\u00f3n dice (") & unit & ") y la unidad es " & _
                IIf(Len(declared) > 0, declared, U("vac\u00eda")), AsText(stock.Values(i, 2))
        End If
    Next k

    FindDuplicates stock, stockIdx, stockCode, stockN

    ' Minimos.
    Dim limCodes() As String, limHas() As Boolean, minIndex As New Collection
    Dim minOrder() As String, minN As Long, limits As New Collection
    Dim minimo As Variant, maximo As Variant, valid As Boolean
    ReadCodes limitsSheet, SHEET_LIMITS, "Codigo", limCodes, limHas
    FirstByCode limitsSheet, limCodes, limHas, SHEET_LIMITS, minIndex, minOrder, minN
    For k = 1 To minN
        code = minOrder(k)
        i = minIndex(code)
        fila = limitsSheet.Fila(i)
        If Not Has(firstRow, code) Then
            AddException SHEET_LIMITS, fila, code, CODIGO_SIN_EXISTENCIA, "No aparece en Existencias"
        End If
        minimo = limitsSheet.Values(i, 2)
        maximo = limitsSheet.Values(i, 3)
        valid = IsNum(minimo) And IsNum(maximo)
        If valid Then valid = minimo >= 0 And maximo >= 0
        If Not valid Then
            AddException SHEET_LIMITS, fila, code, MINIMO_INVALIDO, _
                U("M\u00ednimo y m\u00e1ximo deben ser n\u00fameros mayores o iguales a 0"), _
                AsText(minimo) & " / " & AsText(maximo)
        ElseIf minimo > maximo Then
            AddException SHEET_LIMITS, fila, code, MINIMO_MAYOR_MAXIMO, _
                U("M\u00ednimo ") & FormatG(minimo) & U(" mayor que m\u00e1ximo ") & FormatG(maximo), _
                FormatG(minimo) & " / " & FormatG(maximo)
        Else
            limits.Add i, code
        End If
    Next k

    ' Proveedores y Producto_Proveedor.
    Dim invalidSuppliers As New Collection, supplierIndex As New Collection
    ValidateSuppliers prov, invalidSuppliers, supplierIndex

    Dim ppCodes() As String, ppHas() As Boolean, ppIndex As New Collection
    Dim ppOrder() As String, ppN As Long, purchase As New Collection
    Dim supplierId As String, costo As Variant, multiplo As Variant, bad As Boolean
    ReadCodes pp, SHEET_PRODUCT_SUPPLIER, "Codigo", ppCodes, ppHas
    FirstByCode pp, ppCodes, ppHas, SHEET_PRODUCT_SUPPLIER, ppIndex, ppOrder, ppN
    For k = 1 To ppN
        code = ppOrder(k)
        i = ppIndex(code)
        fila = pp.Fila(i)
        If Not Has(firstRow, code) Then
            AddException SHEET_PRODUCT_SUPPLIER, fila, code, CODIGO_SIN_EXISTENCIA, _
                "No aparece en Existencias"
        End If
        supplierId = UCase$(PyStrip(AsText(pp.Values(i, 2))))
        costo = pp.Values(i, 3)
        multiplo = pp.Values(i, 4)
        valid = True
        If Not Has(supplierIndex, supplierId) Then
            valid = False
            AddException SHEET_PRODUCT_SUPPLIER, fila, code, PROVEEDOR_INEXISTENTE, _
                U("El proveedor no est\u00e1 en la hoja Proveedores"), AsText(pp.Values(i, 2))
        End If
        bad = Not IsNum(costo)
        If Not bad Then bad = costo <= 0
        If bad Then
            valid = False
            AddException SHEET_PRODUCT_SUPPLIER, fila, code, COSTO_INVALIDO, _
                U("El costo debe ser un n\u00famero mayor a 0"), AsText(costo)
        End If
        bad = Not IsNum(multiplo)
        If Not bad Then bad = multiplo <= 0 Or CDbl(multiplo) <> Fix(CDbl(multiplo))
        If bad Then
            valid = False
            AddException SHEET_PRODUCT_SUPPLIER, fila, code, MULTIPLO_INVALIDO, _
                U("El m\u00faltiplo debe ser un entero mayor a 0"), AsText(multiplo)
        End If
        If valid Then purchase.Add i, code
    Next k

    ' Referencias faltantes de cada producto.
    For k = 1 To stockN
        code = stockCode(k)
        fila = stock.Fila(stockIdx(k))
        If Not Has(minIndex, code) Then
            AddException SHEET_STOCK, fila, code, SIN_MINIMO, "No aparece en Minimos"
        End If
        If Not Has(ppIndex, code) Then
            AddException SHEET_STOCK, fila, code, SIN_PROVEEDOR, "No aparece en Producto_Proveedor"
        End If
    Next k

    ' Clasificacion: un producto se excluye si alguna de sus excepciones lo excluye.
    Dim excludedCodes As New Collection
    For i = 1 To ExceptionCount
        With Exceptions(i)
            If Excludes(.Tipo) And .Hoja <> SHEET_SUPPLIERS And Len(.Codigo) > 0 Then
                If Not Has(excludedCodes, .Codigo) Then excludedCodes.Add True, .Codigo
            End If
        End With
    Next i
    ExcludedCount = blankCodes
    Dim excluded As Boolean, row As Long
    For k = 1 To stockN
        code = stockCode(k)
        i = stockIdx(k)
        supplierId = ""
        If Has(purchase, code) Then supplierId = UCase$(PyStrip(AsText(pp.Values(purchase(code), 2))))
        excluded = Has(excludedCodes, code) Or Not stockKnown(k) Or Not Has(limits, code) _
            Or Not Has(purchase, code)
        If Not excluded And Len(supplierId) > 0 Then excluded = Has(invalidSuppliers, supplierId)
        If excluded Then
            ExcludedCount = ExcludedCount + 1
        Else
            ProductCount = ProductCount + 1
            If ProductCount = 1 Then ReDim Products(1 To stockN)
            row = purchase(code)
            With Products(ProductCount)
                .Codigo = code
                .Descripcion = PyStrip(AsText(stock.Values(i, 2)))
                .Existencia = stockValue(k)
                .Minimo = CDbl(limitsSheet.Values(limits(code), 2))
                .Maximo = CDbl(limitsSheet.Values(limits(code), 3))
                .ProveedorId = supplierId
                .Costo = CDbl(pp.Values(row, 3))
                .Multiplo = CLng(pp.Values(row, 4))
                .Fila = stock.Fila(i)
                .Revisar = Has(review, code)
            End With
        End If
    Next k

    SortExceptions
End Sub

' Ordena las excepciones como aparecen en el Excel: por hoja y luego por fila. Estable,
' igual que sorted() de Python: dentro de la misma fila se respeta el orden de deteccion.
Public Sub SortExceptions()
    Dim i As Long, j As Long, current As DataException
    For i = 2 To ExceptionCount
        current = Exceptions(i)
        j = i - 1
        Do While j >= 1
            If Not ComesAfter(Exceptions(j), current) Then Exit Do
            Exceptions(j + 1) = Exceptions(j)
            j = j - 1
        Loop
        Exceptions(j + 1) = current
    Next i
End Sub

Private Function ComesAfter(ByRef a As DataException, ByRef b As DataException) As Boolean
    Dim orderA As Long, orderB As Long
    orderA = SheetOrder(a.Hoja)
    orderB = SheetOrder(b.Hoja)
    If orderA <> orderB Then
        ComesAfter = orderA > orderB
    Else
        ComesAfter = a.Fila > b.Fila
    End If
End Function

Private Function SheetOrder(ByVal hoja As String) As Long
    Select Case hoja
        Case SHEET_STOCK: SheetOrder = 0
        Case SHEET_LIMITS: SheetOrder = 1
        Case SHEET_PRODUCT_SUPPLIER: SheetOrder = 2
        Case Else: SheetOrder = 3
    End Select
End Function

Private Sub ResetResult()
    Erase Exceptions
    Erase Products
    Erase Suppliers
    ExceptionCount = 0
    ProductCount = 0
    SupplierCount = 0
    RowsRead = 0
    RepeatedCount = 0
    ExcludedCount = 0
End Sub

Private Function ReadSheet(ByVal sheetName As String) As SheetRows
    Dim ws As Worksheet, columnCount As Long, lastRow As Long, raw As Variant
    Dim result As SheetRows, r As Long, c As Long, used As Boolean, value As Variant
    Set ws = ThisWorkbook.Worksheets(sheetName)
    columnCount = UBound(DataColumns(sheetName)) + 1
    lastRow = LastDataRow(ws, columnCount)
    If lastRow < DATA_FIRST_ROW Then
        ReadSheet = result
        Exit Function
    End If
    raw = ws.Range(ws.Cells(DATA_FIRST_ROW, 1), ws.Cells(lastRow, columnCount)).Value
    ReDim result.Fila(1 To UBound(raw, 1))
    ReDim result.Values(1 To UBound(raw, 1), 1 To columnCount)
    For r = 1 To UBound(raw, 1)
        used = False
        For c = 1 To columnCount
            If Not IsEmpty(raw(r, c)) Then used = True
        Next c
        If used Then
            result.Count = result.Count + 1
            result.Fila(result.Count) = DATA_FIRST_ROW + r - 1
            For c = 1 To columnCount
                value = raw(r, c)
                If IsError(value) Then value = ErrorText(value)
                If VarType(value) = vbCurrency Then value = CDbl(value)
                result.Values(result.Count, c) = value
            Next c
        End If
    Next r
    ReadSheet = result
End Function

' validation.py: _read_codes. Normaliza los codigos y reporta los vacios y los que cambiaron.
Private Sub ReadCodes(ByRef rows As SheetRows, ByVal hoja As String, ByVal column As String, _
                      ByRef codes() As String, ByRef hasCode() As Boolean)
    Dim i As Long, raw As Variant, code As String, standard As Boolean
    If rows.Count = 0 Then Exit Sub
    ReDim codes(1 To rows.Count)
    ReDim hasCode(1 To rows.Count)
    For i = 1 To rows.Count
        raw = rows.Values(i, 1)
        If IsBlank(raw) Then
            AddException hoja, rows.Fila(i), "", CODIGO_VACIO, U("El rengl\u00f3n no tiene ") & column
        Else
            NormalizeCode raw, code, standard
            If Not standard Then
                AddException hoja, rows.Fila(i), code, CODIGO_NO_NORMALIZABLE, _
                    "No sigue el formato FTR-0000 y no se pudo normalizar", AsText(raw)
            ElseIf code <> PyStr(raw) Then
                AddException hoja, rows.Fila(i), code, CODIGO_FORMATO, _
                    U("Se escribi\u00f3 ") & PyRepr(PyStr(raw)) & "; corresponde a " & code, AsText(raw)
            End If
            codes(i) = code
            hasCode(i) = True
        End If
    Next i
End Sub

' validation.py: normalize_code. Mayusculas, sin espacios y con 4 digitos.
Public Sub NormalizeCode(ByVal value As Variant, ByRef code As String, ByRef standard As Boolean)
    Dim digits As String
    code = UCase$(PyStrip(PyStr(value)))
    If Left$(code, 3) = "FTR" Then
        digits = Mid$(code, 4)
        If Left$(digits, 1) = "-" Then digits = Mid$(digits, 2)
        If Len(digits) >= 1 And Len(digits) <= 4 And AllDigits(digits) Then
            code = "FTR-" & Right$("000" & CStr(CLng(digits)), 4)
        End If
    End If
    standard = code Like "FTR-####"
End Sub

Private Function AllDigits(ByVal text As String) As Boolean
    Dim at As Long
    If Len(text) = 0 Then Exit Function
    For at = 1 To Len(text)
        If Not Mid$(text, at, 1) Like "#" Then Exit Function
    Next at
    AllDigits = True
End Function

' validation.py: _first_by_code. Primer renglon por codigo; los repetidos se reportan.
Private Sub FirstByCode(ByRef rows As SheetRows, ByRef codes() As String, ByRef hasCode() As Boolean, _
                        ByVal hoja As String, ByVal index As Collection, ByRef order() As String, _
                        ByRef count As Long)
    Dim i As Long, code As String
    If rows.Count = 0 Then Exit Sub
    ReDim order(1 To rows.Count)
    For i = 1 To rows.Count
        If hasCode(i) Then
            code = codes(i)
            If Has(index, code) Then
                AddException hoja, rows.Fila(i), code, CODIGO_REPETIDO_REFERENCIA, _
                    U("El c\u00f3digo ya aparece en la fila ") & rows.Fila(index(code)) & " de " & hoja
            Else
                index.Add i, code
                count = count + 1
                order(count) = code
            End If
        End If
    Next i
End Sub

' validation.py: _validate_suppliers
Private Sub ValidateSuppliers(ByRef rows As SheetRows, ByVal invalid As Collection, _
                              ByVal supplierIndex As Collection)
    Dim seen As New Collection, i As Long, fila As Long, supplierId As String
    Dim correo As String, pedidoMinimo As Variant, bad As Boolean
    If rows.Count > 0 Then ReDim Suppliers(1 To rows.Count)
    For i = 1 To rows.Count
        fila = rows.Fila(i)
        If IsBlank(rows.Values(i, 1)) Then
            AddException SHEET_SUPPLIERS, fila, "", CODIGO_VACIO, U("El rengl\u00f3n no tiene Proveedor_ID")
        Else
            supplierId = UCase$(PyStrip(PyStr(rows.Values(i, 1))))
            If Has(seen, supplierId) Then
                If Not Has(invalid, supplierId) Then invalid.Add True, supplierId
                AddException SHEET_SUPPLIERS, fila, supplierId, CODIGO_REPETIDO_REFERENCIA, _
                    "El proveedor ya aparece en la fila " & seen(supplierId)
            Else
                seen.Add fila, supplierId
                correo = PyStrip(AsText(rows.Values(i, 3)))
                If Not IsEmail(correo) Then
                    If Not Has(invalid, supplierId) Then invalid.Add True, supplierId
                    AddException SHEET_SUPPLIERS, fila, supplierId, CORREO_INVALIDO, _
                        U("El correo no tiene formato v\u00e1lido"), AsText(rows.Values(i, 3))
                End If
                pedidoMinimo = rows.Values(i, 4)
                bad = Not IsNum(pedidoMinimo)
                If Not bad Then bad = pedidoMinimo < 0
                If bad Then
                    If Not Has(invalid, supplierId) Then invalid.Add True, supplierId
                    AddException SHEET_SUPPLIERS, fila, supplierId, PEDIDO_MINIMO_INVALIDO, _
                        U("El pedido m\u00ednimo debe ser un n\u00famero mayor o igual a 0"), AsText(pedidoMinimo)
                    pedidoMinimo = 0
                End If
                SupplierCount = SupplierCount + 1
                With Suppliers(SupplierCount)
                    .Id = supplierId
                    .Nombre = PyStrip(AsText(rows.Values(i, 2)))
                    .Correo = correo
                    .PedidoMinimo = CDbl(pedidoMinimo)
                    .Fila = fila
                End With
                supplierIndex.Add SupplierCount, supplierId
            End If
        End If
    Next i
End Sub

' validation.py: EMAIL, [^@\s]+@[^@\s]+\.[A-Za-z]{2,} sobre el texto completo.
Public Function IsEmail(ByVal text As String) As Boolean
    Dim at As Long, domain As String, dot As Long, tld As String, i As Long
    at = InStr(text, "@")
    If at <= 1 Then Exit Function
    If InStr(at + 1, text, "@") > 0 Then Exit Function
    If HasPyWhitespace(text) Then Exit Function
    domain = Mid$(text, at + 1)
    dot = InStrRev(domain, ".")
    If dot <= 1 Then Exit Function
    tld = Mid$(domain, dot + 1)
    If Len(tld) < 2 Then Exit Function
    For i = 1 To Len(tld)
        If Not Mid$(tld, i, 1) Like "[A-Za-z]" Then Exit Function
    Next i
    IsEmail = True
End Function

' validation.py: _read_stock. Regresa True si hay existencia para el calculo; needsReview
' indica que se marca para revision del comprador (existencia negativa).
Private Function ReadStock(ByVal raw As Variant, ByVal code As String, ByVal fila As Long, _
                           ByRef value As Double, ByRef needsReview As Boolean) As Boolean
    Dim number As Double, fromText As Boolean
    needsReview = False
    If IsBlank(raw) Then
        AddException SHEET_STOCK, fila, code, EXISTENCIA_VACIA, U("La existencia est\u00e1 vac\u00eda")
        Exit Function
    End If
    If VarType(raw) = vbString Then
        If Not ParseTextNumber(raw, number) Then
            AddException SHEET_STOCK, fila, code, EXISTENCIA_NO_NUMERICA, _
                U("La existencia no es un n\u00famero"), AsText(raw)
            Exit Function
        End If
        AddException SHEET_STOCK, fila, code, EXISTENCIA_TEXTO, _
            U("Ven\u00eda como texto; se tom\u00f3 como ") & FormatG(number), AsText(raw)
        fromText = True
    ElseIf Not IsNum(raw) Then
        AddException SHEET_STOCK, fila, code, EXISTENCIA_NO_NUMERICA, _
            U("La existencia no es un n\u00famero"), AsText(raw)
        Exit Function
    Else
        number = CDbl(raw)
    End If
    If number < 0 Then
        AddException SHEET_STOCK, fila, code, EXISTENCIA_NEGATIVA, _
            "Existencia " & FormatG(number) & U("; se toma como 0 para el c\u00e1lculo"), _
            IIf(fromText, FloatRepr(number), AsText(raw))
        number = 0
        needsReview = True
    End If
    value = number
    ReadStock = True
End Function

' validation.py: parse_text_number. "1,250" o "35" a numero; False si no representa uno.
Public Function ParseTextNumber(ByVal text As String, ByRef number As Double) As Boolean
    Dim body As String, intPart As String, fraction As String, dot As Long, groups As Variant
    Dim i As Long
    body = PyStrip(text)
    If Left$(body, 1) = "-" Then body = Mid$(body, 2)
    dot = InStr(body, ".")
    If dot > 0 Then
        intPart = Left$(body, dot - 1)
        fraction = Mid$(body, dot + 1)
        If Not AllDigits(fraction) Then Exit Function
    Else
        intPart = body
    End If
    If InStr(intPart, ",") > 0 Then
        groups = Split(intPart, ",")
        If Len(groups(0)) < 1 Or Len(groups(0)) > 3 Or Not AllDigits(groups(0)) Then Exit Function
        For i = 1 To UBound(groups)
            If Len(groups(i)) <> 3 Or Not AllDigits(groups(i)) Then Exit Function
        Next i
    ElseIf Not AllDigits(intPart) Then
        Exit Function
    End If
    number = Val(Replace(PyStrip(text), ",", ""))
    ParseTextNumber = True
End Function

' validation.py: UNIT_IN_DESCRIPTION, "(caja|bolsa|kg|m|par)" al final de la descripcion.
' Regresa la unidad tal como esta escrita, o "" si no hay.
Private Function UnitInDescription(ByVal description As String) As String
    Dim text As String, unit As Variant, size As Long
    text = PyRStrip(description)
    For Each unit In Array("caja", "bolsa", "kg", "m", "par")
        size = Len(unit) + 2
        If Len(text) >= size Then
            If LCase$(Right$(text, size)) = "(" & unit & ")" Then
                UnitInDescription = Mid$(text, Len(text) - size + 2, Len(unit))
                Exit Function
            End If
        End If
    Next unit
End Function

' validation.py: normalize_description. Minusculas, sin comillas y espacios colapsados.
Public Function NormalizeDescription(ByVal value As Variant) As String
    Dim text As String, result As String, at As Long, ch As String, pendingSpace As Boolean
    text = Replace(Replace(LCase$(PyStr(value)), """", ""), "'", "")
    For at = 1 To Len(text)
        ch = Mid$(text, at, 1)
        If IsPyWhitespace(ch) Then
            pendingSpace = True
        Else
            If pendingSpace And Len(result) > 0 Then result = result & " "
            pendingSpace = False
            result = result & ch
        End If
    Next at
    NormalizeDescription = result
End Function

' Productos con la misma descripcion normalizada: todos los del grupo se reportan.
Private Sub FindDuplicates(ByRef stock As SheetRows, ByRef stockIdx() As Long, _
                           ByRef stockCode() As String, ByVal stockN As Long)
    Dim groups As New Collection, keys() As String, keyCount As Long, members As Collection
    Dim k As Long, key As String, g As Long, m As Variant, other As Variant, others As String
    Dim i As Long
    If stockN = 0 Then Exit Sub
    ReDim keys(1 To stockN)
    For k = 1 To stockN
        i = stockIdx(k)
        If Not IsBlank(stock.Values(i, 2)) Then
            key = NormalizeDescription(stock.Values(i, 2))
            If Not Has(groups, key) Then
                groups.Add New Collection, key
                keyCount = keyCount + 1
                keys(keyCount) = key
            End If
            groups(key).Add k
        End If
    Next k
    For g = 1 To keyCount
        Set members = groups(keys(g))
        If members.Count > 1 Then
            For Each m In members
                others = ""
                For Each other In members
                    If stockCode(other) <> stockCode(m) Then
                        others = others & IIf(Len(others) > 0, ", ", "") & stockCode(other)
                    End If
                Next other
                i = stockIdx(m)
                AddException SHEET_STOCK, stock.Fila(i), stockCode(m), POSIBLE_DUPLICADO, _
                    U("Misma descripci\u00f3n que ") & others, AsText(stock.Values(i, 2))
            Next m
        End If
    Next g
End Sub

' Collection no tiene "contiene"; se prueba la llave y se atrapa el error.
Public Function Has(ByVal items As Collection, ByVal key As String) As Boolean
    Dim probe As Boolean
    If Len(key) = 0 Then Exit Function
    On Error GoTo Missing
    probe = IsObject(items(key))
    Has = True
    Exit Function
Missing:
    Has = False
End Function
