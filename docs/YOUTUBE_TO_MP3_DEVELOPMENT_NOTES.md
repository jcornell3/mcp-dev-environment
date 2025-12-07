# YouTube to MP3 MCP Server - Development Notes

This document captures the development journey, challenges encountered, and solutions for the YouTube to MP3 MCP server.

## Project Overview

The YouTube to MP3 MCP server enables Claude to download YouTube videos and convert them to MP3 format with comprehensive metadata preservation:
- ID3 tag embedding (title, artist, album, year, description)
- Album art extraction and embedding (YouTube thumbnail)
- Video statistics preservation (views, likes, uploader)
- Configurable bitrate options (128k, 192k, 256k, 320k)
- **Optional Google Drive upload** (added December 7, 2025)
- Full MCP JSON-RPC protocol compliance

## Architecture

### Core Components

1. **mcp_logic.py** (250+ lines)
   - `extract_video_id(url)` - Parse YouTube URLs and extract video ID
   - `format_file_size(bytes)` - Human-readable file size formatting
   - `format_duration(seconds)` - Time formatting (MM:SS or HH:MM:SS)
   - `embed_metadata(mp3_path, metadata, video_info)` - ID3 tag and album art embedding
   - `youtube_to_mp3()` - Main download and conversion logic

2. **server.py** (250+ lines)
   - MCP Server wrapper using official Python SDK
   - `list_tools()` - Register youtube_to_mp3 tool with input schema
   - `call_tool()` - Execute tool with parameter validation
   - Google Drive upload integration (optional)
   - Error handling with troubleshooting suggestions
   - Health endpoint with Google Drive configuration status

3. **google_drive.py** (NEW - 150+ lines)
   - `get_drive_service()` - Get authenticated Google Drive service
   - `upload_to_drive()` - Upload file to Google Drive
   - `get_or_create_folder()` - Get or create folder by name
   - `is_drive_configured()` - Check if credentials are configured
   - Supports OAuth2 user credentials and Service Account authentication

4. **Dockerfile** (25 lines)
   - Python 3.11-slim base image
   - System dependencies: ffmpeg, wget, ca-certificates
   - Python dependencies: mcp, yt-dlp, mutagen, Pillow, requests, google-api-python-client, google-auth
   - Credentials directory mount point

5. **docker-compose.yml.local**
   - youtube-to-mp3 service with HTTP/SSE transport
   - Volume mount for persistent downloads
   - Volume mount for Google Drive credentials (read-only)
   - Environment variables for Google Drive configuration

## Issues Encountered and Solutions

### Issue 1: Stdout/Stderr Pollution Breaking JSON-RPC Protocol

**Problem:**
yt-dlp library outputs progress messages, warnings, and status updates to stdout/stderr, breaking the clean JSON-RPC protocol stream.

```
[download] 23% of ~8.29 MiB at 1.23 MiB/s
[ffmpeg] Destination: file.mp3
Warning: Could not embed metadata: an ID3 tag already exists
{"jsonrpc":"2.0",...}  # <-- Mixed with non-JSON output
```

**Root Cause:**
By default, yt-dlp outputs comprehensive progress information and FFmpeg integration produces status messages. The MCP protocol requires pure JSON-RPC on stdout.

**Solution:**
Configure yt-dlp to be completely silent:

```python
ydl_opts = {
    # ... other options ...
    'quiet': True,           # Suppress all output
    'no_warnings': True,     # Hide warnings
    'noprogress': True,      # Hide progress bars
    'no_color': True,        # Disable ANSI color codes
}
```

**Key Insights:**
- Setting `quiet: False` and `no_warnings: False` causes protocol violations
- Even Python warnings via `print()` in exception handlers pollute stdout
- All output must be suppressed to maintain JSON-RPC protocol integrity
- FFmpeg inherits stderr suppression from yt-dlp configuration

**Files Modified:**
- `servers/youtube-to-mp3/mcp_logic.py` (lines 171-174)

---

### Issue 2: ID3 Tag Conflicts on Repeated Metadata Embedding

**Problem:**
When downloading the same video or reprocessing an MP3 file with existing ID3 tags, the metadata embedding fails:

```
Warning: Could not embed metadata: an ID3 tag already exists
```

**Root Cause:**
The original code used `audio.tags.add()` method, which fails when tags already exist. The method throws an exception rather than updating existing tags.

```python
# WRONG - Fails with existing tags
audio.tags.add(TIT2(encoding=3, text=metadata['title']))
# Error: an ID3 tag already exists
```

**Solution:**
Use dictionary-style assignment instead of `.add()` method, with safe deletion of existing tags:

```python
# CORRECT - Safely handles existing tags
for tag in ['TIT2', 'TPE1', 'TALB', 'TDRC']:
    try:
        del audio.tags[tag]
    except KeyError:
        pass  # Tag doesn't exist, that's fine

audio.tags['TIT2'] = TIT2(encoding=3, text=metadata['title'])
audio.tags['TPE1'] = TPE1(encoding=3, text=metadata['artist'])
audio.tags['TALB'] = TALB(encoding=3, text=metadata['album'])
```

**Additional Improvements:**
- For COMM (comments) and WXXX (custom) tags, iterate existing keys and delete matching ones
- Handle APIC (album art) deletion before re-embedding
- Use `try/except KeyError` pattern for safe deletion

```python
# Safe deletion for multi-value tag types
for key in list(audio.tags.keys()):
    if key.startswith('COMM:') and 'Description' in key:
        del audio.tags[key]
audio.tags['COMM:Description'] = COMM(...)
```

**Files Modified:**
- `servers/youtube-to-mp3/mcp_logic.py` (lines 67-109, 127-129)

---

### Issue 3: Metadata Embedding Exception Handling

**Problem:**
Print statements in exception handlers were being displayed, polluting logs and potentially stdout.

```python
except Exception as e:
    print(f"Warning: Could not embed album art: {e}")  # <-- Pollutes output
    metadata['thumbnail_embedded'] = False
```

**Root Cause:**
Using `print()` in exception handlers and metadata embedding functions was intended for debugging but actually breaks the clean JSON-RPC output contract.

**Solution:**
Remove all print statements from production code in the MCP server context. The result dict in the JSON-RPC response provides sufficient diagnostic information.

```python
except Exception as e:
    metadata['thumbnail_embedded'] = False
    # No print - let the error propagate or handle gracefully
```

**Learning:**
In MCP servers where stdout is the communication channel, use structured error returns via JSON-RPC instead of print statements.

**Files Modified:**
- `servers/youtube-to-mp3/mcp_logic.py` (line 140)

---

### Issue 4: Google Drive OAuth2 Setup - Desktop vs Web Application

**Problem:**
Initial OAuth2 setup used "Desktop app" application type, which doesn't support configurable redirect URIs, causing OAuth flow failures.

```
Error 400: invalid_request
Missing parameter: redirect_uri
```

**Root Cause:**
Google Cloud Console's "Desktop app" OAuth client type doesn't provide a field to add redirect URIs. The generated authorization URL doesn't include the redirect_uri parameter, which is required for the manual OAuth flow in WSL/Linux environments without a browser.

**Solution:**
Changed OAuth client type from "Desktop app" to "Web application":

1. **OAuth Client Configuration:**
   - Application type: **Web application** (NOT Desktop app)
   - Authorized redirect URIs: `http://localhost:8080`
   - Test users must be added in both "Test users" section AND "Audience" screen

2. **Token Generation Script:**
```python
from google_auth_oauthlib.flow import Flow  # Not InstalledAppFlow

# Required for localhost HTTP
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

flow = Flow.from_client_secrets_file(
    CLIENT_SECRETS_FILE,
    scopes=SCOPES,
    redirect_uri="http://localhost:8080"  # Explicit redirect URI
)
```

3. **Manual Authorization Process:**
   - Script generates authorization URL
   - User opens URL in browser and authorizes
   - Browser redirects to `http://localhost:8080/?state=...&code=...`
   - Browser shows "This site can't be reached" - **this is normal**
   - User copies entire URL from address bar
   - Script exchanges authorization code for access token

**Key Insights:**
- Desktop app OAuth clients work for `InstalledAppFlow.run_local_server()` but not manual flows
- Web application clients require explicit redirect URI configuration
- `OAUTHLIB_INSECURE_TRANSPORT=1` is required for HTTP localhost in production OAuth library
- Test users need to be added in Audience screen, not just OAuth consent screen

**Files Created:**
- `servers/youtube-to-mp3/GOOGLE_DRIVE_SETUP.md` - Complete setup guide
- Token generation scripts using Flow instead of InstalledAppFlow

---

### Issue 5: Standardized Folder Name for Google Drive Uploads

**Problem:**
Initial implementation allowed custom folder names but defaulted to Google Drive root, making it difficult to find uploaded files.

**Solution:**
Implemented standardized default folder name "MCP-YouTube-to-MP3":

```python
# In server.py
folder_name = drive_folder if drive_folder else "MCP-YouTube-to-MP3"
folder_id = get_or_create_folder(folder_name)
```

**Benefits:**
- All uploads without specified folder go to consistent location
- Easier to find and organize downloaded MP3s
- Folder created automatically if doesn't exist
- Users can still override with custom folder via `drive_folder` parameter

**Files Modified:**
- `servers/youtube-to-mp3/server.py` (lines 131-133)
- `servers/youtube-to-mp3/tests/test_google_drive_integration.py`

---

## Implementation Best Practices

### 1. yt-dlp Configuration for MCP Servers

When using yt-dlp in an MCP server context:

```python
ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'outtmpl': output_template,
    'writethumbnail': True,
    'quiet': True,              # CRITICAL: Must be True for MCP
    'no_warnings': True,        # CRITICAL: Must be True for MCP
    'noprogress': True,         # CRITICAL: Hide progress bars
    'no_color': True,           # CRITICAL: Remove ANSI codes
}
```

**Why Each Setting Matters:**
- `quiet: True` - Suppresses download progress, info, and debug messages
- `no_warnings: True` - Hides deprecation and compatibility warnings
- `noprogress: True` - Disables progress bar (redundant with quiet but explicit)
- `no_color: True` - Removes ANSI escape codes that break JSON parsing

### 2. ID3 Tag Manipulation with Mutagen

When working with ID3 tags using Mutagen:

**Creating Tags:**
```python
audio = MP3(mp3_path, ID3=ID3)
if audio.tags is None:
    audio.add_tags()
```

**Updating Tags (Safe Pattern):**
```python
# Method 1: Delete then set (for single-value tags)
try:
    del audio.tags['TIT2']
except KeyError:
    pass
audio.tags['TIT2'] = TIT2(encoding=3, text='New Title')

# Method 2: Iterate and delete (for multi-value tags)
for key in list(audio.tags.keys()):
    if key.startswith('COMM:') and 'Description' in key:
        del audio.tags[key]
audio.tags['COMM:Description'] = COMM(...)
```

**Saving:**
```python
audio.save()  # Writes all tags to file
```

### 3. Album Art Handling

Extract thumbnail and embed as APIC tag:

```python
import requests
from PIL import Image
import io

response = requests.get(thumbnail_url, timeout=10)
img = Image.open(io.BytesIO(response.content))
img.thumbnail((500, 500), Image.Resampling.LANCZOS)

# Convert to JPEG
img_byte_arr = io.BytesIO()
img.convert('RGB').save(img_byte_arr, format='JPEG', quality=90)
img_data = img_byte_arr.getvalue()

# Delete existing album art
for key in list(audio.tags.keys()):
    if key.startswith('APIC'):
        del audio.tags[key]

# Embed new album art
audio.tags['APIC'] = APIC(
    encoding=3,
    mime='image/jpeg',
    type=3,  # Cover (front)
    desc='Album Art',
    data=img_data
)
```

### 4. MCP Server Error Handling

Return structured errors via JSON-RPC instead of printing:

```python
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        # Validate inputs
        if not arguments.get('video_url'):
            raise ValueError("video_url is required")

        # Perform operation
        result = youtube_to_mp3(...)
        return [TextContent(type="text", text=result)]

    except Exception as e:
        error_msg = f"❌ Error: {str(e)}\n\nTroubleshooting:\n"
        error_msg += "- Verify the YouTube URL is correct\n"
        error_msg += "- Check if video is public (not private/deleted)\n"
        # ... more troubleshooting ...
        raise ValueError(error_msg)
```

The exception message is returned in the JSON-RPC response, providing diagnostic info without polluting stdout.

### 5. Google Drive Integration

**OAuth2 Configuration:**
```python
# Use Flow (not InstalledAppFlow) for manual auth flows
from google_auth_oauthlib.flow import Flow

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Required for localhost

flow = Flow.from_client_secrets_file(
    credentials_file,
    scopes=['https://www.googleapis.com/auth/drive.file'],
    redirect_uri='http://localhost:8080'
)
```

**Standardized Folder Pattern:**
```python
# Default to standardized folder name
folder_name = user_folder if user_folder else "MCP-YouTube-to-MP3"
folder_id = get_or_create_folder(folder_name)
```

**Service Initialization:**
```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def get_drive_service():
    """Get authenticated Drive service, supporting both OAuth2 and Service Account"""
    creds_path = os.environ.get('GOOGLE_DRIVE_CREDENTIALS_JSON')

    if creds_path and os.path.exists(creds_path):
        with open(creds_path, 'r') as f:
            creds_data = json.load(f)

        # Check if it's OAuth2 user credentials or Service Account
        if 'refresh_token' in creds_data:
            # OAuth2 user credentials
            creds = Credentials.from_authorized_user_info(creds_data)
        else:
            # Service Account credentials
            from google.oauth2 import service_account
            creds = service_account.Credentials.from_service_account_info(
                creds_data,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )

        return build('drive', 'v3', credentials=creds)

    return None
```

**Upload with Folder Organization:**
```python
from googleapiclient.http import MediaFileUpload

def upload_to_drive(file_path: str, folder_id: Optional[str] = None) -> dict:
    service = get_drive_service()

    file_metadata = {'name': os.path.basename(file_path)}
    if folder_id:
        file_metadata['parents'] = [folder_id]

    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id,name,webViewLink,webContentLink,size'
    ).execute()

    return file
```

---

## Testing Approach

### Manual Integration Testing

**Test 1: Clean Initialize**
```bash
echo '{"jsonrpc":"2.0","method":"initialize",...}' | \
  docker exec -i mcp-dev-environment-youtube-to-mp3-1 python -u /app/server.py
```
Verifies: Pure JSON output with no pollution

**Test 2: Tools Listing**
```bash
cat << 'EOF' | docker exec -i mcp-dev-environment-youtube-to-mp3-1 python -u /app/server.py
{"jsonrpc":"2.0","method":"initialize",...}
{"jsonrpc":"2.0","method":"tools/list","id":2}
EOF
```
Verifies: Tool schema properly defined

**Test 3: Real Download**
```bash
cat << 'EOF' | docker exec -i mcp-dev-environment-youtube-to-mp3-1 python -u /app/server.py
{"jsonrpc":"2.0","method":"initialize",...}
{"jsonrpc":"2.0","method":"tools/call","params":{"name":"youtube_to_mp3","arguments":{"video_url":"dQw4w9WgXcQ"}},"id":2}
EOF
```
Verifies: Download completes, metadata embedded, no pollution

**Test 4: Verify Metadata**
```bash
file /app/downloads/*.mp3
# Output should show: Audio file with ID3 version 2.4.0
```

---

## Performance Characteristics

### Observed Metrics
- Initialize: ~100-200ms
- Tools/list: ~50-100ms
- Video download: ~15-45 seconds (depends on video duration and bitrate)
- FFmpeg conversion: ~5-15 seconds
- Metadata embedding: ~1-3 seconds (thumbnail download and ID3 write)
- **Total typical operation**: 20-60 seconds

### Bottlenecks
1. YouTube API latency (network, ~2-5s)
2. Video download speed (depends on file size and bandwidth)
3. FFmpeg audio extraction (linear with duration)
4. Thumbnail download and resize (network + image processing)
5. ID3 tag and album art writing (I/O bound)

### Optimization Opportunities
1. **Caching**: Store downloaded videos temporarily to avoid re-downloading
2. **Parallel downloads**: Use asyncio to fetch thumbnail while extracting audio
3. **Format selection**: Smarter bitrate selection based on source quality
4. **Streaming**: Stream response instead of buffering entire operation
5. **Batch processing**: Support downloading multiple videos in one request

---

## Security Considerations

### Legal and Compliance
- Tool includes copyright/ToS disclaimer in description
- Educates users about permitted use cases
- Recommends checking permissions before downloading

### Technical Security
- Input validation for video URLs
- Bitrate enum validation (restricts to allowed values)
- Timeout on all network requests (10 seconds for thumbnail download)
- Temporary file cleanup (webp thumbnails in downloads dir)
- No credential storage or transmission

### Potential Risks
- Users downloading copyrighted content without permission
- Terms of Service violations (YouTube prohibits automated downloading)
- Disk space exhaustion with large downloads
- Network resource consumption

**Mitigation:**
- Provide clear warnings in tool description
- Implement download size limits in future versions
- Add rate limiting to prevent abuse
- Log all operations for audit purposes

---

## Future Enhancements

### 1. Additional Audio Formats
```python
# Support other formats beyond MP3
supported_formats = ['mp3', 'aac', 'wav', 'flac', 'opus']
```

### 2. Batch Processing
```python
@app.call_tool()
async def batch_download(video_urls: list[str], format: str) -> list[TextContent]:
    """Download multiple videos in sequence"""
    results = []
    for url in video_urls:
        results.append(youtube_to_mp3(url, ...))
    return results
```

### 3. Quality/Bitrate Presets
```python
presets = {
    'podcast': '64k',      # Small file size
    'standard': '192k',    # Balanced
    'music': '320k',       # High quality
    'archive': 'lossless'  # Future: FLAC
}
```

### 4. Transcript Extraction
```python
# Combine with youtube-transcript server
@app.call_tool()
async def download_with_transcript(video_url: str) -> list[TextContent]:
    """Download MP3 and extract transcript"""
    mp3 = youtube_to_mp3(video_url)
    transcript = youtube_to_transcript(video_url)
    return [mp3, transcript]
```

### 5. Metadata Enrichment
```python
# Pull additional metadata from music databases
from mutagen.id3 import TALB, TPE2  # Album, Album Artist

# Query MusicBrainz, Discogs, or similar
metadata['album_artist'] = lookup_artist(metadata['artist'])
metadata['genre'] = lookup_genre(metadata['title'], metadata['artist'])
```

### 6. Storage Backend
```python
# Instead of local filesystem, support:
# - S3/Cloud Storage
# - Database streaming
# - HTTP file serving
# - CDN distribution
```

---

## Lessons Learned

### 1. MCP Protocol Strictness
**Learning:** MCP servers must output pure JSON-RPC on stdout with zero pollution.
- Even logging statements break the protocol
- External libraries must be silenced or wrapped
- Test with actual JSON parsers to verify output

### 2. Library Configuration Deep Dives
**Learning:** Always test third-party library output behavior in MCP context.
- yt-dlp has many output modes; `quiet: True` is essential
- FFmpeg output is inherited from yt-dlp settings
- Documentation alone isn't sufficient; test empirically

### 3. ID3 Tag Manipulation Edge Cases
**Learning:** Mutagen's tag handling is strict about duplicates and conflicts.
- `.add()` method fails with existing tags
- Dictionary assignment is more forgiving
- Multi-value tags (COMM, WXXX) need special handling
- Always check for existing keys before deletion

### 4. Docker Development Workflow
**Learning:** Iterative development with Docker requires attention to caching.
- Copy code changes alone don't trigger rebuild
- Use `docker compose build --no-cache` for debugging
- Verify changes made it into container: `docker exec cat /app/file.py`
- Clean containers between major changes: `docker compose rm -f service`

### 5. Error Handling Strategy
**Learning:** In MCP context, structure errors in the JSON-RPC response.
- Don't use print() or logging for errors
- Return detailed error messages in the result
- Include troubleshooting suggestions in error text
- Use isError flag in response to signal failure

---

## References

- [yt-dlp GitHub](https://github.com/yt-dlp/yt-dlp)
- [Mutagen Documentation](https://mutagen.readthedocs.io/)
- [ID3 Tag Specification](https://id3.org/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [Pillow (PIL) Documentation](https://pillow.readthedocs.io/)

---

**Document Status:** Complete
**Created:** 2025-12-02
**Last Updated:** 2025-12-07
**Purpose:** Capture development journey and lessons learned for future MCP server implementations
**Audience:** Developers building MCP servers with similar requirements

---

## Additional Documentation

- **[GOOGLE_DRIVE_SETUP.md](../servers/youtube-to-mp3/GOOGLE_DRIVE_SETUP.md)** - Complete Google Drive integration setup guide
- **[YouTube to MP3 Server README](../servers/youtube-to-mp3/README.md)** - Server documentation and usage examples
- **[Google Drive Integration Tests](../servers/youtube-to-mp3/tests/test_google_drive_integration.py)** - Comprehensive unit tests
