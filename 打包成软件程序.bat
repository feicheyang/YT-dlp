@echo off
chcp 936 > nul
title ��� YTB������


::REM ����֮ǰ�Ĵ������
rmdir /s /q build
rmdir /s /q dist
del /f /q YTB��Ƶ������.spec

::REM �������
Pyinstaller ^
--onefile ^
--noconsole ^
--icon=icons\��2.ico ^
--add-data "icons\��1.png;icons" ^
--add-data "icons\��2.png;icons" ^
--add-data "icons\��2.ico;icons" ^
--add-data "icons\����2.png;icons" ^
--add-data "icons\����1.png;icons" ^
--hidden-import=psutil ^
--name="YTB��Ƶ������" ^
"YTB 3.0.py"  
::����ļ�����


echo.
echo �����ɣ������ļ��� dist\ ·��
pause