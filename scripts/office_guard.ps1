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
 $pathMismatch=$actualPath -ine $identity.executable
 $actualApplicationName=$null
 if($pathMismatch -or ($actualApplicationName=$app.Name) -ne 'Microsoft PowerPoint'){
  if($pathMismatch){
   # The name check was skipped. Read it for diagnostics without masking the path mismatch.
   try{$actualApplicationName=$app.Name}catch{}
  }
  $detail=@{
   actual_application_name=$actualApplicationName
   actual_executable_path=$actualPath
   registered_executable_path=$identity.executable
  } | ConvertTo-Json -Compress
  if($owned){$app.Quit()}; throw "OFFICE_BACKEND_IDENTITY_MISMATCH: $detail"
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
function Open-EpointEmptyPresentation($app, [string]$SeedPresentation){
 if(-not $SeedPresentation -or -not (Test-Path -LiteralPath $SeedPresentation -PathType Leaf)){
  throw 'OFFICE_EMPTY_PRESENTATION_MISSING'
 }
 # Initialize the background document through PowerPoint's Open path.
 $deck=$app.Presentations.Open([IO.Path]::GetFullPath($SeedPresentation),0,0,0)
 if($deck.Slides.Count -ne 0){
  $deck.Close()
  throw 'OFFICE_EMPTY_PRESENTATION_HAS_SLIDES'
 }
 return $deck
}

function Export-EpointPresentation($app, [string]$InputPath, [string]$RenderDirectory, [string]$Mode){
 $path=[IO.Path]::GetFullPath($InputPath)
 $hash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower()
 New-Item -ItemType Directory -Path $RenderDirectory -Force | Out-Null
 $deck=$app.Presentations.Open($path,-1,0,0)
 try{
  $count=$deck.Slides.Count
  foreach($slide in $deck.Slides){
   $slide.Export((Join-Path $RenderDirectory ('P{0:D3}.png' -f $slide.SlideIndex)),'PNG',1280,720)
  }
  return @{status='passed';application='Microsoft PowerPoint';version=$app.Version;slide_count=$count;opened=$true;output_sha256=$hash;validation=$Mode}
 }finally{$deck.Close()}
}

function Test-EpointPowerPointSession($app, [string]$SeedPresentation, [string]$Folder){
 $path=Join-Path $Folder 'smoke.pptx'
 $deck=Open-EpointEmptyPresentation $app $SeedPresentation
 try{
  $slide=$deck.Slides.Add(1,12)
  $slide.Shapes.AddTextbox(1,20,20,300,80).TextFrame.TextRange.Text='Epoint Office smoke test'
  $deck.SaveAs($path,24)
 }finally{$deck.Close()}
 return Export-EpointPresentation $app $path (Join-Path $Folder 'smoke-render') 'smoke'
}
