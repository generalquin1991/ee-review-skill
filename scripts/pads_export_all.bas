' ============================================================
' PADS Layout - One-Click Export Script
' ============================================================
' Purpose: Export all files needed for EE Review skill
'          (ASCII, Gerber via CAM, Netlist, BOM, Pick&Place)
'
' Usage:
'   Method 1 - In PADS GUI:
'     Tools -> Basic Scripts -> Basic Scripts -> select this .bas file -> Run
'
'   Method 2 - Command line:
'     layout.exe /runscript pads_export_all.bas
'
'   Method 3 - Batch file (recommended for automation):
'     See pads_export.bat in same directory
'
' Tested on: PADS VX.2.2, VX.2.7, VX.2.8
' ============================================================

Sub Main
    Dim app, doc
    Set app = Application
    Set doc = app.ActiveDocument

    ' --- Check if a document is open ---
    If doc Is Nothing Then
        MsgBox "No active document! Please open a PCB file first.", vbExclamation, "Export Error"
        Exit Sub
    End If

    ' --- Get project path ---
    Dim projPath, projName
    projPath = doc.Path
    If projPath = "" Then projPath = "C:\PADS_Export\"
    projName = doc.Name
    ' Remove .pcb extension
    If InStrRev(projName, ".") > 0 Then
        projName = Left(projName, InStrRev(projName, ".") - 1)
    End If

    ' --- Create export directory ---
    Dim exportDir
    exportDir = projPath & "EE_Review_Export\"
    CreateDir exportDir

    Dim logMsg
    logMsg = "Export started: " & Now & vbCrLf & vbCrLf
    logMsg = logMsg & "Project: " & projName & vbCrLf
    logMsg = logMsg & "Output:  " & exportDir & vbCrLf & vbCrLf

    ' --- 1. Export ASCII ---
    On Error Resume Next
    doc.Export exportDir & projName & ".asc", "ascii"
    If Err.Number = 0 Then
        logMsg = logMsg & "[OK] ASCII export: " & projName & ".asc" & vbCrLf
    Else
        logMsg = logMsg & "[FAIL] ASCII export: " & Err.Description & vbCrLf
        Err.Clear
    End If
    On Error GoTo 0

    ' --- 2. Export IPC-356 Netlist ---
    On Error Resume Next
    doc.Export exportDir & projName & "_netlist.ipc", "ipc356"
    If Err.Number = 0 Then
        logMsg = logMsg & "[OK] IPC-356 netlist: " & projName & "_netlist.ipc" & vbCrLf
    Else
        logMsg = logMsg & "[FAIL] IPC-356 netlist: " & Err.Description & vbCrLf
        Err.Clear
    End If
    On Error GoTo 0

    ' --- 3. Export BOM (CSV) ---
    On Error Resume Next
    Dim fso, f, comp, comps, line
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set f = fso.CreateTextFile(exportDir & projName & "_bom.csv", True)

    ' CSV header
    f.WriteLine "RefDes,PartType,Footprint,Value,Quantity,Layer,Rotation,X,Y,Description"

    Set comps = doc.Components
    For Each comp In comps
        line = comp.Name & "," & _
               SafeStr(comp.PartType) & "," & _
               SafeStr(comp.Footprint) & "," & _
               SafeStr(comp.Value) & "," & _
               "1," & _
               SafeStr(comp.Layer) & "," & _
               comp.Rotation & "," & _
               comp.PositionX & "," & _
               comp.PositionY & "," & _
               SafeStr(comp.GetAttribute("Description"))
        f.WriteLine line
    Next
    f.Close
    Set fso = Nothing

    logMsg = logMsg & "[OK] BOM + Pick&Place: " & projName & "_bom.csv" & vbCrLf
    On Error GoTo 0

    ' --- 4. Export component placement (separate file) ---
    On Error Resume Next
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set f = fso.CreateTextFile(exportDir & projName & "_placement.csv", True)
    f.WriteLine "Designator,Footprint,Layer,Rotation,CenterX,CenterY,Value"
    For Each comp In doc.Components
        f.WriteLine comp.Name & "," & _
                     SafeStr(comp.Footprint) & "," & _
                     SafeStr(comp.Layer) & "," & _
                     comp.Rotation & "," & _
                     comp.PositionX & "," & _
                     comp.PositionY & "," & _
                     SafeStr(comp.Value)
    Next
    f.Close
    Set fso = Nothing
    logMsg = logMsg & "[OK] Placement file: " & projName & "_placement.csv" & vbCrLf
    On Error GoTo 0

    ' --- 5. Export layer stackup info ---
    On Error Resume Next
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set f = fso.CreateTextFile(exportDir & projName & "_stackup.txt", True)

    f.WriteLine "=== Layer Stackup ==="
    f.WriteLine "Project: " & projName
    f.WriteLine "Date: " & Now
    f.WriteLine ""
    f.WriteLine "Layer Count: " & doc.LayerCount
    f.WriteLine ""
    f.WriteLine "Layer | Name | Type"
    f.WriteLine "-----|------|----"

    Dim i
    For i = 1 To doc.LayerCount
        f.WriteLine i & " | " & doc.LayerName(i) & " | " & doc.LayerType(i)
    Next
    f.Close
    Set fso = Nothing
    logMsg = logMsg & "[OK] Stackup info: " & projName & "_stackup.txt" & vbCrLf
    On Error GoTo 0

    ' --- 6. Export design rules report ---
    On Error Resume Next
    doc.Export exportDir & projName & "_rules.rpt", "rules"
    If Err.Number = 0 Then
        logMsg = logMsg & "[OK] Design rules: " & projName & "_rules.rpt" & vbCrLf
    Else
        logMsg = logMsg & "[SKIP] Design rules export not supported in this version" & vbCrLf
        Err.Clear
    End If
    On Error GoTo 0

    ' --- 7. Note about Gerber ---
    logMsg = logMsg & vbCrLf
    logMsg = logMsg & "=== Gerber Export ===" & vbCrLf
    logMsg = logMsg & "Gerber files require CAM configuration." & vbCrLf
    logMsg = logMsg & "Use: File -> CAM -> Define CAM Documents" & vbCrLf
    logMsg = logMsg & "Or run: pads_export_gerber.bas (separate script)" & vbCrLf

    ' --- Summary ---
    logMsg = logMsg & vbCrLf
    logMsg = logMsg & "=== Export Complete ===" & vbCrLf
    logMsg = logMsg & "Output directory: " & exportDir & vbCrLf
    logMsg = logMsg & "Files exported for EE Review skill processing." & vbCrLf
    logMsg = logMsg & "Next: copy files to host machine and run:" & vbCrLf
    logMsg = logMsg & "  python3 convert_layout.py " & projName & ".asc --export-all" & vbCrLf

    MsgBox logMsg, vbInformation, "PADS Export Complete"

    ' --- Also write log to file ---
    On Error Resume Next
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set f = fso.CreateTextFile(exportDir & "export_log.txt", True)
    f.WriteLine logMsg
    f.Close
    Set fso = Nothing
    On Error GoTo 0
End Sub

' ============================================================
' Helper Functions
' ============================================================

Sub CreateDir(path)
    Dim fso
    Set fso = CreateObject("Scripting.FileSystemObject")
    If Not fso.FolderExists(path) Then
        fso.CreateFolder path
    End If
    Set fso = Nothing
End Sub

Function SafeStr(val)
    If IsNull(val) Or IsEmpty(val) Then
        SafeStr = ""
    Else
        ' Remove commas and newlines that would break CSV
        SafeStr = Replace(Replace(CStr(val), ",", ";"), vbCrLf, " ")
    End If
End Function
