@echo off
chcp 65001 >nul
:: 매일 실행: 뉴스 수집 -> news_data.json -> site\index.html 재생성
:: Notion에도 저장하려면 아래 collect_news.py 줄 끝에 --notion 을 붙이세요.

cd /d "%~dp0"
set PY="C:\Users\hb038\AppData\Local\Programs\Python\Python312\python.exe"
set PYTHONIOENCODING=utf-8

echo [%date% %time%] 수집 시작
%PY% collect_news.py --top 6
if errorlevel 1 (
    echo 수집 실패 - 사이트를 갱신하지 않습니다.
    exit /b 1
)

%PY% build_site.py
echo [%date% %time%] 완료 - site\index.html
