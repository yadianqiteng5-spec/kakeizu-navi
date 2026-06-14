# 無人自動実行（タスクスケジューラから呼ばれる）。中身は auto_pipeline.py が全部やる。
$dir = $PSScriptRoot
Set-Location $dir
$py = 'C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }
& $py auto_pipeline.py
