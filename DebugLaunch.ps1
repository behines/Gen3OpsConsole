if (-not $env:GEN3_SITE) {
  Add-Type -AssemblyName PresentationFramework
  [System.Windows.MessageBox]::Show(
    "GEN3_SITE is not set. Set it to 'sandia' or 'windsor' before launching.",
    "Gen3 Ops Console Startup Error",
    "OK",
    "Error"
  )
  exit 1
}

Start-Process `
  -FilePath "C:\Program Files\Microsoft VS Code\Code.exe" `
  -ArgumentList @(
    "C:\Users\PlanetA\Documents\GitHub\Gen3OpsConsole\Gen3OpsConsole.code-workspace",
    "--new-window",
    "--profile",
    "AutoDebug"
  )