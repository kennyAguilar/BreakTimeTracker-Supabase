@echo off
echo === INICIANDO APLICACION FLASK ===
echo.
echo Para probar el cierre de descansos:
echo 1. Una vez que Flask inicie, ve a:
echo    http://localhost:5000/status
echo.
echo 2. Para probar flujo completo con un codigo de usuario:
echo    http://localhost:5000/test_flujo_completo/001
echo.
echo 3. Para probar solo cerrar descanso:
echo    http://localhost:5000/test_close_by_code/001
echo.
echo 4. Para usar la aplicacion normal:
echo    http://localhost:5000
echo.
echo === INICIANDO SERVIDOR ===
python app.py
pause
