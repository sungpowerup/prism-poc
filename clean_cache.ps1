# PRISM Phase 5.7.2.2 - 캐시 완전 제거 스크립트
# Windows PowerShell용

Write-Host "🧹 PRISM 캐시 제거 시작..." -ForegroundColor Green
Write-Host ""

# 1. Python 프로세스 종료
Write-Host "1️⃣ Python 프로세스 종료 중..." -ForegroundColor Cyan
try {
    Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
    Stop-Process -Name "streamlit" -Force -ErrorAction SilentlyContinue
    Write-Host "   ✅ 프로세스 종료 완료" -ForegroundColor Green
} catch {
    Write-Host "   ℹ️ 실행 중인 프로세스 없음" -ForegroundColor Yellow
}

Start-Sleep -Seconds 2

# 2. __pycache__ 제거
Write-Host ""
Write-Host "2️⃣ __pycache__ 제거 중..." -ForegroundColor Cyan
$pycache = Get-ChildItem -Recurse -Include __pycache__ -Force -ErrorAction SilentlyContinue
$count = ($pycache | Measure-Object).Count

if ($count -gt 0) {
    $pycache | Remove-Item -Recurse -Force
    Write-Host "   ✅ $count 개 __pycache__ 제거 완료" -ForegroundColor Green
} else {
    Write-Host "   ℹ️ __pycache__ 없음" -ForegroundColor Yellow
}

# 3. .pyc 제거
Write-Host ""
Write-Host "3️⃣ .pyc 파일 제거 중..." -ForegroundColor Cyan
$pyc = Get-ChildItem -Recurse -Include *.pyc -Force -ErrorAction SilentlyContinue
$count = ($pyc | Measure-Object).Count

if ($count -gt 0) {
    $pyc | Remove-Item -Force
    Write-Host "   ✅ $count 개 .pyc 파일 제거 완료" -ForegroundColor Green
} else {
    Write-Host "   ℹ️ .pyc 파일 없음" -ForegroundColor Yellow
}

# 4. Streamlit 캐시 제거
Write-Host ""
Write-Host "4️⃣ Streamlit 캐시 제거 중..." -ForegroundColor Cyan
if (Test-Path ".streamlit") {
    Remove-Item -Path ".streamlit" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "   ✅ Streamlit 캐시 제거 완료" -ForegroundColor Green
} else {
    Write-Host "   ℹ️ Streamlit 캐시 없음" -ForegroundColor Yellow
}

# 5. 완료
Write-Host ""
Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║                                        ║" -ForegroundColor Magenta
Write-Host "║     ✅ 캐시 제거 완료!                 ║" -ForegroundColor Magenta
Write-Host "║                                        ║" -ForegroundColor Magenta
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""
Write-Host "📌 다음 단계:" -ForegroundColor Yellow
Write-Host "   streamlit run app.py" -ForegroundColor White
Write-Host ""
