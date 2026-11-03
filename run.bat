@echo off
cd /d "%~dp0"
echo Starter Netto AI Madplanlægger...
call venv\Scripts\activate.bat
streamlit run app.py
pause
