@echo off
echo =============================================
echo Verificando y configurando permisos de instalacion APK...
echo =============================================

:: Comprobar/verifier_verify_adb_installs
for /f "tokens=*" %%i in ('adb shell settings get global verifier_verify_adb_installs') do set adb_verifier=%%i
echo Verifier ADB Install: %adb_verifier%
if "%adb_verifier%"=="0" (
    echo Ya desactivado.
) else (
    echo Desactivando verifier_verify_adb_installs...
    adb shell settings put global verifier_verify_adb_installs 0
)

:: Comprobar/package_verifier_enable (Play Protect)
for /f "tokens=*" %%i in ('adb shell settings get global package_verifier_enable') do set package_verifier=%%i
echo Package verifier (Play Protect): %package_verifier%
if "%package_verifier%"=="0" (
    echo Ya desactivado.
) else (
    echo Desactivando package_verifier_enable...
    adb shell settings put global package_verifier_enable 0
)

:: Comprobar/install_non_market_apps
for /f "tokens=*" %%i in ('adb shell settings get global install_non_market_apps') do set non_market_apps=%%i
echo Install non-market apps: %non_market_apps%
if "%non_market_apps%"=="1" (
    echo Ya permitido.
) else (
    echo Permitindo install_non_market_apps...
    adb shell settings put global install_non_market_apps 1
)

:: Comprobar/depuracion USB
for /f "tokens=*" %%i in ('adb shell settings get global adb_enabled') do set adb_enabled=%%i
echo Depuracion USB (adb_enabled): %adb_enabled%
if "%adb_enabled%"=="1" (
    echo Depuracion USB activada.
) else (
    echo Activando depuracion USB...
    adb shell settings put global adb_enabled 1
)

echo =============================================
echo Configuracion completada.
echo Ahora el dispositivo deberia permitir instalar APKs desde ADB y orígenes desconocidos.
pause

