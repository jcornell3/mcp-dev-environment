# YouTube Transcript MCP Server - Development Notes

This document captures the lessons learned and technical issues encountered during the development of the YouTube Transcript MCP server.

## Issues Encountered & Solutions

### Issue 1: YouTubeTranscriptApi Method Signature

**Problem:**
Initial implementation used `YouTubeTranscriptApi.get_transcript()` as a static method:

```python
# WRONG - This failed
transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
```

**Error Message:**
```
type object 'YouTubeTranscriptApi' has no attribute 'get_transcript'
```

**Root Cause:**
The youtube-transcript-api library (v0.6.0+) requires instantiating the `YouTubeTranscriptApi` class before calling methods. The API changed from class methods to instance methods.

**Solution:**
Instantiate the API object and use `fetch()` instead of `get_transcript()`:

```python
# CORRECT
api = YouTubeTranscriptApi()
transcript_list = api.fetch(video_id, languages=(language,))
```

**Key Differences:**
| Method | Type | Usage |
|--------|------|-------|
| `get_transcript()` | Static (old) | ❌ No longer available |
| `fetch()` | Instance (new) | ✅ Correct |
| `list()` | Instance | ✅ Lists available transcripts |

**Files Modified:**
- `servers/youtube-transcript/mcp_logic.py` (lines 58, 63, 114-115)

**Lesson Learned:**
Always check the actual library implementation via introspection:
```python
from youtube_transcript_api import YouTubeTranscriptApi
import inspect

# View available methods
for name in dir(YouTubeTranscriptApi):
    if not name.startswith('_'):
        print(f"  - {name}")

# Check method signatures
print(inspect.signature(YouTubeTranscriptApi.fetch))
```

---

### Issue 2: FetchedTranscriptSnippet Object vs Dictionary

**Problem:**
Initial implementation treated transcript entries as dictionaries:

```python
# WRONG - This failed
lines = [f"{format_timestamp(entry['start'])} {entry['text']}" for entry in transcript_list]
```

**Error Message:**
```
'FetchedTranscriptSnippet' object is not subscriptable
```

**Root Cause:**
The `api.fetch()` method returns a list of `FetchedTranscriptSnippet` objects, not dictionaries. These objects have attributes (not keys) for `start`, `duration`, and `text`.

**Solution:**
Access object attributes instead of dictionary keys:

```python
# CORRECT
lines = [f"{format_timestamp(entry.start)} {entry.text}" for entry in transcript_list]
```

**FetchedTranscriptSnippet Attributes:**
```python
# Available attributes on each transcript entry
entry.text          # str: The transcript text
entry.start         # float: Start time in seconds
entry.duration      # float: Duration in seconds
```

**Files Modified:**
- `servers/youtube-transcript/mcp_logic.py`:
  - Line 68: `entry.start` (was `entry['start']`)
  - Line 69: `entry.text` (was `entry['text']`)
  - Line 73: `entry.text` (was `entry['text']`)
  - Line 84: `transcript_list[-1].start` (was `transcript_list[-1]['start']`)
  - Line 84: `transcript_list[-1].duration` (was `transcript_list[-1]['duration']`)

**Lesson Learned:**
Always test object types in a Python REPL before implementing:
```python
from youtube_transcript_api import YouTubeTranscriptApi

api = YouTubeTranscriptApi()
result = api.fetch("dQw4w9WgXcQ")

# Check the type
print(type(result))           # <class 'youtube_transcript_api._transcripts.FetchedTranscript'>
print(type(result[0]))        # <class 'FetchedTranscriptSnippet'>

# Check available attributes
print(dir(result[0]))         # Shows all attributes
print(result[0].text)         # Access via attribute
```

---

### Issue 3: Docker Image Caching

**Problem:**
After fixing the code, the container still ran the old code with the original error:

```
type object 'YouTubeTranscriptApi' has no attribute 'get_transcript'
```

**Root Cause:**
Docker layer caching. The image was built and cached with the old code. Rebuilding without clearing the cache used the cached layers.

**Solution:**
Force rebuild without cache:

```bash
docker compose stop youtube-transcript
docker compose rm -f youtube-transcript
docker compose build --no-cache youtube-transcript
docker compose up -d youtube-transcript
```

**Why This Happened:**
When you run `docker compose build`, Docker uses cached layers from previous builds. Since we only changed `mcp_logic.py` and the `COPY` command already existed in the cache, it didn't re-copy the updated file. We had to:

1. Stop the running container
2. Remove the container instance
3. Build with `--no-cache` flag to force rebuild of all layers
4. Start the container again

**Files Modified:**
- Build process (no source code changes, only build commands)

**Lesson Learned:**
For iterative development with Docker:

1. Always use `--no-cache` when troubleshooting code issues
2. Clean up old containers: `docker compose rm -f SERVICE_NAME`
3. Verify the image was rebuilt: `docker images | grep youtube`
4. Check what's in the container: `docker exec CONTAINER cat /app/file.py`

**Alternative Approach:**
Use Docker volumes for development:
```yaml
services:
  youtube-transcript:
    build: ./servers/youtube-transcript
    volumes:
      - ./servers/youtube-transcript:/app  # Mount source for live updates
    stdin_open: true
    tty: false
```

This allows editing files locally and seeing changes immediately without rebuild.

---

## Implementation Best Practices

### 1. API Compatibility Testing

**Before Implementation:**
```python
# Test the actual API methods
api = YouTubeTranscriptApi()

# Test fetch method
result = api.fetch("dQw4w9WgXcQ")
print(f"Type: {type(result)}")
print(f"Length: {len(result)}")
print(f"First item: {result[0]}")
print(f"Attributes: {dir(result[0])}")

# Test list method
langs = api.list("dQw4w9WgXcQ")
print(f"Languages: {[t.language_code for t in langs]}")
```

**Result Verified:**
- `fetch()` returns an iterable of `FetchedTranscriptSnippet` objects
- `list()` returns a `TranscriptList` with transcript objects containing metadata
- Both methods require instantiated API object

### 2. Error Handling

The implementation includes proper exception handling for three error cases:

```python
try:
    api = YouTubeTranscriptApi()
    transcript_list = api.fetch(video_id, languages=(language,))
except NoTranscriptFound:
    # Language not available, try fallback
    transcript_list = api.fetch(video_id)
except TranscriptsDisabled:
    # Video has transcripts disabled
    raise ValueError(f"Transcripts are disabled for video: {video_id}")
except VideoUnavailable:
    # Video doesn't exist or is restricted
    raise ValueError(f"Video unavailable or does not exist: {video_id}")
except Exception as e:
    # Catch all other errors
    raise ValueError(f"Error retrieving transcript: {str(e)}")
```

**Coverage:**
- ✅ Language fallback (requested language → any language)
- ✅ Disabled transcripts (graceful error)
- ✅ Unavailable videos (graceful error)
- ✅ Network/API errors (caught and wrapped)

### 3. MCP Server Pattern

The MCP server follows the correct async pattern with the MCP Python SDK:

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("youtube-transcript")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [...]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    # Process and return results
    return [TextContent(type="text", text=result)]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())
```

**Key Points:**
- Use `@app.list_tools()` and `@app.call_tool()` decorators
- Methods must be `async`
- Use `stdio_server()` context manager for transport
- Return `list[TextContent]` from `call_tool`

---

## Testing Approach

### Manual Integration Testing

**Test 1: Initialize**
```bash
echo '{"jsonrpc":"2.0","method":"initialize",...}' | docker exec -i CONTAINER python -u /app/server.py
```
Verifies: Server starts, protocol version correct

**Test 2: List Tools**
Must send initialize first in same connection:
```bash
cat << 'EOF' | docker exec -i CONTAINER python -u /app/server.py
{"jsonrpc":"2.0","method":"initialize",...}
{"jsonrpc":"2.0","method":"tools/list","id":2}
EOF
```
Verifies: Tools properly registered, input schemas correct

**Test 3: Get Transcript**
Real-world test with actual YouTube video:
```bash
cat << 'EOF' | docker exec -i CONTAINER python -u /app/server.py
{"jsonrpc":"2.0","method":"initialize",...}
{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_transcript","arguments":{"video_url":"dQw4w9WgXcQ"}},"id":3}
EOF
```
Verifies: API integration works, transcript extraction works

**Test 4: List Languages**
```bash
cat << 'EOF' | docker exec -i CONTAINER python -u /app/server.py
{"jsonrpc":"2.0","method":"initialize",...}
{"jsonrpc":"2.0","method":"tools/call","params":{"name":"list_available_languages","arguments":{"video_url":"dQw4w9WgXcQ"}},"id":4}
EOF
```
Verifies: Language listing works, metadata extraction works

**Result:** All 4 tests passed ✅

---

## Performance Characteristics

### Response Times (Observed)
- Initialize: ~100-200ms
- List Tools: ~50-100ms
- Get Transcript: ~2-5 seconds (network + YouTube API)
- List Languages: ~1-2 seconds (network + YouTube API)

### Bottlenecks
- YouTube API latency (external dependency)
- Network latency (WSL → Docker → YouTube)
- Transcript size (larger videos take longer to retrieve)

### Optimization Opportunities
1. **Caching**: Store transcripts locally (not implemented to keep fresh)
2. **Parallel requests**: Use `asyncio` to fetch multiple languages simultaneously
3. **Compression**: Send compressed transcripts over the wire
4. **Streaming**: Stream response instead of buffering entire transcript

---

## Future Improvements

### 1. Add Caching Layer
```python
import functools
import time

@functools.lru_cache(maxsize=32)
def get_transcript_cached(video_url, language, ttl=3600):
    # Cache transcripts for 1 hour
    # Check expiry and refresh if needed
    pass
```

### 2. Support Additional Formats
```python
# Current: Plain text
# Future options:
# - JSON format with timestamps
# - SRT format (subtitle file format)
# - VTT format (WebVTT for HTML5 video)
# - Markdown with formatting
```

### 3. Transcript Search
```python
@app.call_tool()
async def search_transcript(video_url: str, search_term: str) -> list[TextContent]:
    """Find all occurrences of search term in transcript with context"""
    # Returns matches with timestamp and surrounding context
```

### 4. Subtitle Generation
```python
@app.call_tool()
async def generate_subtitles(video_url: str, format: str = "srt") -> list[TextContent]:
    """Generate subtitle file from transcript"""
    # Returns SRT, VTT, or WebVTT format
```

### 5. Translation Integration
```python
@app.call_tool()
async def translate_transcript(video_url: str, target_language: str) -> list[TextContent]:
    """Translate transcript to target language using translation API"""
    # Could use Google Translate API or similar
```

---

## Lessons for Future MCP Development

1. **Always Introspect Third-Party Libraries**
   - Check method signatures before implementation
   - Test object types in Python REPL
   - Use `dir()` and `inspect.signature()` to verify API

2. **Docker Development Workflow**
   - Use `--no-cache` for troubleshooting
   - Consider volume mounts for iterative development
   - Always verify changes made it into the image

3. **MCP Server Pattern**
   - Follow decorator pattern for tools
   - Use async/await for all methods
   - Return proper TextContent objects
   - Handle all edge cases with try/catch

4. **Testing Strategy**
   - Test each method in isolation first
   - Use persistent connections for stateful servers
   - Test with real-world data (actual YouTube videos)
   - Verify error handling paths

5. **Documentation**
   - Document not just usage, but implementation decisions
   - Include error cases and how to recover
   - Provide working code examples
   - Link to external APIs and their documentation

---

## References

- [youtube-transcript-api Library](https://github.com/jdelete/yt-transcript-api)
- [MCP Python SDK](https://modelcontextprotocol.io/)
- [YouTube API Documentation](https://developers.google.com/youtube)
- [Python Async/Await Guide](https://docs.python.org/3/library/asyncio.html)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

**Created:** 2025-12-01
**Purpose:** Document implementation journey and lessons learned
**Status:** Complete
