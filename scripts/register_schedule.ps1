# Windows 작업 스케줄러에 정기 작업 등록
#   - 매일 07:00  : 필수 추적 요소 수집 (LLM 미사용, 비용 없음)
#   - 매주 월 07:30: 수집 + 주간 동향 리포트 생성 (reports/ 에 저장)
# 사용법: powershell -ExecutionPolicy Bypass -File scripts\register_schedule.ps1
# 해제:   Unregister-ScheduledTask -TaskName "CIS-Intel-*" -Confirm:$false

$root = Split-Path -Parent $PSScriptRoot
$python = (Get-Command python).Source

$daily = New-ScheduledTaskAction -Execute $python -Argument "app.py collect --days 3" -WorkingDirectory $root
Register-ScheduledTask -TaskName "CIS-Intel-DailyCollect" -Action $daily `
    -Trigger (New-ScheduledTaskTrigger -Daily -At 7:00am) -Force | Out-Null

$weekly = New-ScheduledTaskAction -Execute "cmd.exe" `
    -Argument "/c `"$python`" app.py weekly >> logs\weekly.log 2>&1" -WorkingDirectory $root
Register-ScheduledTask -TaskName "CIS-Intel-WeeklyReport" -Action $weekly `
    -Trigger (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 7:30am) -Force | Out-Null

New-Item -ItemType Directory -Force (Join-Path $root "logs") | Out-Null
Get-ScheduledTask -TaskName "CIS-Intel-*" | Select-Object TaskName, State
