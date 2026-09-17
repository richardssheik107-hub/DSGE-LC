param([Parameter(Mandatory=$true)][string]$Docx)
$ErrorActionPreference = 'Stop'
$inputPath = (Resolve-Path -LiteralPath $Docx).Path
$pdfPath = [IO.Path]::ChangeExtension($inputPath, '.pdf')
if (Test-Path -LiteralPath $pdfPath) { throw "Refusing to overwrite: $pdfPath" }
$word = $null; $doc = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($inputPath, $false, $true)
    $doc.ExportAsFixedFormat($pdfPath, 17)
} finally {
    if ($doc) { $doc.Close(0); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($doc) }
    if ($word) { $word.Quit(); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) }
}
if (!(Test-Path -LiteralPath $pdfPath)) { throw 'Word did not create PDF' }
Write-Output $pdfPath
