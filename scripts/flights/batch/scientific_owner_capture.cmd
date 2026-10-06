@echo off
setlocal
rem Preserve an independent native exit receipt even if the inner owner terminates.
if exist "%~6\owner-process-exit.json" exit /b 91
if exist "%~6\owner.stdout.log" exit /b 91
if exist "%~6\owner.stderr.log" exit /b 91
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~1" -RegistrationPath "%~2" -RegistrationSHA "%~3" -PlanPath "%~4" -PlanSHA "%~5" 1>"%~6\owner.stdout.log" 2>"%~6\owner.stderr.log"
set "SAEA_CAPTURE_EXIT=%errorlevel%"
>"%~6\owner-process-exit.json" echo {"schema":"saea-owner-native-process-exit-v1","exit_code":%SAEA_CAPTURE_EXIT%,"plan_sha256":"%~5"}
exit /b %SAEA_CAPTURE_EXIT%
