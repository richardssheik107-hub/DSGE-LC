param([Parameter(Mandatory=$true)][string]$Docx)
$ErrorActionPreference = 'Stop'
$inputPath = (Resolve-Path -LiteralPath $Docx).Path
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$expectedPrefix = Join-Path $workspace 'outputs\thesis\'
if (-not $inputPath.StartsWith($expectedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "DOCX must be under ignored outputs/thesis: $inputPath"
}
$pdfPath = [IO.Path]::ChangeExtension($inputPath, '.pdf')
if (Test-Path -LiteralPath $pdfPath) { throw "Refusing to overwrite: $pdfPath" }
$before = @(Get-CimInstance Win32_Process -Filter "Name = 'WINWORD.EXE'" | Select-Object -ExpandProperty ProcessId)
$word = $null; $doc = $null; $owned = @()
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    Start-Sleep -Milliseconds 600
    $owned = @(Get-CimInstance Win32_Process -Filter "Name = 'WINWORD.EXE'" |
        Where-Object { ($before -notcontains $_.ProcessId) -and ($_.CommandLine -match '/Automation\s+-Embedding') } |
        Select-Object -ExpandProperty ProcessId)
    if ($owned.Count -ne 1) { throw "Cannot uniquely identify this task's Word automation process; found $($owned.Count)" }
    $doc = $word.Documents.Open($inputPath, $false, $false)
    $doc.Save()
    $doc.ExportAsFixedFormat($pdfPath, 17)
    $doc.Close($false)
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($doc)
    $doc = $null
    $word.NormalTemplate.Saved = $true
} finally {
    if ($null -ne $doc) {
        try { $doc.Save(); $doc.Close($false) } catch { Write-Warning $_ }
        try { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($doc) } catch { Write-Warning $_ }
        $doc = $null
    }
    if ($null -ne $word) {
        try { $word.NormalTemplate.Saved = $true; $word.Quit() } catch { Write-Warning $_ }
        try { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) } catch { Write-Warning $_ }
        $word = $null
    }
    [GC]::Collect(); [GC]::WaitForPendingFinalizers(); [GC]::Collect()
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
if (!(Test-Path -LiteralPath $pdfPath)) { throw 'Word did not create PDF' }
Write-Output $pdfPath
