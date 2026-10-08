Attribute VB_Name = "modEmails"
' Borradores de correo por proveedor (resurtido/emails.py). Nunca se envian: solo se
' escriben archivos .eml, byte por byte en UTF-8, y el indice interno indice.csv. Leen
' Resumen y Detalle tal como estan, con las cantidades que el comprador haya ajustado.
Option Explicit

Public Const EMAILS_DIR As String = "correos"
Public Const INDEX_FILE As String = "indice.csv"
Private Const COMPANY As String = "Ferretera Garza"

' Escribe un .eml por pedido que se envia y el indice en `folder` (la crea si no existe).
' Regresa cuantos borradores escribio.
Public Function WriteDrafts(ByVal folder As String, ByVal orderDate As Date) As Long
    Dim summary As Worksheet, row As Long, id As String, estado As String, filename As String
    Dim index As String, lines As Collection, revisar As String, total As Currency
    Application.Calculate
    Set summary = ThisWorkbook.Worksheets(SHEET_SUMMARY)
    EnsureFolder folder
    ' Un borrador viejo de un proveedor que ya no tiene pedido podria enviarse por error.
    DeleteOldDrafts folder

    index = CsvLine(Array("proveedor_id", "proveedor", "correo", "estado", "archivo", _
        "productos", "total_mxn", "revisar_antes_de_enviar"))
    row = 2
    Do While Len(CellText(summary.Cells(row, 1).Value)) > 0
        id = CellText(summary.Cells(row, 1).Value)
        estado = CellText(summary.Cells(row, 7).Value)
        If estado = U(SE_ENVIA) Or estado = U(NO_SE_ENVIA) Then
            Set lines = DetailLines(id, revisar)
            total = Money(CDbl(summary.Cells(row, 5).Value))
            filename = ""
            If estado = U(SE_ENVIA) Then
                filename = DraftFilename(id, CellText(summary.Cells(row, 2).Value))
                WriteUtf8File JoinPath(folder, filename), DraftMessage( _
                    CellText(summary.Cells(row, 2).Value), CellText(summary.Cells(row, 3).Value), _
                    lines, total, orderDate), False
                WriteDrafts = WriteDrafts + 1
            End If
            index = index & CsvLine(Array(id, CellText(summary.Cells(row, 2).Value), _
                CellText(summary.Cells(row, 3).Value), estado, filename, CStr(lines.Count), _
                MoneyText(total, False), revisar))
        End If
        row = row + 1
    Loop
    WriteUtf8File JoinPath(folder, INDEX_FILE), index, True
End Function

' Renglones de Detalle del proveedor con cantidad mayor que cero, en el orden de la hoja.
' Cada elemento es Array(codigo, descripcion, cantidad, costo, importe). `revisar` regresa
' los codigos marcados para revisar, separados por "; ".
Private Function DetailLines(ByVal id As String, ByRef revisar As String) As Collection
    Dim detail As Worksheet, row As Long, quantity As Variant
    Set DetailLines = New Collection
    Set detail = ThisWorkbook.Worksheets(SHEET_DETAIL)
    revisar = ""
    row = 2
    Do While Len(CellText(detail.Cells(row, 1).Value)) > 0
        If CellText(detail.Cells(row, 1).Value) = id Then
            quantity = detail.Cells(row, 9).Value
            If IsNum(quantity) Then
                If quantity > 0 Then
                    DetailLines.Add Array(CellText(detail.Cells(row, 3).Value), _
                        CellText(detail.Cells(row, 4).Value), PyStr(quantity), _
                        CDbl(detail.Cells(row, 10).Value), Money(CDbl(detail.Cells(row, 11).Value)))
                    If CellText(detail.Cells(row, 13).Value) = U("S\u00ed") Then
                        revisar = revisar & IIf(Len(revisar) > 0, "; ", "") & _
                            CellText(detail.Cells(row, 3).Value)
                    End If
                End If
            End If
        End If
        row = row + 1
    Loop
End Function

Private Function CellText(ByVal value As Variant) As String
    If IsError(value) Then
        CellText = ErrorText(value)
    Else
        CellText = PyStr(value)
    End If
End Function

' emails.py: build_draft. Mismo orden de encabezados y fin de linea LF que EmailMessage.
Public Function DraftMessage(ByVal nombre As String, ByVal correo As String, _
                             ByVal lines As Collection, ByVal total As Currency, _
                             ByVal orderDate As Date) As String
    DraftMessage = "To: " & correo & vbLf & _
        "Subject: Pedido de resurtido " & COMPANY & " - " & Format$(orderDate, "yyyy-mm-dd") & vbLf & _
        "X-Unsent: 1" & vbLf & _
        "Content-Type: text/plain; charset=""utf-8""" & vbLf & _
        "Content-Transfer-Encoding: 8bit" & vbLf & _
        "MIME-Version: 1.0" & vbLf & vbLf & _
        DraftBody(nombre, lines, total, orderDate)
End Function

' emails.py: draft_body. La tabla va alineada con espacios para leerse en texto plano.
Public Function DraftBody(ByVal nombre As String, ByVal lines As Collection, _
                          ByVal total As Currency, ByVal orderDate As Date) As String
    Dim rows() As Variant, widths(0 To 4) As Long, dashes(0 To 4) As String
    Dim i As Long, c As Long, item As Variant, table As String, first As String, totalLine As String
    ReDim rows(0 To lines.Count)
    rows(0) = Array(U("C\u00f3digo"), U("Descripci\u00f3n"), "Cantidad", "Costo unitario", "Importe")
    i = 0
    For Each item In lines
        i = i + 1
        rows(i) = Array(item(0), item(1), item(2), "$" & PyFixed2(item(3), True), _
            "$" & MoneyText(item(4), True))
    Next item
    For i = 0 To lines.Count
        For c = 0 To 4
            If Len(rows(i)(c)) > widths(c) Then widths(c) = Len(rows(i)(c))
        Next c
    Next i
    For c = 0 To 4
        dashes(c) = String$(widths(c), "-")
    Next c

    first = FormatRow(rows(0), widths)
    table = first & vbLf & FormatRow(dashes, widths) & vbLf
    For i = 1 To lines.Count
        table = table & FormatRow(rows(i), widths) & vbLf
    Next i
    totalLine = "Total del pedido: $" & MoneyText(total, True)
    If Len(totalLine) < Len(first) Then totalLine = Space$(Len(first) - Len(totalLine)) & totalLine
    table = table & totalLine & vbLf

    DraftBody = "Estimado equipo de " & nombre & ":" & vbLf & vbLf & _
        "Les compartimos nuestro pedido de resurtido del " & LongDate(orderDate) & ":" & vbLf & vbLf & _
        table & vbLf & _
        "Les pedimos confirmar por este medio las cantidades y la fecha de entrega" & _
        " de cada producto." & vbLf & vbLf & _
        "Saludos," & vbLf & "Compras" & vbLf & COMPANY & vbLf
End Function

' Codigo y descripcion a la izquierda, numeros a la derecha, dos espacios entre columnas.
Private Function FormatRow(ByVal row As Variant, ByRef widths() As Long) As String
    Dim c As Long, cell As String, result As String
    For c = 0 To 4
        cell = row(c)
        If Len(cell) < widths(c) Then
            If c < 2 Then
                cell = cell & Space$(widths(c) - Len(cell))
            Else
                cell = Space$(widths(c) - Len(cell)) & cell
            End If
        End If
        If c > 0 Then result = result & "  "
        result = result & cell
    Next c
    FormatRow = PyRStrip(result)
End Function

' emails.py: long_date. "7 de octubre de 2026", sin depender de la configuracion regional.
Public Function LongDate(ByVal orderDate As Date) As String
    Dim months As Variant
    months = Array("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", _
        "agosto", "septiembre", "octubre", "noviembre", "diciembre")
    LongDate = Day(orderDate) & " de " & months(Month(orderDate) - 1) & " de " & Year(orderDate)
End Function

' emails.py: draft_filename. P01_distribuidora-truper-norte.eml
Public Function DraftFilename(ByVal id As String, ByVal nombre As String) As String
    DraftFilename = id & "_" & Slugify(nombre) & ".eml"
End Function

' emails.py: slugify. Quita los acentos (lo que NFKD descompone en letra + acento), tira
' el resto de lo que no es ASCII y junta lo que no es letra o numero en un guion.
Public Function Slugify(ByVal text As String) As String
    Dim accented As String, plain As String, i As Long, ch As String, at As Long
    Dim ascii As String, result As String, pendingDash As Boolean
    accented = U("\u00e1\u00e0\u00e2\u00e4\u00e3\u00e5\u00e9\u00e8\u00ea\u00eb\u00ed\u00ec\u00ee\u00ef" & _
        "\u00f3\u00f2\u00f4\u00f6\u00f5\u00fa\u00f9\u00fb\u00fc\u00f1\u00e7\u00fd\u00ff" & _
        "\u00c1\u00c0\u00c2\u00c4\u00c3\u00c5\u00c9\u00c8\u00ca\u00cb\u00cd\u00cc\u00ce\u00cf" & _
        "\u00d3\u00d2\u00d4\u00d6\u00d5\u00da\u00d9\u00db\u00dc\u00d1\u00c7\u00dd")
    plain = "aaaaaaeeeeiiiiooooouuuuncyy" & "AAAAAAEEEEIIIIOOOOOUUUUNCY"
    For i = 1 To Len(text)
        ch = Mid$(text, i, 1)
        If (AscW(ch) And &HFFFF&) < 128 Then
            ascii = ascii & ch
        Else
            at = InStr(1, accented, ch, vbBinaryCompare)
            If at > 0 Then ascii = ascii & Mid$(plain, at, 1)
        End If
    Next i
    ascii = LCase$(ascii)
    For i = 1 To Len(ascii)
        ch = Mid$(ascii, i, 1)
        If (ch >= "a" And ch <= "z") Or (ch >= "0" And ch <= "9") Then
            If pendingDash And Len(result) > 0 Then result = result & "-"
            pendingDash = False
            result = result & ch
        Else
            pendingDash = True
        End If
    Next i
    Slugify = result
End Function

Private Sub EnsureFolder(ByVal folder As String)
    If Len(Dir(folder, vbDirectory)) = 0 Then MkDir folder
End Sub

' Dir con comodines no funciona en Mac: se listan todos y se filtra por extension. Como
' glob("*.eml") de Python: sensible a mayusculas y sin archivos ocultos.
Private Sub DeleteOldDrafts(ByVal folder As String)
    Dim name As String, found As New Collection, item As Variant
    name = Dir(JoinPath(folder, ""))
    Do While Len(name) > 0
        If Right$(name, 4) = ".eml" And Left$(name, 1) <> "." Then found.Add name
        name = Dir()
    Loop
    For Each item In found
        Kill JoinPath(folder, CStr(item))
    Next item
End Sub
