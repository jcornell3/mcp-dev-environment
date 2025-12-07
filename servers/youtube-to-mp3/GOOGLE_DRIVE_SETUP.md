# Google Drive Integration Setup

This guide explains how to configure Google Drive upload functionality for the YouTube to MP3 service.

## Overview

The service supports uploading MP3 files to Google Drive after conversion. This feature is **optional** and requires Google Cloud credentials.

## Authentication Methods

Two authentication methods are supported:

1. **OAuth2 User Credentials** (Recommended for personal use)
2. **Service Account** (Recommended for automated/server deployments)

## Method 1: OAuth2 User Credentials (Personal Use)

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Note your project name

### Step 2: Enable Google Drive API

1. In Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for "Google Drive API"
3. Click **Enable**

### Step 3: Create OAuth2 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. If prompted, configure OAuth consent screen:
   - User Type: **External** (for personal use)
   - App name: `YouTube to MP3 Uploader` (or any name)
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: Add `https://www.googleapis.com/auth/drive.file`
   - **Test users**: Add your Gmail address in the **Test users** section
   - **Important**: Also add your email under the **Audience** screen
4. Application type: **Web application** (NOT Desktop app)
5. Name: `YouTube MP3 Web Client`
6. **Authorized redirect URIs**: Add `http://localhost:8080`
7. Click **Create**
8. Download the credentials JSON file
9. Save as `google-drive-credentials.json`

### Step 4: Generate User Token

Run this Python script to generate the user token:

```python
#!/usr/bin/env python3
"""
Generate Google Drive OAuth2 token - Web Application Flow
"""

from google_auth_oauthlib.flow import Flow
import json
import os

# Allow HTTP for localhost (required for local OAuth flow)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Path to your downloaded credentials
CLIENT_SECRETS_FILE = "google-drive-credentials.json"

# Must match the redirect URI configured in Google Cloud Console
REDIRECT_URI = "http://localhost:8080"

# Create flow with explicit redirect URI
flow = Flow.from_client_secrets_file(
    CLIENT_SECRETS_FILE,
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI
)

# Generate authorization URL
auth_url, state = flow.authorization_url(
    access_type='offline',
    prompt='consent'
)

print("=" * 80)
print("1. Copy this URL and paste it in your browser:\n")
print(auth_url)
print("\n" + "=" * 80)
print("\n2. After authorizing, you'll be redirected to:")
print("   http://localhost:8080/?state=...&code=...&scope=...")
print("\n3. Your browser will show 'This site can't be reached' - THAT'S NORMAL!")
print("\n4. Copy the ENTIRE URL from your browser's address bar")
print("   (starts with http://localhost:8080/?state=...)")
print("\n" + "=" * 80)

redirect_response = input("\nPaste the full redirect URL here: ").strip()

# Exchange authorization code for credentials
flow.fetch_token(authorization_response=redirect_response)
creds = flow.credentials

# Save token
token_data = {
    'token': creds.token,
    'refresh_token': creds.refresh_token,
    'token_uri': creds.token_uri,
    'client_id': creds.client_id,
    'client_secret': creds.client_secret,
    'scopes': creds.scopes
}

with open('google-drive-token.json', 'w') as f:
    json.dump(token_data, f, indent=2)

print("\n✅ SUCCESS! Token saved to google-drive-token.json")
print("Copy this file to your credentials directory")
```

Save this script as `generate_token.py` and run:

```bash
pip install google-auth-oauthlib
python generate_token.py
```

**Important Notes:**
- The browser will show "This site can't be reached" after authorization - this is normal!
- Copy the ENTIRE URL from the address bar (starts with `http://localhost:8080/?state=...`)
- The script sets `OAUTHLIB_INSECURE_TRANSPORT=1` to allow HTTP for localhost
- Make sure the redirect URI matches what you configured in Google Cloud Console

### Step 5: Configure Environment

1. **Create credentials directory:**
   ```bash
   mkdir -p ~/google-credentials
   cp google-drive-token.json ~/google-credentials/
   ```

2. **Update `.env` file:**
   ```bash
   # Google Drive Configuration
   GOOGLE_DRIVE_CREDENTIALS_PATH=/home/YOUR_USERNAME/google-credentials
   GOOGLE_DRIVE_CREDENTIALS_JSON=/app/credentials/google-drive-token.json
   ```

   Replace `YOUR_USERNAME` with your actual username.

3. **Copy docker-compose template:**
   ```bash
   cp docker-compose.yml.local docker-compose.yml
   ```

4. **Restart service:**
   ```bash
   export MCP_API_KEY=5b919081bcca34a32d8ac272e6691521cabbf71b1baace759cc6c710a3003c74
   docker compose down
   docker compose build youtube-to-mp3
   docker compose up -d youtube-to-mp3
   ```

5. **Verify configuration:**
   ```bash
   curl -s http://127.0.0.1:3004/health | grep google_drive
   ```

   Expected output:
   ```json
   "google_drive_configured": true
   ```

## Method 2: Service Account (Automated/Server Use)

### Step 1: Create Service Account

1. In Google Cloud Console, go to **IAM & Admin** > **Service Accounts**
2. Click **Create Service Account**
3. Name: `youtube-mp3-uploader`
4. Description: `Service account for YouTube to MP3 Google Drive uploads`
5. Click **Create and Continue**
6. Skip role assignment (optional)
7. Click **Done**

### Step 2: Generate Service Account Key

1. Click on the created service account
2. Go to **Keys** tab
3. Click **Add Key** > **Create new key**
4. Key type: **JSON**
5. Click **Create**
6. Save the downloaded JSON file as `google-service-account.json`

### Step 3: Share Google Drive Folder

**Important:** Service accounts don't have their own Google Drive. You must share a folder with the service account.

1. Create a folder in your Google Drive (e.g., "YouTube MP3s")
2. Right-click folder > **Share**
3. Add the service account email (found in the JSON file under `client_email`)
   - Example: `youtube-mp3-uploader@project-id.iam.gserviceaccount.com`
4. Grant **Editor** permission
5. Click **Share**

### Step 4: Configure Environment

1. **Create credentials directory:**
   ```bash
   mkdir -p ~/google-credentials
   cp google-service-account.json ~/google-credentials/
   ```

2. **Update `.env` file:**
   ```bash
   # Google Drive Configuration
   GOOGLE_DRIVE_CREDENTIALS_PATH=/home/YOUR_USERNAME/google-credentials
   GOOGLE_SERVICE_ACCOUNT_JSON=/app/credentials/google-service-account.json
   ```

3. **Restart service:**
   ```bash
   export MCP_API_KEY=5b919081bcca34a32d8ac272e6691521cabbf71b1baace759cc6c710a3003c74
   docker compose down
   docker compose build youtube-to-mp3
   docker compose up -d youtube-to-mp3
   ```

## Usage

### Basic Upload (Default Folder)

```
Convert https://www.youtube.com/watch?v=dQw4w9WgXcQ to MP3 in my Google Drive
```

Claude will call:
```json
{
  "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "upload_to_drive": true
}
```

**Note:** Files are uploaded to the standardized folder **"MCP-YouTube-to-MP3"** by default. This folder is created automatically if it doesn't exist.

### Upload to Specific Folder

```
Convert https://www.youtube.com/watch?v=dQw4w9WgXcQ to MP3 and upload to my Music folder in Google Drive
```

Claude will call:
```json
{
  "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "upload_to_drive": true,
  "drive_folder": "Music"
}
```

The folder will be created automatically if it doesn't exist.

### Custom Bitrate + Upload

```
Convert https://www.youtube.com/watch?v=dQw4w9WgXcQ to 320k MP3 and upload to Google Drive
```

Claude will call:
```json
{
  "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "bitrate": "320k",
  "upload_to_drive": true
}
```

## Response Format

When upload is successful, you'll see:

```
✅ Download and conversion complete!

📁 File Details:
- Path: /downloads/Never Gonna Give You Up.mp3
- Size: 8.42 MB
- Bitrate: 192k
- Duration: 3:33

🏷️ Metadata (Embedded):
- Title: Never Gonna Give You Up
- Artist: Rick Astley
- Album: YouTube
- Year: 2009
- Album Art: ✅ Embedded

📊 Statistics:
- Views: 1,234,567,890
- Likes: 12,345,678
- Uploader: Rick Astley

🔗 Source: https://www.youtube.com/watch?v=dQw4w9WgXcQ

💾 File saved to: /downloads/Never Gonna Give You Up.mp3

☁️ Google Drive Upload:
- File ID: 1abc123xyz456def789
- View Link: https://drive.google.com/file/d/1abc123xyz456def789/view
- Folder: MCP-YouTube-to-MP3
- Status: ✅ Upload successful
```

## Troubleshooting

### Error: "Google Drive credentials not configured"

**Solution:**
1. Verify credentials file exists in `~/google-credentials/`
2. Check `.env` file has correct path variables
3. Restart docker container
4. Check health endpoint: `curl http://127.0.0.1:3004/health`

### Error: "Failed to upload to Google Drive: 403 Forbidden"

**Causes:**
- Service account method: Folder not shared with service account
- OAuth method: Token expired or revoked

**Solution (Service Account):**
1. Find service account email in credentials JSON
2. Share target folder with that email address

**Solution (OAuth):**
1. Delete `google-drive-token.json`
2. Re-run `generate_token.py`
3. Copy new token to credentials directory
4. Restart container

### Error: "Invalid credentials"

**Solution:**
1. Verify JSON file is valid (check with `cat ~/google-credentials/*.json`)
2. Ensure you enabled Google Drive API in Cloud Console
3. For OAuth: Regenerate token
4. For Service Account: Regenerate key

### Files Upload but Don't Appear

**Causes:**
- Service account uploads to its own Drive space (invisible to you)

**Solution:**
1. Make sure you're using a shared folder
2. Check the folder is shared with service account email
3. Or use OAuth method for personal Drive access

### Health Check Shows `google_drive_configured: false`

**Solution:**
1. Check environment variable is set:
   ```bash
   docker exec mcp-youtube-to-mp3 env | grep GOOGLE
   ```
2. Verify credentials file is mounted:
   ```bash
   docker exec mcp-youtube-to-mp3 ls -la /app/credentials/
   ```
3. Check docker-compose.yml has correct volume mount

## Security Notes

- **Never commit credentials to git** - they're secrets!
- Credentials directory should have restricted permissions: `chmod 700 ~/google-credentials`
- Credential files should be read-only: `chmod 600 ~/google-credentials/*.json`
- Use OAuth for personal use, Service Account for automation
- Service accounts should only have access to specific shared folders

## Optional: Disable Google Drive

To use the service without Google Drive:

1. Don't set `GOOGLE_DRIVE_CREDENTIALS_*` environment variables
2. Don't use `upload_to_drive` parameter
3. Files will only save to local downloads directory

The Google Drive feature is completely optional and the service works fine without it.
