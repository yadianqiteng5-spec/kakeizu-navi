import os, subprocess
BASE = os.path.dirname(os.path.abspath(__file__))
ps1 = os.path.join(BASE, "auto_run.ps1")
tr = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%s"' % ps1
r = subprocess.run(["schtasks","/Create","/TN","KakeizuNavi-AutoPost","/TR",tr,
                    "/SC","HOURLY","/MO","8","/F","/RL","LIMITED"],
                   capture_output=True, text=True)
print("rc:", r.returncode)
print("stdout:", r.stdout.strip())
print("stderr:", r.stderr.strip())
# 確認
q = subprocess.run(["schtasks","/Query","/TN","KakeizuNavi-AutoPost","/FO","LIST"],
                   capture_output=True, text=True)
print("--- query ---")
print(q.stdout.strip()[:400])
