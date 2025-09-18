# PowerShell script to set up Google OAuth credentials
# Run this after getting your credentials from Google Cloud Console

Write-Host "Enter your Google OAuth credentials:" -ForegroundColor Green

$clientId = Read-Host "Enter Google Client ID"
$clientSecret = Read-Host "Enter Google Client Secret" -AsSecureString
$secretPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($clientSecret))

# Update .env file
$envPath = ".\.env"
$content = Get-Content $envPath

$content = $content -replace 'GOOGLE_CLIENT_ID=.*', "GOOGLE_CLIENT_ID=$clientId"
$content = $content -replace 'GOOGLE_CLIENT_SECRET=.*', "GOOGLE_CLIENT_SECRET=$secretPlain"

Set-Content -Path $envPath -Value $content

Write-Host "Credentials updated successfully!" -ForegroundColor Green
Write-Host "Restart the Django server to apply changes." -ForegroundColor Yellow