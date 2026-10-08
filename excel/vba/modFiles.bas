Attribute VB_Name = "modFiles"
' Escritura de archivos de texto en UTF-8, byte por byte. ADODB.Stream no existe en Mac.
Option Explicit

' Bitacora de diagnostico: si TracePath tiene ruta, Trace agrega una linea con el tiempo.
Public TracePath As String

Public Function Utf8Bytes(ByVal text As String) As Byte()
    Dim result() As Byte, size As Long, at As Long, code As Long, low As Long
    If Len(text) = 0 Then
        Utf8Bytes = result
        Exit Function
    End If
    ReDim result(0 To Len(text) * 4 - 1)
    at = 1
    Do While at <= Len(text)
        code = AscW(Mid$(text, at, 1)) And &HFFFF&
        If code >= &HD800& And code <= &HDBFF& And at < Len(text) Then
            low = AscW(Mid$(text, at + 1, 1)) And &HFFFF&
            If low >= &HDC00& And low <= &HDFFF& Then
                code = &H10000 + (code - &HD800&) * &H400& + (low - &HDC00&)
                at = at + 1
            End If
        End If
        If code < &H80& Then
            result(size) = code
            size = size + 1
        ElseIf code < &H800& Then
            result(size) = &HC0& Or (code \ &H40&)
            result(size + 1) = &H80& Or (code And &H3F&)
            size = size + 2
        ElseIf code < &H10000 Then
            result(size) = &HE0& Or (code \ &H1000&)
            result(size + 1) = &H80& Or ((code \ &H40&) And &H3F&)
            result(size + 2) = &H80& Or (code And &H3F&)
            size = size + 3
        Else
            result(size) = &HF0& Or (code \ &H40000)
            result(size + 1) = &H80& Or ((code \ &H1000&) And &H3F&)
            result(size + 2) = &H80& Or ((code \ &H40&) And &H3F&)
            result(size + 3) = &H80& Or (code And &H3F&)
            size = size + 4
        End If
        at = at + 1
    Loop
    ReDim Preserve result(0 To size - 1)
    Utf8Bytes = result
End Function

' Reemplaza el archivo. Con BOM, Excel en Windows abre bien los acentos de un CSV.
Public Sub WriteUtf8File(ByVal path As String, ByVal text As String, ByVal withBom As Boolean)
    Dim handle As Integer, bytes() As Byte, bom(0 To 2) As Byte
    DeleteFile path
    handle = FreeFile
    Open path For Binary Access Write As #handle
    If withBom Then
        bom(0) = &HEF
        bom(1) = &HBB
        bom(2) = &HBF
        Put #handle, , bom
    End If
    If Len(text) > 0 Then
        bytes = Utf8Bytes(text)
        Put #handle, , bytes
    End If
    Close #handle
End Sub

Public Sub DeleteFile(ByVal path As String)
    On Error Resume Next
    If Len(Dir(path)) > 0 Then Kill path
End Sub

Public Function JoinPath(ByVal folder As String, ByVal name As String) As String
    If Right$(folder, 1) = Application.PathSeparator Then
        JoinPath = folder & name
    Else
        JoinPath = folder & Application.PathSeparator & name
    End If
End Function

' Un renglon de CSV como lo escribe csv.writer de Python (QUOTE_MINIMAL, fin de linea CRLF).
Public Function CsvLine(ByVal fields As Variant) As String
    Dim i As Long, field As String, line As String
    For i = LBound(fields) To UBound(fields)
        field = fields(i)
        If InStr(field, ",") > 0 Or InStr(field, """") > 0 Or InStr(field, vbCr) > 0 _
           Or InStr(field, vbLf) > 0 Then
            field = """" & Replace(field, """", """""") & """"
        End If
        If i > LBound(fields) Then line = line & ","
        line = line & field
    Next i
    CsvLine = line & CRLF()
End Function

' vbCrLf en Excel para Mac escribe LF+CR (al reves); el fin de linea se arma a mano.
Public Function CRLF() As String
    CRLF = Chr$(13) & Chr$(10)
End Function


Public Sub Trace(ByVal message As String)
    Dim handle As Integer
    If Len(TracePath) = 0 Then Exit Sub
    handle = FreeFile
    Open TracePath For Append As #handle
    Print #handle, Format$(Timer, "0.00") & " " & message
    Close #handle
End Sub
