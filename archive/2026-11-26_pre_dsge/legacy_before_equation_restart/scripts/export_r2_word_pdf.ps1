param(
    [Parameter(Mandatory=$true)][string]$RunDirectory
)

$ErrorActionPreference = 'Stop'
$resolvedRun = (Resolve-Path -LiteralPath $RunDirectory).Path
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$expectedPrefix = Join-Path $workspace 'outputs\thesis\'
if (-not $resolvedRun.StartsWith($expectedPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Run directory must be under ignored outputs/thesis: $resolvedRun"
}

$before = @(Get-CimInstance Win32_Process -Filter "Name = 'WINWORD.EXE'" | Select-Object -ExpandProperty ProcessId)
$word = $null
$document = $null
$owned = @()
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    Start-Sleep -Milliseconds 600
    $owned = @(Get-CimInstance Win32_Process -Filter "Name = 'WINWORD.EXE'" |
        Where-Object { ($before -notcontains $_.ProcessId) -and ($_.CommandLine -match '/Automation\s+-Embedding') } |
        Select-Object -ExpandProperty ProcessId)
    if ($owned.Count -ne 1) {
        throw "Cannot uniquely identify this task's Word automation process; found $($owned.Count)"
    }
    $inputs = @(Get-ChildItem -LiteralPath $resolvedRun -Filter '*.docx' -File | Sort-Object Name)
    if ($inputs.Count -ne 2) { throw "Expected exactly two R2 DOCX files" }
    foreach ($inputDoc in $inputs) {
        $docx = $inputDoc.FullName
        $pdf = [System.IO.Path]::ChangeExtension($docx, '.pdf')
        if (-not (Test-Path -LiteralPath $docx)) { throw "Missing DOCX: $docx" }
        if (Test-Path -LiteralPath $pdf) { throw "Refusing to overwrite PDF: $pdf" }
        $document = $word.Documents.Open($docx, $false, $false)
        foreach ($toc in @($document.TablesOfContents)) { $toc.Update() }
        $document.Save()
        $document.ExportAsFixedFormat($pdf, 17)
        $document.Close($false)
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($document)
        $document = $null
    }
    $word.NormalTemplate.Saved = $true
}
finally {
    if ($null -ne $document) {
        try { $document.Save(); $document.Close($false) } catch { Write-Warning $_ }
        try { [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($document) } catch { Write-Warning $_ }
        $document = $null
    }
    if ($null -ne $word) {
        try { $word.NormalTemplate.Saved = $true; $word.Quit() } catch { Write-Warning $_ }
        try { [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) } catch { Write-Warning $_ }
        $word = $null
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
    [GC]::Collect()
    Start-Sleep -Seconds 2
    foreach ($pidToCheck in $owned) {
        $entry = Get-CimInstance Win32_Process -Filter "ProcessId = $pidToCheck" -ErrorAction SilentlyContinue
        if ($null -ne $entry -and $entry.CommandLine -match '/Automation\s+-Embedding') {
            $process = Get-Process -Id $pidToCheck -ErrorAction SilentlyContinue
            if ($null -ne $process) {
                [void]$process.CloseMainWindow()
                Start-Sleep -Seconds 2
                $entry = Get-CimInstance Win32_Process -Filter "ProcessId = $pidToCheck" -ErrorAction SilentlyContinue
                if ($null -ne $entry -and $entry.CommandLine -match '/Automation\s+-Embedding') {
                    Stop-Process -Id $pidToCheck -Force
                }
            }
        }
    }
    $residual = @(Get-CimInstance Win32_Process -Filter "Name = 'WINWORD.EXE'" |
        Where-Object { ($owned -contains $_.ProcessId) -and ($_.CommandLine -match '/Automation\s+-Embedding') })
    if ($residual.Count -ne 0) { throw "Task-owned Word automation process did not exit" }
}

Get-ChildItem -LiteralPath $resolvedRun -Filter '*.pdf' -File |
    Select-Object Name, Length, FullName
