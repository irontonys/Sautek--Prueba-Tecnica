Attribute VB_Name = "modUI"
' Lo que hace cada boton de la hoja Inicio.
Option Explicit

Public Sub LoadInventory()
    Dim path As Variant, outcome As String
    If HasLoadedData() Then
        If MsgBox(U("Ya hay un inventario cargado. Si cargas otro, se reemplazan los datos y " & _
                    "se pierden las correcciones que hiciste." & vbLf & vbLf & "\u00bfContinuar?"), _
                  vbYesNo + vbExclamation, APP_TITLE) <> vbYes Then Exit Sub
    End If
    path = ChooseInventoryFile()
    If VarType(path) = vbBoolean Then Exit Sub

    outcome = LoadFrom(CStr(path))
    If Left$(outcome, 3) = "OK " Then
        ThisWorkbook.Worksheets(SHEET_HOME).Activate
        MsgBox "Inventario cargado." & vbLf & Mid$(outcome, 4) & vbLf & vbLf & _
               "Siguiente paso: Revisar datos.", vbInformation, APP_TITLE
    Else
        MsgBox Mid$(outcome, Len("ERROR: ") + 1), vbExclamation, APP_TITLE
    End If
End Sub

' Para la prueba de paridad: la misma secuencia que los botones, sin dialogos. Recibe la
' ruta del inventario, la carpeta de salida y la fecha (aaaa-mm-dd); regresa "OK ..." o "ERROR: ...".
Public Function RunHeadless(ByVal inputPath As String, ByVal outputDir As String, _
                            ByVal isoDate As String) As String
    Dim outcome As String, emails As Long
    On Error GoTo Failed
    outcome = LoadFrom(inputPath)
    If Left$(outcome, 3) <> "OK " Then
        RunHeadless = outcome
        Exit Function
    End If
    outcome = ReviewCore()
    BuildOrders
    SortExceptions
    WriteExceptionsCsv outputDir
    WriteOrdersCsv outputDir
    WriteOrderSheets
    emails = WriteDrafts(JoinPath(outputDir, EMAILS_DIR), _
        DateSerial(CLng(Left$(isoDate, 4)), CLng(Mid$(isoDate, 6, 2)), CLng(Right$(isoDate, 2))))
    RunHeadless = "OK leidos=" & RowsRead & " repetidos=" & RepeatedCount & _
        " procesables=" & ProductCount & " no_procesables=" & ExcludedCount & _
        " excepciones=" & ExceptionCount & " se_envian=" & OrderEstadoCount(SE_ENVIA) & _
        " no_se_envian=" & OrderEstadoCount(NO_SE_ENVIA) & " total=" & MoneyText(TotalToBuy(), False) & " correos=" & emails
    Exit Function
Failed:
    RunHeadless = "ERROR: " & Err.Description & " (" & Err.Number & ")"
End Function

Public Sub ReviewData()
    Dim outcome As String
    On Error GoTo Failed
    If Not HasLoadedData() Then
        MsgBox "Primero carga el inventario (paso 1).", vbExclamation, APP_TITLE
        Exit Sub
    End If
    outcome = ReviewCore()
    ThisWorkbook.Worksheets(SHEET_EXCEPTIONS).Activate
    MsgBox ReviewSummary() & vbLf & vbLf & _
        U("Corrige en las hojas de datos lo que haga falta y vuelve a dar Revisar datos. " & _
          "Cuando est\u00e9 listo, sigue con Preparar pedidos."), vbInformation, APP_TITLE
    Exit Sub
Failed:
    ReportFailure "Revisar datos"
End Sub

' Un error inesperado se explica en un mensaje en lugar de abrir el editor de VBA.
Private Sub ReportFailure(ByVal stepName As String)
    Application.ScreenUpdating = True
    MsgBox U("Ocurri\u00f3 un error en ") & stepName & ": " & Err.Description & _
        " (" & Err.Number & ")", vbCritical, APP_TITLE
End Sub

' Valida los datos actuales y reescribe Excepciones, Correcciones y el estado de Inicio.
' Los pedidos anteriores dejan de valer: se borran hasta volver a prepararlos.
Public Function ReviewCore() As String
    Dim corrections As Long
    Application.ScreenUpdating = False
    Trace "revisar: validar"
    Validate
    Trace "revisar: hoja Excepciones"
    WriteExceptionsSheet
    Trace "revisar: hoja Correcciones"
    corrections = WriteCorrectionsSheet()
    Trace "revisar: estado"
    ClearTable ThisWorkbook.Worksheets(SHEET_SUMMARY)
    ClearTable ThisWorkbook.Worksheets(SHEET_DETAIL)
    ClearSignature
    SetReviewStatus corrections
    SetStatus "StatusOrders", "Pendiente"
    SetStatus "StatusEmails", "Pendiente"
    Application.ScreenUpdating = True
    Trace "revisar: listo"
    ReviewCore = "OK excepciones=" & ExceptionCount & " correcciones=" & corrections
End Function

' Para pruebas: ReviewCore con manejo de errores (un error regresa como texto, sin "break").
Public Function ReviewHeadless() As String
    On Error GoTo Failed
    ReviewHeadless = ReviewCore()
    Exit Function
Failed:
    Application.ScreenUpdating = True
    ReviewHeadless = "ERROR: " & Err.Description & " (" & Err.Number & ")"
End Function

' Diagnostico: carga y revisa escribiendo una bitacora de tiempos en logPath.
Public Function DebugReview(ByVal inputPath As String, ByVal logPath As String) As String
    On Error GoTo Failed
    TracePath = logPath
    Trace "inicio"
    DebugReview = LoadFrom(inputPath)
    Trace "cargado: " & DebugReview
    DebugReview = DebugReview & " | " & ReviewCore()
    TracePath = ""
    Exit Function
Failed:
    DebugReview = "ERROR: " & Err.Description & " (" & Err.Number & ")"
    Trace DebugReview
    TracePath = ""
    Application.ScreenUpdating = True
End Function

Private Sub SetReviewStatus(ByVal corrections As Long)
    SetStatus "StatusReviewed", Format$(Now, "yyyy-mm-dd hh:nn") & " - " & RowsRead & _
        U(" renglones le\u00eddos: ") & ProductCount & " procesables, " & ExcludedCount & _
        " no procesables, " & RepeatedCount & " repetidos; " & corrections & _
        IIf(corrections = 1, U(" correcci\u00f3n a mano"), " correcciones a mano")
    SetStatus "StatusExceptions", ReviewSummary()
End Sub

Public Sub PrepareOrders()
    On Error GoTo Failed
    If Not HasLoadedData() Then
        MsgBox "Primero carga el inventario (paso 1).", vbExclamation, APP_TITLE
        Exit Sub
    End If
    PrepareCore
    ThisWorkbook.Worksheets(SHEET_SUMMARY).Activate
    MsgBox OrdersSummary() & vbLf & vbLf & _
        U("En Detalle puedes ajustar la Cantidad (celdas amarillas); el importe, el total y " & _
          "el estado se recalculan solos. Cuando est\u00e9 listo, sigue con Generar correos."), _
        vbInformation, APP_TITLE
    Exit Sub
Failed:
    ReportFailure "Preparar pedidos"
End Sub

' Valida los datos actuales, calcula los pedidos, escribe Resumen y Detalle y guarda la
' firma de los datos para que Generar correos sepa si cambiaron despues.
Public Function PrepareCore() As String
    Dim corrections As Long
    Application.ScreenUpdating = False
    Validate
    BuildOrders
    SortExceptions
    WriteExceptionsSheet
    corrections = WriteCorrectionsSheet()
    WriteOrderSheets
    SaveSignature DataSignature()
    SetReviewStatus corrections
    SetStatus "StatusOrders", Format$(Now, "yyyy-mm-dd hh:nn") & " - " & OrdersSummary()
    SetStatus "StatusEmails", "Pendiente"
    Application.ScreenUpdating = True
    PrepareCore = "OK se_envian=" & OrderEstadoCount(SE_ENVIA) & " no_se_envian=" & _
        OrderEstadoCount(NO_SE_ENVIA) & " total=" & MoneyText(TotalToBuy(), False)
End Function

' Para pruebas: PrepareCore con manejo de errores.
Public Function PrepareHeadless() As String
    On Error GoTo Failed
    PrepareHeadless = PrepareCore()
    Exit Function
Failed:
    Application.ScreenUpdating = True
    PrepareHeadless = "ERROR: " & Err.Description & " (" & Err.Number & ")"
End Function

Private Function OrdersSummary() As String
    Dim sent As Long, notSent As Long, i As Long, names As String
    sent = OrderEstadoCount(SE_ENVIA)
    notSent = OrderEstadoCount(NO_SE_ENVIA)
    For i = 1 To OrderCount
        If Orders(i).Estado = NO_SE_ENVIA Then
            names = names & IIf(Len(names) > 0, ", ", "") & Suppliers(Orders(i).SupplierIndex).Id
        End If
    Next i
    OrdersSummary = sent & U(" pedidos se env\u00edan por $") & MoneyText(TotalToBuy(), True)
    If notSent > 0 Then
        OrdersSummary = OrdersSummary & "; " & notSent & U(" no llegan al pedido m\u00ednimo (") & names & ")"
    End If
End Function

Private Function ReviewSummary() As String
    Dim i As Long, counts(0 To 3) As Long, groups As Variant, labels As Variant, k As Long
    groups = Array(GROUP_CORRECTED, GROUP_WARNING, GROUP_EXCLUDED, GROUP_PURCHASE)
    labels = Array(U("se corrigieron solas"), "advertencias", U("no se procesaron"), "de compra")
    For i = 1 To ExceptionCount
        For k = 0 To 3
            If ExceptionGroup(Exceptions(i).Tipo) = groups(k) Then counts(k) = counts(k) + 1
        Next k
    Next i
    ReviewSummary = ExceptionCount & " excepciones: "
    For k = 0 To 3
        ReviewSummary = ReviewSummary & counts(k) & " " & labels(k) & IIf(k < 3, ", ", "")
    Next k
End Function


Public Sub GenerateEmails()
    Dim folder As String, outcome As String
    On Error GoTo Failed
    If Not HasLoadedData() Then
        MsgBox "Primero carga el inventario (paso 1).", vbExclamation, APP_TITLE
        Exit Sub
    End If
    If Len(ThisWorkbook.Path) = 0 Then
        MsgBox U("Guarda primero el libro: los correos se escriben en la carpeta correos, " & _
            "junto a \u00e9l."), vbExclamation, APP_TITLE
        Exit Sub
    End If
    folder = JoinPath(ThisWorkbook.Path, EMAILS_DIR)
    outcome = CheckReadyForEmails()
    If Len(outcome) > 0 Then
        MsgBox outcome, vbExclamation, APP_TITLE
        Exit Sub
    End If
    If Not GrantFolderAccess(folder) Then
        MsgBox U("Excel no tiene permiso para escribir en ") & folder & U(". No se escribi\u00f3 nada."), _
            vbExclamation, APP_TITLE
        Exit Sub
    End If
    outcome = GenerateCore(folder, Date)
    If Left$(outcome, 3) = "OK " Then
        MsgBox Mid$(outcome, 4) & vbLf & vbLf & U("Est\u00e1n en ") & folder & vbLf & _
            U("\u00c1brelos con doble clic, rev\u00edsalos y env\u00edalos desde tu correo. " & _
              "Nada se envi\u00f3 desde el libro."), vbInformation, APP_TITLE
    Else
        MsgBox Mid$(outcome, InStr(outcome, " ") + 1), vbExclamation, APP_TITLE
    End If
    Exit Sub
Failed:
    ReportFailure "Generar correos"
End Sub

' Escribe los borradores en `folder` si los pedidos estan preparados con los datos actuales.
' Regresa "OK <resumen>" o "AVISO: <motivo>"; si avisa, no escribe ni borra nada.
Public Function GenerateCore(ByVal folder As String, ByVal orderDate As Date) As String
    Dim problem As String, count As Long
    problem = CheckReadyForEmails()
    If Len(problem) > 0 Then
        GenerateCore = "AVISO: " & problem
        Exit Function
    End If
    count = WriteDrafts(folder, orderDate)
    SetStatus "StatusEmails", Format$(Now, "yyyy-mm-dd hh:nn") & " - " & count & _
        IIf(count = 1, " borrador", " borradores") & " en " & folder & " (sin enviar)"
    GenerateCore = "OK " & U(IIf(count = 1, "Se escribi\u00f3 1 borrador", _
        "Se escribieron " & count & " borradores") & " de correo, uno por pedido que se env\u00eda.")
End Function

' Para pruebas: GenerateCore con manejo de errores.
Public Function GenerateHeadless(ByVal folder As String, ByVal isoDate As String) As String
    On Error GoTo Failed
    GenerateHeadless = GenerateCore(folder, DateSerial(CLng(Left$(isoDate, 4)), _
        CLng(Mid$(isoDate, 6, 2)), CLng(Right$(isoDate, 2))))
    Exit Function
Failed:
    GenerateHeadless = "ERROR: " & Err.Description & " (" & Err.Number & ")"
End Function

' Vacio si se puede generar; si no, el motivo para el comprador.
Private Function CheckReadyForEmails() As String
    Dim stored As String
    stored = StoredSignature()
    If Len(stored) = 0 Then
        CheckReadyForEmails = "Primero da Preparar pedidos (paso 3)."
    ElseIf stored <> DataSignature() Then
        CheckReadyForEmails = U("Los datos cambiaron despu\u00e9s de preparar los pedidos. " & _
            "Da Preparar pedidos de nuevo para que los correos lleven las cantidades correctas. " & _
            "No se escribi\u00f3 ni se borr\u00f3 ning\u00fan archivo.")
    End If
End Function

' Excel para Mac corre en sandbox: pide permiso para la carpeta del libro y la de correos.
Private Function GrantFolderAccess(ByVal folder As String) As Boolean
#If Mac Then
    GrantFolderAccess = GrantAccessToMultipleFiles(Array(ThisWorkbook.Path, folder))
#Else
    GrantFolderAccess = True
#End If
End Function

' Regresa la ruta elegida o False si se cancela. En Mac el filtro de tipos no aplica.
Private Function ChooseInventoryFile() As Variant
#If Mac Then
    ChooseInventoryFile = Application.GetOpenFilename()
#Else
    ChooseInventoryFile = Application.GetOpenFilename( _
        "Libros de Excel (*.xlsx;*.xlsm;*.xls),*.xlsx;*.xlsm;*.xls", , "Elige el Excel de inventario")
#End If
End Function

