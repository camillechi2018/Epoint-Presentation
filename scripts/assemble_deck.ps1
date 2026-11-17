param(
 [Parameter(Mandatory=$true)][string]$Manifest,
 [Parameter(Mandatory=$true)][string]$OutputPath,
 [string]$RenderDirectory='', [string]$PythonExe='python',
 [string]$FontProfile='windows', [ValidateRange(1,3600)][int]$TimeoutSeconds=300
)
$ErrorActionPreference='Stop'
$arguments=@((Join-Path $PSScriptRoot 'office_runtime.py'),'--manifest',$Manifest,'--output',$OutputPath,'--python-exe',$PythonExe,'--font-profile',$FontProfile,'--timeout',"$TimeoutSeconds")
if($RenderDirectory){$arguments+=@('--render-directory',$RenderDirectory)}
& $PythonExe @arguments
if($LASTEXITCODE -eq 3){exit 3}
if($LASTEXITCODE -ne 0){throw 'OFFICE_ASSEMBLY_FAILED: see Office worker report'}
