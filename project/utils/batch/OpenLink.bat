@echo off
setlocal

:: Cambia la URL aquí
set URL=https://www.google.com

:: Abre la URL en Chrome del dispositivo conectado
adb shell am start -a android.intent.action.VIEW -d "%URL%" com.android.chrome

endlocal
pause

