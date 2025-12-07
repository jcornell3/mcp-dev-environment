# YouTube to MP3 MCP Server

Download YouTube videos and convert to MP3 with metadata preservation. Optionally upload to Google Drive.

## Features

- **High-Quality Conversion**: Convert YouTube videos to MP3 with configurable bitrates (128k-320k)
- **Metadata Preservation**: Automatically embeds ID3 tags (title, artist, album, year, description)
- **Album Art**: Downloads and embeds video thumbnail as album art
- **Google Drive Upload**: Optional upload to Google Drive with folder organization
- **MCP Protocol**: Fully compliant MCP server with HTTP/SSE transport

## Usage

### Basic Conversion

```
Convert https://www.youtube.com/watch?v=dQw4w9WgXcQ to MP3
```

Downloads MP3 to local downloads directory.

### Upload to Google Drive

```
Convert https://www.youtube.com/watch?v=dQw4w9WgXcQ to MP3 in my Google Drive
```

Converts and uploads to the standardized **"MCP-YouTube-to-MP3"** folder (created automatically if doesn't exist).

### Upload to Specific Folder

```
Convert https://www.youtube.com/watch?v=dQw4w9WgXcQ to MP3 and upload to my Music folder in Google Drive
```

Converts and uploads to "Music" folder (created automatically if doesn't exist).

### Custom Quality

```
Convert https://www.youtube.com/watch?v=dQw4w9WgXcQ to 320k MP3
```

Available bitrates:
- **128k** - Low quality, small file size
- **192k** - Standard quality (default)
- **256k** - High quality
- **320k** - Maximum quality, large file size

## Tool Parameters

**Tool: `youtube_to_mp3`**

Parameters:
- `video_url` (required): YouTube URL or video ID
- `bitrate` (optional): Audio bitrate - 128k, 192k, 256k, or 320k (default: 192k)
- `preserve_metadata` (optional): Embed ID3 tags and album art (default: true)
- `output_filename` (optional): Custom filename without .mp3 extension
- `upload_to_drive` (optional): Upload to Google Drive (default: false)
- `drive_folder` (optional): Google Drive folder name (default: "MCP-YouTube-to-MP3")

## Environment Variables

- `MCP_API_KEY`: API key for authentication (required)
- `PORT`: Server port (default: 3000)
- `DOWNLOADS_DIR`: Local downloads directory (default: /app/downloads)
- `GOOGLE_DRIVE_CREDENTIALS_JSON`: Path to Google Drive credentials inside container (optional)
- `GOOGLE_SERVICE_ACCOUNT_JSON`: Path to service account JSON inside container (optional)

## Google Drive Setup

See [GOOGLE_DRIVE_SETUP.md](GOOGLE_DRIVE_SETUP.md) for detailed instructions on configuring Google Drive upload.

**Quick Setup:**

1. Create OAuth2 credentials in Google Cloud Console
2. Generate user token: `python generate_token.py`
3. Save token to `~/google-credentials/google-drive-token.json`
4. Update `.env`:
   ```bash
   GOOGLE_DRIVE_CREDENTIALS_PATH=/home/YOUR_USERNAME/google-credentials
   GOOGLE_DRIVE_CREDENTIALS_JSON=/app/credentials/google-drive-token.json
   ```
5. Restart service

## Docker Deployment

### Build

```bash
docker build -t mcp-youtube-to-mp3 .
```

### Run (Without Google Drive)

```bash
docker run -d \
  -p 3004:3000 \
  -e MCP_API_KEY=your-api-key-here \
  -v /path/to/downloads:/downloads \
  --name mcp-youtube-to-mp3 \
  mcp-youtube-to-mp3
```

### Run (With Google Drive)

```bash
docker run -d \
  -p 3004:3000 \
  -e MCP_API_KEY=your-api-key-here \
  -e GOOGLE_DRIVE_CREDENTIALS_JSON=/app/credentials/google-drive-token.json \
  -v /path/to/downloads:/downloads \
  -v /path/to/credentials:/app/credentials:ro \
  --name mcp-youtube-to-mp3 \
  mcp-youtube-to-mp3
```

### Health Check

```bash
curl http://localhost:3004/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "youtube-to-mp3",
  "api_key_configured": true,
  "google_drive_configured": true
}
```

## Development

### Local Testing

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run server:**
   ```bash
   export MCP_API_KEY=test-key
   export DOWNLOADS_DIR=/tmp/downloads
   mkdir -p /tmp/downloads
   python server.py
   ```

3. **Test endpoint:**
   ```bash
   curl -X POST http://localhost:3000/messages \
     -H "Authorization: Bearer test-key" \
     -H "Content-Type: application/json" \
     -d '{"method":"tools/call","params":{"name":"youtube_to_mp3","arguments":{"video_url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}},"jsonrpc":"2.0","id":1}'
   ```

## Output Format

The MP3 file includes:

**ID3 Tags:**
- Title (TIT2): Video title
- Artist (TPE1): Uploader name
- Album (TALB): "YouTube" or video album
- Year (TDRC): Upload year
- Comment (COMM): Video description + stats
- URL (WXXX): Source YouTube URL

**Album Art:**
- Embedded thumbnail as JPEG
- Resized to 500x500 max
- Type: Front cover

**File Location:**
- Local: `DOWNLOADS_DIR/<video-title>.mp3`
- Windows (via symlink): `C:\Users\<username>\Downloads\<video-title>.mp3`
- Google Drive: "MCP-YouTube-to-MP3" folder (default) or specified folder

## Legal Notice

⚠️ **Copyright Compliance Required**

Use this tool only with:
- Your own videos
- Public domain content
- Creative Commons licensed content
- Content you have explicit permission to download

Respect:
- YouTube Terms of Service
- Copyright laws
- Content creator rights

This is a demonstration project with no warranty. Users are responsible for ensuring their usage complies with all applicable laws and terms of service.

## Troubleshooting

### Error: "Video not found"

**Causes:**
- Invalid URL
- Private/deleted video
- Region-locked content
- Age-restricted video

**Solution:**
- Verify URL is correct
- Check video is public
- Try different video to test

### Error: "Google Drive credentials not configured"

**Solution:**
See [GOOGLE_DRIVE_SETUP.md](GOOGLE_DRIVE_SETUP.md)

### Files Don't Appear in Windows Downloads

**Solution:**
Verify symbolic link:
```bash
ls -la ~/downloads
# Should show: downloads -> /mnt/c/Users/YOUR_USERNAME/Downloads
```

If missing, create:
```bash
ln -s /mnt/c/Users/YOUR_USERNAME/Downloads ~/downloads
```

### Poor Audio Quality

**Solution:**
Use higher bitrate:
```
Convert <URL> to 320k MP3
```

Trade-off: Higher bitrate = better quality but larger file size.

## Support

For issues or questions:
- Check server logs: `docker logs mcp-youtube-to-mp3`
- Review health endpoint: `curl http://127.0.0.1:3004/health`
- See deployment guide: `/mcp-dev-environment/DEPLOYMENT.md`
- Google Drive setup: [GOOGLE_DRIVE_SETUP.md](GOOGLE_DRIVE_SETUP.md)
