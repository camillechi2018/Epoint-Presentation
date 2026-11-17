# Shared by supervised Office workers. Never kill or quit an existing user process.
function Get-EpointPowerPoint {
 $key='Registry::HKEY_CLASSES_ROOT\PowerPoint.Application\CLSID'
 if(-not (Test-Path $key)){throw 'OFFICE_BACKEND_UNAVAILABLE'}
 $clsid=(Get-Item $key).GetValue('')
 $serverKey="Registry::HKEY_CLASSES_ROOT\CLSID\$clsid\LocalServer32"
 if(-not (Test-Path $serverKey)){throw 'OFFICE_BACKEND_UNAVAILABLE'}
 $server=[Environment]::ExpandEnvironmentVariables((Get-Item $serverKey).GetValue(''))
 if($server -notmatch '^\s*"?(.+?\.exe)"?(?:\s|$)'){throw 'OFFICE_BACKEND_UNVERIFIED'}
 $exe=$Matches[1]
 if(-not (Test-Path -LiteralPath $exe)){throw 'OFFICE_BACKEND_UNAVAILABLE'}
 $file=Get-Item -LiteralPath $exe
 if($file.Name -ine 'POWERPNT.EXE' -or $file.VersionInfo.CompanyName -notmatch '^Microsoft' -or $file.VersionInfo.ProductName -notmatch 'Microsoft'){
  throw 'OFFICE_BACKEND_UNSUPPORTED: PowerPoint registration is not Microsoft PowerPoint'
 }
 return @{status='detected';backend='windows_powerpoint_com';executable=$file.FullName;version=$file.VersionInfo.FileVersion;error_code=$null}
}
function Start-EpointPowerPoint([string]$OwnerFile){
 $identity=Get-EpointPowerPoint
 $before=@(Get-Process POWERPNT -ErrorAction SilentlyContinue | ForEach-Object {$_.Id})
 $app=New-Object -ComObject PowerPoint.Application
 # PowerPoint versions do not consistently expose Application.HWND.
 # Use the reported application path and a unique newly-created process instead.
 $actualPath=Join-Path $app.Path 'POWERPNT.EXE'
 $newProcesses=@(Get-Process POWERPNT -ErrorAction SilentlyContinue | Where-Object {$before -notcontains $_.Id -and $_.Path -ieq $actualPath})
 $owned=$before.Count -eq 0 -and $newProcesses.Count -eq 1
 $process=if($owned){$newProcesses[0]}else{$null}
 if($owned -and $OwnerFile){
  @{pid=$process.Id;started=$process.StartTime.ToUniversalTime().Ticks.ToString();path=$process.Path;owned=$true} | ConvertTo-Json | Set-Content -LiteralPath $OwnerFile -Encoding UTF8
 }
 if($actualPath -ine $identity.executable -or $app.Name -ne 'Microsoft PowerPoint'){
  if($owned){$app.Quit()}; throw 'OFFICE_BACKEND_IDENTITY_MISMATCH'
 }
 $security=$app.AutomationSecurity;$alerts=$app.DisplayAlerts
 $app.AutomationSecurity=3
 $app.DisplayAlerts=1
 return @{app=$app;owned=$owned;identity=$identity;security=$security;alerts=$alerts}
}
function Stop-EpointPowerPoint($session){
 if($session -and $session.owned){$session.app.Quit()}
 elseif($session){$session.app.AutomationSecurity=$session.security;$session.app.DisplayAlerts=$session.alerts}
}
