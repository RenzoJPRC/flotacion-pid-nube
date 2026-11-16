@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (set "PYTHON=python") else (set "PYTHON=py -3")
if not exist ".venv\Scripts\python.exe" (
    %PYTHON% -m venv .venv
    if errorlevel 1 goto error
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error
echo Abra http://127.0.0.1:5000 en su navegador.
".venv\Scripts\python.exe" app.py
goto end
:error
echo No se pudo iniciar. Instale Python 3.11 o posterior y revise su conexion.
:end
pause
