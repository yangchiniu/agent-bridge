@echo off
REM watcher-loop.bat — Auto-restart bridge on exit
REM Place this in the same directory as your bridge.yaml
:loop
echo [%date% %time%] Starting hermes-bridge...
python -m hermes_bridge -c bridge.yaml run
echo [%date% %time%] Bridge exited (code %ERRORLEVEL%), restarting in 5s...
timeout /t 5 /nobreak >nul
goto loop
