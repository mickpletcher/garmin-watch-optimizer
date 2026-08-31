[CmdletBinding()]
param(
    [switch]$UpdateAssessment
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$authorityPath = Join-Path $repoRoot ".docs-authority.json"
$assessmentPath = Join-Path $repoRoot "ASSESSMENT.md"

if (-not (Test-Path -LiteralPath $authorityPath -PathType Leaf)) {
    throw "Missing .docs-authority.json"
}

$config = Get-Content -LiteralPath $authorityPath -Raw | ConvertFrom-Json
$duplicates = @(
    $config.authorities |
        Group-Object -Property responsibility |
        Where-Object Count -gt 1
)

$rows = @(
    foreach ($authority in $config.authorities) {
        $resolvedPath = Join-Path $repoRoot $authority.path
        [pscustomobject]@{
            Responsibility = [string]$authority.responsibility
            Authority = [string]$authority.path
            Present = Test-Path -LiteralPath $resolvedPath
        }
    }
)

$tableLines = @(
    "| Responsibility | Authority | Present |"
    "| --- | --- | --- |"
    foreach ($row in $rows) {
        $present = if ($row.Present) { "Yes" } else { "No" }
        "| $($row.Responsibility) | ``$($row.Authority)`` | $present |"
    }
)
$table = $tableLines -join "`n"

if ($UpdateAssessment) {
    if (-not (Test-Path -LiteralPath $assessmentPath -PathType Leaf)) {
        throw "Missing ASSESSMENT.md"
    }
    $assessment = Get-Content -LiteralPath $assessmentPath -Raw
    $pattern = "(?s)<!-- docs-check:start -->.*?<!-- docs-check:end -->"
    if ($assessment -notmatch $pattern) {
        throw "ASSESSMENT.md is missing docs-check markers"
    }
    $replacement = "<!-- docs-check:start -->`n$table`n<!-- docs-check:end -->"
    $updated = [regex]::Replace($assessment, $pattern, $replacement)
    [System.IO.File]::WriteAllText(
        $assessmentPath,
        $updated,
        [System.Text.UTF8Encoding]::new($false)
    )
}

$table

$missing = @($rows | Where-Object Present -eq $false)
if ($duplicates.Count -gt 0) {
    Write-Error "Duplicate authority responsibilities: $($duplicates.Name -join ', ')"
}
if ($missing.Count -gt 0) {
    Write-Error "Missing authorities: $($missing.Authority -join ', ')"
}
