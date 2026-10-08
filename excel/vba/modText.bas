Attribute VB_Name = "modText"
' Textos con acentos. Los .bas van en ASCII porque el editor de VBA no importa bien UTF-8,
' asi que cada acento se escribe como \uXXXX y U() lo convierte: U("Revisi\u00f3n").
Option Explicit

Public Function U(ByVal text As String) As String
    Dim at As Long, result As String
    at = InStr(text, "\u")
    Do While at > 0
        result = result & Left$(text, at - 1) & ChrW$(CLng("&H" & Mid$(text, at + 2, 4)))
        text = Mid$(text, at + 6)
        at = InStr(text, "\u")
    Loop
    U = result & text
End Function

' --- Equivalentes de Python, para que los textos del reporte salgan identicos ---

' Python str.strip(): quita cualquier espacio en blanco, no solo el espacio comun.
Public Function PyStrip(ByVal text As String) As String
    PyStrip = PyRStrip(PyLStrip(text))
End Function

Public Function PyLStrip(ByVal text As String) As String
    Dim at As Long
    at = 1
    Do While at <= Len(text)
        If Not IsPyWhitespace(Mid$(text, at, 1)) Then Exit Do
        at = at + 1
    Loop
    PyLStrip = Mid$(text, at)
End Function

Public Function PyRStrip(ByVal text As String) As String
    Dim last As Long
    last = Len(text)
    Do While last > 0
        If Not IsPyWhitespace(Mid$(text, last, 1)) Then Exit Do
        last = last - 1
    Loop
    PyRStrip = Left$(text, last)
End Function

Public Function IsPyWhitespace(ByVal ch As String) As Boolean
    Select Case AscW(ch) And &HFFFF&
        Case 9 To 13, 28 To 32, 133, 160, 5760, 8192 To 8202, 8232, 8233, 8239, 8287, 12288
            IsPyWhitespace = True
    End Select
End Function

Public Function HasPyWhitespace(ByVal text As String) As Boolean
    Dim at As Long
    For at = 1 To Len(text)
        If IsPyWhitespace(Mid$(text, at, 1)) Then
            HasPyWhitespace = True
            Exit Function
        End If
    Next at
End Function

' resurtido/validation.py: is_blank
Public Function IsBlank(ByVal value As Variant) As Boolean
    If IsEmpty(value) Or IsNull(value) Then
        IsBlank = True
    ElseIf VarType(value) = vbString Then
        IsBlank = Len(PyStrip(value)) = 0
    End If
End Function

' resurtido/validation.py: is_number (los booleanos y las fechas no cuentan)
Public Function IsNum(ByVal value As Variant) As Boolean
    Select Case VarType(value)
        Case vbInteger, vbLong, vbSingle, vbDouble, vbCurrency, vbDecimal, vbByte, 20
            IsNum = True
    End Select
End Function

' resurtido/validation.py: as_text
Public Function AsText(ByVal value As Variant) As String
    If Not IsBlank(value) Then AsText = PyStr(value)
End Function

' str(valor) tal como lo lee pandas desde el Excel: un numero entero sale sin decimales
' (openpyxl lo entrega como int) y uno con decimales como float de Python.
Public Function PyStr(ByVal value As Variant) As String
    If IsEmpty(value) Or IsNull(value) Then Exit Function
    Select Case VarType(value)
        Case vbString
            PyStr = value
        Case vbBoolean
            PyStr = IIf(value, "True", "False")
        Case vbDate
            PyStr = Format$(value, "yyyy-mm-dd hh:nn:ss")
        Case Else
            If IsNum(value) Then
                If CDbl(value) = Int(CDbl(value)) And Abs(CDbl(value)) < 1E+15 Then
                    PyStr = IntText(CDbl(value))
                Else
                    PyStr = FloatRepr(CDbl(value))
                End If
            Else
                PyStr = CStr(value)
            End If
    End Select
End Function

Public Function IntText(ByVal number As Double) As String
    IntText = Format$(number, "0")
End Function

' repr(float) de Python: 60.0, 0.5, 1e-05. Str$ siempre usa punto decimal.
Public Function FloatRepr(ByVal number As Double) As String
    Dim text As String
    If number = Int(number) And Abs(number) < 1E+16 Then
        FloatRepr = IntText(number) & ".0"
        Exit Function
    End If
    text = Trim$(Str$(number))
    If Left$(text, 1) = "." Then text = "0" & text
    If Left$(text, 2) = "-." Then text = "-0" & Mid$(text, 2)
    FloatRepr = LCase$(text)
End Function

' f"{x:g}" de Python: 6 cifras significativas, sin ceros de sobra.
Public Function FormatG(ByVal number As Double) As String
    Dim sign As String, exponent As Long, digits As Double, text As String, mantissa As String
    If number = 0 Then
        FormatG = "0"
        Exit Function
    End If
    If number < 0 Then sign = "-"
    number = Abs(number)
    exponent = Int(Log(number) / Log(10#))
    If number / 10# ^ exponent >= 10# Then exponent = exponent + 1
    If number / 10# ^ exponent < 1# Then exponent = exponent - 1
    digits = Int(number / 10# ^ (exponent - 5) + 0.5)
    If digits >= 1000000# Then
        digits = digits / 10#
        exponent = exponent + 1
    End If
    text = IntText(digits)
    If exponent >= -4 And exponent < 6 Then
        If exponent >= 0 Then
            mantissa = Left$(text, exponent + 1) & "." & Mid$(text, exponent + 2)
        Else
            mantissa = "0." & String$(-exponent - 1, "0") & text
        End If
        FormatG = sign & TrimZeros(mantissa)
    Else
        FormatG = sign & TrimZeros(Left$(text, 1) & "." & Mid$(text, 2)) & "e" & _
            IIf(exponent < 0, "-", "+") & Right$("0" & CStr(Abs(exponent)), 2)
    End If
End Function

Private Function TrimZeros(ByVal text As String) As String
    If InStr(text, ".") > 0 Then
        Do While Right$(text, 1) = "0"
            text = Left$(text, Len(text) - 1)
        Loop
        If Right$(text, 1) = "." Then text = Left$(text, Len(text) - 1)
    End If
    TrimZeros = text
End Function

' f"{x:.2f}" (o f"{x:,.2f}") de un float de Python: redondea el valor binario exacto, no
' el decimal escrito. 0.105 es 0.10499... en binario y sale "0.10"; 0.125 es exacto y
' empata, y Python lo deja par: "0.12". x * 100 se calcula sin perder el error de
' redondeo (producto exacto de Dekker), y ese error decide los casos de en medio.
Public Function PyFixed2(ByVal number As Double, ByVal thousands As Boolean) As String
    Dim sign As String, scaled As Double, splitter As Double, high As Double, low As Double
    Dim exact As Double, rest As Double, cents As Double, fraction As Double
    If number < 0 Then
        sign = "-"
        number = -number
    End If
    scaled = number * 100#
    splitter = 134217729# * number
    high = splitter - (splitter - number)
    low = number - high
    exact = high * 100#
    rest = exact - scaled
    rest = rest + low * 100#
    cents = Int(scaled)
    fraction = scaled - cents
    If fraction > 0.5 Then
        cents = cents + 1
    ElseIf fraction = 0.5 Then
        If rest > 0 Or (rest = 0 And cents - Int(cents / 2) * 2 = 1) Then cents = cents + 1
    End If
    PyFixed2 = sign & MoneyText(CCur(cents) / 100, thousands)
End Function

' repr(str) de Python: comillas simples salvo que el texto traiga una y ninguna doble.
Public Function PyRepr(ByVal text As String) As String
    Dim quote As String, result As String, at As Long, ch As String
    If InStr(text, "'") > 0 And InStr(text, """") = 0 Then quote = """" Else quote = "'"
    For at = 1 To Len(text)
        ch = Mid$(text, at, 1)
        Select Case ch
            Case "\": result = result & "\\"
            Case vbTab: result = result & "\t"
            Case vbLf: result = result & "\n"
            Case vbCr: result = result & "\r"
            Case quote: result = result & "\" & quote
            Case Else: result = result & ch
        End Select
    Next at
    PyRepr = quote & result & quote
End Function

' Texto de un valor de error de Excel, como lo entrega openpyxl.
Public Function ErrorText(ByVal value As Variant) As String
    Select Case True
        Case value = CVErr(2042): ErrorText = "#N/A"
        Case value = CVErr(2007): ErrorText = "#DIV/0!"
        Case value = CVErr(2015): ErrorText = "#VALUE!"
        Case value = CVErr(2023): ErrorText = "#REF!"
        Case value = CVErr(2029): ErrorText = "#NAME?"
        Case value = CVErr(2036): ErrorText = "#NUM!"
        Case value = CVErr(2000): ErrorText = "#NULL!"
        Case Else: ErrorText = "#ERROR"
    End Select
End Function
