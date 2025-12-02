# YouTube Transcript MCP Server Usage Guide

This guide covers how to use the YouTube Transcript MCP server in Claude Desktop.

## Overview

The YouTube Transcript MCP server allows you to extract transcripts/captions from YouTube videos. It supports multiple languages, auto-generated captions, and timestamp formatting.

**Server Name in Claude Desktop:** `youtube-transcript-local`

## Available Tools

### 1. get_transcript

Retrieves the complete transcript or captions for a YouTube video.

**Parameters:**
- `video_url` (string, required): YouTube URL or video ID
  - Formats supported:
    - `https://www.youtube.com/watch?v=VIDEO_ID`
    - `https://youtu.be/VIDEO_ID`
    - `https://www.youtube.com/embed/VIDEO_ID`
    - `VIDEO_ID` (direct ID)

- `language` (string, optional): Language code (default: "en")
  - Examples: "en", "es", "fr", "de", "ja", "pt", etc.
  - If the specified language is not available, the server will attempt to retrieve any available transcript

- `include_timestamps` (boolean, optional): Include timestamps in output (default: false)
  - When `true`: Returns format like `[01:23] text here`
  - When `false`: Returns plain text with timestamps removed

**Example Usage in Claude Desktop:**

```
Use the youtube-transcript-local server to get the transcript for the video at:
https://www.youtube.com/watch?v=dQw4w9WgXcQ

Or just the video ID:
dQw4w9WgXcQ
```

**With timestamps:**
```
Get the transcript for dQw4w9WgXcQ with timestamps included
```

**Specific language:**
```
Get the transcript for dQw4w9WgXcQ in Spanish (es)
```

### 2. list_available_languages

Lists all available transcript languages for a specific video.

**Parameters:**
- `video_url` (string, required): YouTube URL or video ID (same formats as get_transcript)

**Returns:**
- List of available language codes
- Language names
- Indication if transcript is auto-generated

**Example Usage in Claude Desktop:**

```
What languages are available for dQw4w9WgXcQ?

Or:

List available transcript languages for:
https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

## Common YouTube Video IDs for Testing

| Video | ID | Languages |
|-------|--|----|
| Rick Astley - Never Gonna Give You Up | `dQw4w9WgXcQ` | 6+ (en, de, ja, pt-BR, es-419, en auto-gen) |
| Most popular music videos | Usually 5-10+ | en, es, fr, de, pt, ja, ko, etc. |
| Educational content | Varies | Often auto-generated in multiple languages |
| News clips | Varies | Multiple languages, often official captions |

## Language Codes Reference

Common language codes:

| Code | Language |
|------|----------|
| en | English |
| es | Spanish (Spain) |
| es-419 | Spanish (Latin America) |
| fr | French |
| de | German (Germany) |
| de-DE | German (Germany) |
| pt | Portuguese |
| pt-BR | Portuguese (Brazil) |
| it | Italian |
| ja | Japanese |
| ko | Korean |
| zh | Chinese (Simplified) |
| zh-Hans | Chinese (Simplified) |
| zh-Hant | Chinese (Traditional) |
| ru | Russian |
| hi | Hindi |
| th | Thai |
| ar | Arabic |

**Note:** Not all languages are available for all videos. Use `list_available_languages` to check what's available for a specific video.

## Timestamp Formatting

When `include_timestamps` is enabled:

**Format Examples:**
- `[00:15] Some text` - For videos under 1 hour
- `[01:23:45] Some text` - For videos over 1 hour

**Timestamp Structure:**
- `[MM:SS]` - Minutes:Seconds format for short videos
- `[HH:MM:SS]` - Hours:Minutes:Seconds format for long videos

## Example Workflows

### Workflow 1: Get English Transcript

```
In Claude Desktop, ask:
"Get the transcript for the video dQw4w9WgXcQ"

Expected output:
- Full transcript in English
- Contains all spoken words and visible text
- Formatted as continuous text with natural line breaks
```

### Workflow 2: Get Transcript with Timestamps

```
Ask: "Get the transcript for dQw4w9WgXcQ with timestamps"

Expected output:
- Same transcript but with [MM:SS] timestamps before each text segment
- Useful for referencing specific moments in the video
```

### Workflow 3: Translate/Check Available Languages

```
Ask: "What languages are available for dQw4w9WgXcQ?"

Server will return:
- List of available languages (e.g., en, es, fr, de, ja, pt-BR)
- Indication which are auto-generated
- Then you can ask for a specific language:
  "Get the German transcript for dQw4w9WgXcQ"
```

### Workflow 4: Check Captions Before Extracting

```
Ask: "Does dQw4w9WgXcQ have Spanish captions?"

Server will list languages, and you'll see if Spanish is available.
If yes:
  "Get the Spanish transcript for dQw4w9WgXcQ"
```

## Error Handling

### Common Errors and Solutions

**"Video unavailable or does not exist"**
- Cause: Invalid video ID or URL
- Solution:
  - Verify the video ID is correct
  - Check the URL format is supported
  - Ensure the video is publicly available

**"Transcripts are disabled for this video"**
- Cause: Video creator disabled captions/transcripts
- Solution:
  - Contact video creator or find alternative
  - Some videos allow comments-based discussions

**"No transcript found in requested language"**
- Cause: The video doesn't have transcripts in that language
- Solution:
  - Use `list_available_languages` to see what's available
  - Request a different language
  - English ("en") usually has the best coverage

**"Invalid YouTube URL or video ID"**
- Cause: Malformed URL or invalid video ID
- Solution:
  - Use one of the supported URL formats
  - Ensure 11-character video ID is correct
  - Remove URL parameters (like ?t=123)

## Performance Considerations

**Response Times:**
- First request: ~3-5 seconds (initial connection + transcript fetch)
- Subsequent requests: ~2-3 seconds
- Large videos (2+ hours): May take up to 10 seconds

**Transcript Size:**
- Short videos (5-10 min): ~1-5 KB
- Medium videos (20-60 min): ~5-20 KB
- Long videos/lectures (90+ min): ~20-100 KB

**Limitations:**
- Videos must be publicly available
- No support for restricted/private videos
- Some creators disable transcripts intentionally
- YouTube may rate-limit if many requests are made rapidly

## Troubleshooting

### Container Not Running

If you get connection errors:

```bash
# Check container status
docker compose ps | grep youtube

# Should show: mcp-dev-environment-youtube-transcript-1 Up

# If not running, start it:
docker compose up -d youtube-transcript

# Verify it started:
docker compose ps | grep youtube
```

### Configuration Not Updated in Claude Desktop

1. Verify config file was copied:
   ```bash
   cat /mnt/c/Users/jcorn/AppData/Roaming/Claude/claude_desktop_config.json
   ```
   Should show "youtube-transcript-local" section

2. Restart Claude Desktop completely (not just close/open)
   - Task Manager → End Claude Desktop process
   - Wait 5 seconds
   - Reopen Claude Desktop

3. Verify the server appears in Claude Desktop's MCP list

### Transcript Content Issues

**Transcript is empty:**
- Cause: Video has no auto-generated captions and no manual captions
- Solution: Check available languages first

**Transcript has strange formatting:**
- Cause: Auto-generated captions have errors (YouTube's limitation)
- Solution: Request a manual caption language if available

**Missing timestamps:**
- Make sure you set `include_timestamps: true` in the request

## Advanced Usage

### Batch Processing Multiple Videos

```
Ask Claude: "Get transcripts for these videos:
1. dQw4w9WgXcQ
2. jNQXAC9IVRw
3. VIDEO_ID_3"

Claude will call the tool multiple times.
```

### Extracting Specific Sections

```
Ask: "Get the transcript for dQw4w9WgXcQ with timestamps,
then find the verse about 'no strangers to love'"

Claude can search the transcript for specific content.
```

### Language Comparison

```
Ask: "Compare the Spanish and English transcripts for dQw4w9WgXcQ"

Claude will call the tool twice (once per language) and compare.
```

## Security & Privacy

- Video transcripts are obtained directly from YouTube's official API
- No caching of transcripts (fresh fetch each time)
- No logging or storage of transcript content
- API calls use standard HTTP/HTTPS
- No authentication credentials needed (YouTube transcripts are public)

## References

- [YouTube Video URL Formats](https://www.youtube.com/)
- [YouTube API Documentation](https://developers.google.com/youtube/v3)
- [ISO 639-1 Language Codes](https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)

## Support

For issues with:

1. **Transcript retrieval**: Check video availability, language codes, and container status
2. **Claude Desktop configuration**: Verify config file location and restart Claude Desktop
3. **Docker container**: Use `docker compose logs youtube-transcript` to see error details
4. **Specific videos**: Use `list_available_languages` tool to verify transcript availability

---

**Last Updated:** 2025-12-01

**Status:** Production Ready
- ✅ Full MCP protocol support
- ✅ Multiple language support
- ✅ Timestamp formatting
- ✅ Error handling
- ✅ Docker containerized
- ✅ Claude Desktop integrated
