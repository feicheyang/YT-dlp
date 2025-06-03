@echo off
chcp 936 > nul
title 打包 YTB下载器


::REM 清理之前的打包缓存
rmdir /s /q build
rmdir /s /q dist
del /f /q YTB视频下载器.spec

::REM 打包命令
Pyinstaller ^
--onefile ^
--noconsole ^
--icon=icons\文2.ico ^
--add-data "icons\文1.png;icons" ^
--add-data "icons\文2.png;icons" ^
--add-data "icons\文2.ico;icons" ^
--add-data "icons\下载2.png;icons" ^
--add-data "icons\搜索1.png;icons" ^
--hidden-import=psutil ^
--name="YTB视频下载器" ^
"YTB 3.0.py"  
::你的文件名字


echo.
echo 打包完成！生成文件在 dist\ 路径
pause