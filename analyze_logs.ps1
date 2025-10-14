# AWS MCP Server - Log Analysis Script
# PowerShell script for analyzing requests.log

param(
    [string]$LogFile = "requests.log",
    [string]$Action = "analyze",
    [int]$Lines = 10,
    [string]$SearchTerm = ""
)

function Test-LogFile {
    param([string]$Path)
    
    if (-not (Test-Path $Path)) {
        Write-Host "Error: Log file not found: $Path" -ForegroundColor Red
        Write-Host "Run the MCP server and execute some commands to generate logs." -ForegroundColor Yellow
        return $false
    }
    return $true
}

function Get-LogStatistics {
    param([string]$LogPath)
    
    if (-not (Test-LogFile $LogPath)) { return }
    
    Write-Host "`nAnalyzing log file: $LogPath`n" -ForegroundColor Cyan
    
    $entries = Get-Content $LogPath | ForEach-Object {
        try {
            $_ | ConvertFrom-Json
        } catch {
            Write-Warning "Invalid JSON on line: $_"
        }
    }
    
    if ($entries.Count -eq 0) {
        Write-Host "No valid log entries found." -ForegroundColor Yellow
        return
    }
    
    $totalRequests = $entries.Count
    $successful = ($entries | Where-Object { $_.status -eq "success" }).Count
    $errors = ($entries | Where-Object { $_.status -eq "error" }).Count
    
    $successRate = if ($totalRequests -gt 0) { ($successful / $totalRequests) * 100 } else { 0 }
    $errorRate = if ($totalRequests -gt 0) { ($errors / $totalRequests) * 100 } else { 0 }
    
    # Tool usage
    $toolUsage = $entries | Group-Object -Property tool_name | 
        Select-Object Name, Count | Sort-Object Count -Descending
    
    # Duration statistics
    $durations = $entries | Select-Object -ExpandProperty duration_ms
    $avgDuration = ($durations | Measure-Object -Average).Average
    $maxDuration = ($durations | Measure-Object -Maximum).Maximum
    $minDuration = ($durations | Measure-Object -Minimum).Minimum
    
    # Display statistics
    Write-Host "=" * 60 -ForegroundColor Green
    Write-Host "REQUEST LOG STATISTICS" -ForegroundColor Green
    Write-Host "=" * 60 -ForegroundColor Green
    Write-Host "`nTotal Requests: $totalRequests"
    Write-Host "Successful:     $successful ($($successRate.ToString('F1'))%)" -ForegroundColor Green
    Write-Host "Errors:         $errors ($($errorRate.ToString('F1'))%)" -ForegroundColor $(if ($errors -gt 0) { "Red" } else { "Green" })
    
    Write-Host "`n$("-" * 60)"
    Write-Host "TOOL USAGE"
    Write-Host "$("-" * 60)"
    foreach ($tool in $toolUsage) {
        $toolName = $tool.Name.PadRight(30)
        $count = $tool.Count.ToString().PadLeft(5)
        Write-Host "$toolName $count calls"
    }
    
    Write-Host "`n$("-" * 60)"
    Write-Host "DURATION STATISTICS (milliseconds)"
    Write-Host "$("-" * 60)"
    Write-Host "Average: $($avgDuration.ToString('F2').PadLeft(10)) ms"
    Write-Host "Maximum: $($maxDuration.ToString('F2').PadLeft(10)) ms"
    Write-Host "Minimum: $($minDuration.ToString('F2').PadLeft(10)) ms"
    
    # Recent requests
    Write-Host "`n$("-" * 60)"
    Write-Host "RECENT REQUESTS (last 5)"
    Write-Host "$("-" * 60)"
    $entries | Select-Object -Last 5 | ForEach-Object {
        $symbol = if ($_.status -eq "success") { "✓" } else { "✗" }
        $color = if ($_.status -eq "success") { "Green" } else { "Red" }
        
        Write-Host "$symbol [$($_.timestamp)] $($_.tool_name) - $($_.duration_ms.ToString('F2'))ms - $($_.status)" -ForegroundColor $color
        
        if ($_.input.command) {
            $cmd = $_.input.command
            if ($cmd.Length -gt 70) { $cmd = $cmd.Substring(0, 67) + "..." }
            Write-Host "  Command: $cmd" -ForegroundColor Gray
        }
        
        if ($_.error) {
            $err = $_.error
            if ($err.Length -gt 70) { $err = $err.Substring(0, 67) + "..." }
            Write-Host "  Error: $err" -ForegroundColor Red
        }
        Write-Host ""
    }
    
    Write-Host "=" * 60 -ForegroundColor Green
}

function Get-LogTail {
    param(
        [string]$LogPath,
        [int]$NumLines
    )
    
    if (-not (Test-LogFile $LogPath)) { return }
    
    Write-Host "`nLast $NumLines entries from $LogPath:`n" -ForegroundColor Cyan
    
    Get-Content $LogPath | Select-Object -Last $NumLines | ForEach-Object {
        try {
            $entry = $_ | ConvertFrom-Json
            $entry | ConvertTo-Json -Depth 10 | Write-Host
            Write-Host "$("-" * 60)" -ForegroundColor Gray
        } catch {
            Write-Warning "Invalid JSON: $_"
        }
    }
}

function Search-LogFile {
    param(
        [string]$LogPath,
        [string]$Term
    )
    
    if (-not (Test-LogFile $LogPath)) { return }
    
    if ([string]::IsNullOrWhiteSpace($Term)) {
        Write-Host "Error: Search term is required" -ForegroundColor Red
        return
    }
    
    Write-Host "`nSearching for '$Term' in $LogPath`n" -ForegroundColor Cyan
    
    $matches = @()
    $lineNum = 0
    
    Get-Content $LogPath | ForEach-Object {
        $lineNum++
        if ($_ -match $Term) {
            try {
                $entry = $_ | ConvertFrom-Json
                $matches += [PSCustomObject]@{
                    LineNumber = $lineNum
                    Entry = $entry
                }
            } catch {
                # Ignore invalid JSON
            }
        }
    }
    
    if ($matches.Count -eq 0) {
        Write-Host "No matches found." -ForegroundColor Yellow
        return
    }
    
    Write-Host "Found $($matches.Count) matches:`n" -ForegroundColor Green
    
    $matches | Select-Object -First 20 | ForEach-Object {
        Write-Host "Line $($_.LineNumber):" -ForegroundColor Cyan
        $_.Entry | ConvertTo-Json -Depth 10 | Write-Host
        Write-Host "$("-" * 60)" -ForegroundColor Gray
    }
}

function Show-Help {
    Write-Host @"

AWS MCP Server - Log Analysis Tool
===================================

Usage:
    .\analyze_logs.ps1 [-Action <action>] [-LogFile <path>] [-Lines <number>] [-SearchTerm <term>]

Actions:
    analyze     Show statistics and summary (default)
    tail        Display last N log entries
    search      Search for specific terms
    help        Show this help message

Examples:
    # Analyze the log file
    .\analyze_logs.ps1

    # Show last 20 entries
    .\analyze_logs.ps1 -Action tail -Lines 20

    # Search for errors
    .\analyze_logs.ps1 -Action search -SearchTerm "error"

    # Search for specific command
    .\analyze_logs.ps1 -Action search -SearchTerm "s3 ls"

    # Analyze specific log file
    .\analyze_logs.ps1 -LogFile "C:\logs\requests.log"

"@ -ForegroundColor Cyan
}

# Main script logic
switch ($Action.ToLower()) {
    "analyze" {
        Get-LogStatistics -LogPath $LogFile
    }
    "tail" {
        Get-LogTail -LogPath $LogFile -NumLines $Lines
    }
    "search" {
        Search-LogFile -LogPath $LogFile -Term $SearchTerm
    }
    "help" {
        Show-Help
    }
    default {
        Write-Host "Unknown action: $Action" -ForegroundColor Red
        Show-Help
    }
}
