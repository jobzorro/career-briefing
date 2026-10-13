@echo off
chcp 65001 >nul
:: 매일 오전 8시에 run_daily.bat 자동 실행 등록
:: (수집 -> news_data.json -> site\index.html 재생성)

schtasks /create /tn "CareerNewsCollector" /tr "'%~dp0run_daily.bat'" /sc daily /st 08:00 /f

echo.
echo 작업 스케줄러 등록 완료!
echo 매일 오전 8시에 뉴스 수집 + 사이트 재생성이 실행됩니다.
echo.
echo   해제: schtasks /delete /tn "CareerNewsCollector" /f
echo   즉시 실행 테스트: schtasks /run /tn "CareerNewsCollector"
pause
