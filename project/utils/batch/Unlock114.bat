@echo off
REM Conectar el dispositivo
adb start-server
adb devices

REM Encender pantalla si está apagada
adb shell input keyevent 26
timeout /t 1

REM Deslizar para desbloquear (de abajo hacia arriba, columna derecha)
adb shell input swipe 2300 1800 2300 200 2000
timeout /t 1

REM Coordenadas fijas del teclado en la derecha (ajusta si no coincide)
REM Layout:
REM 1 2 3
REM 4 5 6
REM 7 8 9
REM   0
set COL1=2100
set COL2=2300
set COL3=2500
set ROW1=800
set ROW2=900
set ROW3=1000
set ROW4=1100

REM Teclear PIN 521121
adb shell input tap %COL2% %ROW2%  REM 5
adb shell input tap %COL1% %ROW2%  REM 2
adb shell input tap %COL3% %ROW1%  REM 1
adb shell input tap %COL3% %ROW1%  REM 1
adb shell input tap %COL1% %ROW2%  REM 2
adb shell input tap %COL3% %ROW1%  REM 1

echo Hecho.
pause
