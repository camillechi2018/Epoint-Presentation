param([ValidateSet('inspect','smoke','render')][string]$Mode='inspect',[string]$Report,[string]$OwnerFile,[string]$InputPath,[string]$RenderDirectory,[string]$SeedPresentation)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'office_guard.ps1')
$session=$null;$deck=$null
try {
 $identity=Get-EpointPowerPoint
 if($Mode -eq 'inspect'){$identity | ConvertTo-Json | Set-Content -LiteralPath $Report -Encoding UTF8; exit 0}
 $session=Start-EpointPowerPoint $OwnerFile
 $app=$session.app
 if($Mode -eq 'smoke'){
  $InputPath=Join-Path (Split-Path $Report -Parent) 'smoke.pptx'
  $RenderDirectory=Join-Path (Split-Path $Report -Parent) 'smoke-render'
  $deck=Open-EpointEmptyPresentation $app $SeedPresentation
  $slide=$deck.Slides.Add(1,12)
  $slide.Shapes.AddTextbox(1,20,20,300,80).TextFrame.TextRange.Text='Epoint Office smoke test'
  $deck.SaveAs($InputPath,24);$deck.Close();$deck=$null
 }
 New-Item -ItemType Directory -Path $RenderDirectory -Force | Out-Null
 $deck=$app.Presentations.Open([IO.Path]::GetFullPath($InputPath),-1,0,0)
 $count=$deck.Slides.Count
 foreach($slide in $deck.Slides){$slide.Export((Join-Path $RenderDirectory ('P{0:D3}.png' -f $slide.SlideIndex)),'PNG',1280,720)}
 @{status='passed';application='Microsoft PowerPoint';version=$app.Version;slide_count=$count;opened=$true;output_sha256=(Get-FileHash -LiteralPath $InputPath -Algorithm SHA256).Hash.ToLower();validation=$Mode} | ConvertTo-Json | Set-Content -LiteralPath $Report -Encoding UTF8
} catch {
 @{status='failed';error_code=($_.Exception.Message.Split(':')[0]);detail=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath $Report -Encoding UTF8
 exit 2
} finally {if($deck){$deck.Close()};Stop-EpointPowerPoint $session}
