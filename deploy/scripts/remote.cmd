@echo off
REM =============================================================
REM remote.cmd — Windows → Linux 서버 모니터링·제어 (cmd.exe 래퍼)
REM
REM   PowerShell 실행정책(ExecutionPolicy)을 바꾸지 않고 cmd.exe 에서
REM   바로 쓰기 위한 얇은 래퍼. 실제 로직은 remote.ps1 에 있다.
REM
REM 사용:
REM   remote.cmd status
REM   remote.cmd status -Watch
REM   remote.cmd ps
REM   remote.cmd logs gateway
REM   remote.cmd up prod
REM   remote.cmd deploy gateway ghcr.io/me/sl_gateway:abc123 -Env prod -Pull
REM   remote.cmd tunnel 8080
REM
REM 접속 대상은 deploy\env\remote.env (RemoteTarget=...) 또는
REM 환경변수 SL_REMOTE_TARGET, 또는 인자 -Target user@host 로 지정.
REM =============================================================
setlocal
set "HERE=%~dp0"

REM PowerShell 을 찾는다 (pwsh 우선, 없으면 Windows PowerShell).
where pwsh >nul 2>nul
if %ERRORLEVEL%==0 (
  set "PS=pwsh"
) else (
  set "PS=powershell"
)

REM 실행정책 우회(-ExecutionPolicy Bypass) + 프로필 로드 생략(-NoProfile)으로
REM 어떤 세션에서도 동일하게 동작하도록 한다.
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%HERE%remote.ps1" %*
exit /b %ERRORLEVEL%
