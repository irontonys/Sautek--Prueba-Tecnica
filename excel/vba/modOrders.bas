Attribute VB_Name = "modOrders"
' Calculo de los pedidos de la semana: que pedir, cuanto y a quien. Traduccion de
' resurtido/orders.py. Los importes van en Currency (punto fijo) para no arrastrar el
' error del Double, igual que Decimal en Python.
Option Explicit

Public Const SE_ENVIA As String = "Se env\u00eda"
Public Const NO_SE_ENVIA As String = "No se env\u00eda"
Public Const SIN_PRODUCTOS As String = "Sin productos por pedir"

Public Type OrderRecord
    SupplierIndex As Long
    FirstLine As Long
    LineCount As Long
    Total As Currency
    Estado As String
End Type

Public Type OrderLine
    ProductIndex As Long
    Cantidad As Long
    Importe As Currency
End Type

Public Orders() As OrderRecord
Public OrderCount As Long
Public OrderLines() As OrderLine
Public OrderLineCount As Long

' orders.py: money. Centavos con redondeo hacia arriba en el medio.
Public Function Money(ByVal value As Double) As Currency
    Money = Int(CCur(value) * 100 + 0.5) / 100
End Function

Public Function NeedsOrder(ByRef product As ProductRecord) As Boolean
    NeedsOrder = product.Existencia < product.Minimo
End Function

' orders.py: order_quantity. Lo que falta para el maximo, al entero siguiente y luego
' hacia arriba al multiplo de empaque.
Public Function OrderQuantity(ByVal existencia As Double, ByVal maximo As Double, _
                              ByVal multiplo As Long) As Long
    Dim faltante As Double
    faltante = -Int(-(maximo - existencia))
    OrderQuantity = -Int(-faltante / multiplo) * multiplo
End Function

' orders.py: build_orders. Un pedido por proveedor (ordenados por ID) con sus productos
' ordenados por codigo; agrega las excepciones de pedido minimo no alcanzado.
Public Sub BuildOrders()
    Dim supplierOrder() As Long, productOrder() As Long, s As Long, p As Long, k As Long
    Dim minimo As Currency
    OrderCount = 0
    OrderLineCount = 0
    Erase Orders
    Erase OrderLines
    If SupplierCount = 0 Then Exit Sub

    supplierOrder = SortedSupplierIndexes()
    If ProductCount > 0 Then productOrder = SortedProductIndexes()
    ReDim Orders(1 To SupplierCount)
    If ProductCount > 0 Then ReDim OrderLines(1 To ProductCount)

    For s = 1 To SupplierCount
        OrderCount = OrderCount + 1
        With Orders(OrderCount)
            .SupplierIndex = supplierOrder(s)
            .FirstLine = OrderLineCount + 1
            For k = 1 To ProductCount
                p = productOrder(k)
                If Products(p).ProveedorId = Suppliers(.SupplierIndex).Id Then
                    If NeedsOrder(Products(p)) Then
                        OrderLineCount = OrderLineCount + 1
                        OrderLines(OrderLineCount).ProductIndex = p
                        OrderLines(OrderLineCount).Cantidad = OrderQuantity( _
                            Products(p).Existencia, Products(p).Maximo, Products(p).Multiplo)
                        OrderLines(OrderLineCount).Importe = _
                            Money(Products(p).Costo) * OrderLines(OrderLineCount).Cantidad
                        .Total = .Total + OrderLines(OrderLineCount).Importe
                        .LineCount = .LineCount + 1
                    End If
                End If
            Next k
            minimo = Money(Suppliers(.SupplierIndex).PedidoMinimo)
            If .LineCount = 0 Then
                .Estado = SIN_PRODUCTOS
            ElseIf .Total < minimo Then
                .Estado = NO_SE_ENVIA
                AddException SHEET_SUPPLIERS, Suppliers(.SupplierIndex).Fila, _
                    Suppliers(.SupplierIndex).Id, PEDIDO_MINIMO_NO_ALCANZADO, _
                    "Total $" & MoneyText(.Total, True) & U(" contra m\u00ednimo $") & _
                    MoneyText(minimo, True) & "; faltan $" & MoneyText(minimo - .Total, True), _
                    MoneyText(.Total, False)
            Else
                .Estado = SE_ENVIA
            End If
        End With
    Next s
End Sub

' f"{x:,.2f}" (con miles) o f"{x:.2f}" de Python, sin depender de la configuracion regional.
Public Function MoneyText(ByVal amount As Currency, ByVal thousands As Boolean) As String
    Dim cents As Currency, whole As String, fraction As String, sign As String, i As Long
    Dim grouped As String
    If amount < 0 Then
        sign = "-"
        amount = -amount
    End If
    cents = Int(amount * 100 + 0.5)
    whole = IntText(Int(cents / 100))
    fraction = Right$("0" & IntText(cents - Int(cents / 100) * 100), 2)
    If thousands Then
        For i = Len(whole) To 1 Step -1
            grouped = Mid$(whole, i, 1) & grouped
            If (Len(whole) - i + 1) Mod 3 = 0 And i > 1 Then grouped = "," & grouped
        Next i
        whole = grouped
    End If
    MoneyText = sign & whole & "." & fraction
End Function

Public Function OrderEstadoCount(ByVal estado As String) As Long
    Dim i As Long
    For i = 1 To OrderCount
        If Orders(i).Estado = estado Then OrderEstadoCount = OrderEstadoCount + 1
    Next i
End Function

Public Function TotalToBuy() As Currency
    Dim i As Long
    For i = 1 To OrderCount
        If Orders(i).Estado = SE_ENVIA Then TotalToBuy = TotalToBuy + Orders(i).Total
    Next i
End Function

Private Function SortedSupplierIndexes() As Long()
    Dim result() As Long, i As Long, j As Long, current As Long
    ReDim result(1 To SupplierCount)
    For i = 1 To SupplierCount
        current = i
        j = i - 1
        Do While j >= 1
            If StrComp(Suppliers(result(j)).Id, Suppliers(current).Id, vbBinaryCompare) <= 0 Then Exit Do
            result(j + 1) = result(j)
            j = j - 1
        Loop
        result(j + 1) = current
    Next i
    SortedSupplierIndexes = result
End Function

Private Function SortedProductIndexes() As Long()
    Dim result() As Long, i As Long, j As Long, current As Long
    ReDim result(1 To ProductCount)
    For i = 1 To ProductCount
        current = i
        j = i - 1
        Do While j >= 1
            If StrComp(Products(result(j)).Codigo, Products(current).Codigo, vbBinaryCompare) <= 0 Then Exit Do
            result(j + 1) = result(j)
            j = j - 1
        Loop
        result(j + 1) = current
    Next i
    SortedProductIndexes = result
End Function
