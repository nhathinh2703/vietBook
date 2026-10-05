@echo off
chcp 65001 >nul
title vietBook - Kho Sach Dien Tu
echo ===================================================
echo    vietBook - KHO SACH & TRA CUU SACH DIEN TU
echo ===================================================
echo Dang khoi dong ung dung web...
echo.
python -m streamlit run app.py
pause
