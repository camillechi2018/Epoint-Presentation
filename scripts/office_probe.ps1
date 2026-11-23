param([ValidateSet('inspect','smoke','render')][string]$Mode='inspect',[string]$Report,[string]$OwnerFile,[string]$InputPath,[string]$RenderDirectory,[string]$SeedPresentation)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'office_guard.ps1')
$session=$null
try {
 $identity=Get-EpointPowerPoint
 if($Mode -eq 'inspect'){$identity | ConvertTo-Json | Set-Content -LiteralPath $Report -Encoding UTF8; exit 0}
 $session=Start-EpointPowerPoint $OwnerFile
 $app=$session.app
 if($Mode -eq 'smoke'){
  $evidence=Test-EpointPowerPointSession $app $SeedPresentation (Split-Path $Report -Parent)
 }else{
  $evidence=Export-EpointPresentation $app $InputPath $RenderDirectory 'render'
 }
 $evidence | ConvertTo-Json | Set-Content -LiteralPath $Report -Encoding UTF8
} catch {
 @{status='failed';error_code=($_.Exception.Message.Split(':')[0]);detail=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath $Report -Encoding UTF8
 exit 2
} finally {Stop-EpointPowerPoint $session}
