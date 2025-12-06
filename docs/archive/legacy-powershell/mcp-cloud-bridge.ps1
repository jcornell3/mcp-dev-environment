[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$Url,

    [Parameter(Mandatory=$true)]
    [string]$AuthToken,

    [Parameter(Mandatory=$false)]
    [string]$LogDir = $null
)

# Determine log file location
# Priority: 1) Explicit LogDir parameter, 2) Script directory, 3) User's home directory
if ([string]::IsNullOrWhiteSpace($LogDir)) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    if ([string]::IsNullOrWhiteSpace($scriptDir)) {
        $LogDir = $HOME
    } else {
        $LogDir = $scriptDir
    }
}

# Create unique log file based on URL (extract domain name)
$urlHost = ([System.Uri]$Url).Host.Split('.')[0]
$logFile = Join-Path $LogDir "mcp-cloud-bridge-$urlHost.log"

try {
    "=== Bridge started: $Url at $(Get-Date) ===" | Out-File $logFile -Force
} catch {}

# UTF-8 without BOM
$utf8NoBom = New-Object System.Text.UTF8Encoding $false

while ($null -ne ($line = [Console]::In.ReadLine())) {
    $line = $line.Trim()
    if ([string]::IsNullOrWhiteSpace($line)) { 
        continue
    }
    
    # Logging disabled for production - uncomment for debugging
    # try { "Received: $line" | Out-File $logFile -Append } catch {}
    
    try {
        $headers = @{
            'Content-Type' = 'application/json'
            'Authorization' = "Bearer $AuthToken"
        }

        $bodyBytes = $utf8NoBom.GetBytes($line)

        $response = Invoke-WebRequest -Uri $Url -Method Post -Headers $headers -Body $bodyBytes -UseBasicParsing -ErrorAction Stop

        # Convert response to string to avoid byte array output
        $responseText = if ($response.Content -is [byte[]]) {
            $utf8NoBom.GetString($response.Content)
        } else {
            $response.Content.ToString()
        }

        # Logging disabled for production - uncomment for debugging
        # try { "Response: $responseText" | Out-File $logFile -Append } catch {}

        # Only output non-empty responses (skip 204 No Content notifications)
        if ($responseText.Trim()) {
            [Console]::Out.WriteLine($responseText)
            [Console]::Out.Flush()
        }
    }
    catch {
        try { "Error: $($_.Exception.Message)" | Out-File $logFile -Append } catch {}
        
        $errorMsg = $_.Exception.Message.Replace('"', '\"').Replace("`r", '').Replace("`n", ' ')
        $errorResponse = "{`"jsonrpc`":`"2.0`",`"id`":null,`"error`":{`"code`":-32603,`"message`":`"$errorMsg`"}}"
        
        [Console]::Out.WriteLine($errorResponse)
        [Console]::Out.Flush()
    }
}

# Closing log - kept for production monitoring
try { "=== Bridge ended at $(Get-Date) ===" | Out-File $logFile -Append } catch {}