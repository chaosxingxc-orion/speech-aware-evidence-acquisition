@echo off
setlocal
rem Capture full-cohort native termination independently of the scientific owner.
if exist "%~3\owner-process-exit.json" exit /b 91
if exist "%~3\owner.stdout.log" exit /b 91
if exist "%~3\owner.stderr.log" exit /b 91
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~1" -RegistrationSHA "%~2" 1>"%~3\owner.stdout.log" 2>"%~3\owner.stderr.log"
set "SAEA_FULL_CAPTURE_EXIT=%errorlevel%"
>"%~3\owner-process-exit.json" echo {"schema":"saea-scientific-owner-native-exit-v1","exit_code":%SAEA_FULL_CAPTURE_EXIT%,"registration_sha256":"%~2"}
exit /b %SAEA_FULL_CAPTURE_EXIT%
