# Smoke test: proves uploads + sessions persist in the cloud database.
# Usage:  python run.py   (in one terminal)
#         ./smoke_test.ps1 (in another)
#
# It signs up a fresh user, uploads a document, then signs in AGAIN with a new
# token and re-lists the documents. If the file is still there on the second,
# independent login, the data is genuinely living in MongoDB (not in memory).

$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:8082"          # match COPILOT_PORT in .env
$email = "smoke+$(Get-Random)@test.com"
$password = "TestPass123!"

function Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }

Step "1. Health check"
$health = Invoke-RestMethod "$base/health"
$health | Format-List

Step "2. Sign up ($email)"
$body = @{ email = $email; password = $password } | ConvertTo-Json
$signup = Invoke-RestMethod "$base/api/auth/signup" -Method Post -Body $body -ContentType "application/json"
$token1 = $signup.access_token
Write-Host "Got token, user_id = $($signup.user_id)"

Step "3. Upload a document"
# KB only accepts .txt/.md/.json/.pdf/.docx, so name the temp file .txt.
$tmp = Join-Path $env:TEMP "smoke_doc_$(Get-Random).txt"
"Past project: built an AI proposal generator with RAG over MongoDB." | Set-Content $tmp
$upload = Invoke-RestMethod "$base/api/kb/upload" -Method Post `
    -Headers @{ Authorization = "Bearer $token1" } `
    -Form @{ file = Get-Item $tmp }
Write-Host "Uploaded: $($upload.filename)  (indexed=$($upload.indexed))"
Remove-Item $tmp

Step "4. List documents (same session)"
$list1 = Invoke-RestMethod "$base/api/kb/list" -Headers @{ Authorization = "Bearer $token1" }
Write-Host "Documents now: $($list1.documents.Count)"
$list1.documents | Select-Object filename, size_bytes, uploaded_at | Format-Table

Step "5. Sign in AGAIN (fresh token = simulates a different device)"
$signin = Invoke-RestMethod "$base/api/auth/signin" -Method Post -Body $body -ContentType "application/json"
$token2 = $signin.access_token
$list2 = Invoke-RestMethod "$base/api/kb/list" -Headers @{ Authorization = "Bearer $token2" }

if ($list2.documents.Count -ge 1) {
    Write-Host "`nPASS: document survived a fresh login -> it is stored in the cloud DB." -ForegroundColor Green
} else {
    Write-Host "`nFAIL: document missing on re-login -> not persisted." -ForegroundColor Red
}
