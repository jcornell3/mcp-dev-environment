# Santa Clara County Property Tax MCP Server

Real-time property tax information scraper for Santa Clara County, California.

## Features

- **Live Data Scraping**: Uses Playwright to scrape real-time property tax data from Santa Clara County's TellerOnline portal
- **Smart Caching**: Caches results for 24 hours to minimize requests and improve performance
- **Fallback Support**: Falls back to mock data if scraper fails or is disabled
- **MCP Protocol**: Fully compliant MCP server with HTTP/SSE transport

## Architecture

```
┌─────────────────┐
│  Claude Desktop │
└────────┬────────┘
         │ HTTP/SSE
         ▼
┌─────────────────┐
│ Santa Clara MCP │
│     Server      │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────┐
│Scraper │ │ Mock │
│(Live)  │ │ Data │
└───┬────┘ └──────┘
    │
    ▼
┌─────────────────┐
│  TellerOnline   │
│ (Santa Clara)   │
└─────────────────┘
```

## Usage

### Get Property Information

**Tool: `get_property_info`**

Parameters:
- `apn` (string, optional*): Assessor's Parcel Number (e.g., "288-13-033")
  - *Optional if `MY_APN` environment variable is configured

Returns:
- Address
- Tax rate area
- Property type
- Annual tax bill
- Installment details (amounts, due dates, payment status)
- Payment history

**Tool: `get_my_property_info`**

Parameters: None (uses `MY_APN` environment variable)

Returns: Same as `get_property_info`

Use this tool for natural language queries like:
- "What is my property tax bill?"
- "Show my property taxes"
- "Is my tax paid?"
- "When is my next payment due?"

### Environment Variables

- `MCP_API_KEY`: API key for authentication (required)
- `MY_APN`: Your default Assessor's Parcel Number (optional)
  - Enables natural language queries like "what is my property tax bill?"
  - Used automatically by `get_my_property_info` tool
  - Used as fallback by `get_property_info` when no APN provided
- `PORT`: Server port (default: 3000)
- `USE_SCRAPER`: Enable/disable live scraping (default: "true")
  - Set to "false" to use only mock data

### Mock Data

The server includes mock data for the following APN for testing:
- **288-13-033**: 1373 Cronwell Dr, Campbell, CA 95008

## Scraper Implementation Status

### Current Status

✅ **Infrastructure Complete:**
- Playwright scraper module with caching
- Server integration with fallback support
- Docker configuration with Playwright dependencies
- Health endpoint with scraper status

⚠️ **Extraction Logic Pending:**
The `_extract_property_data()` function in `scraper.py` needs to be implemented with actual HTML parsing logic. Currently it returns placeholder data.

### To Complete Scraper

1. **Inspect TellerOnline HTML Structure:**
   ```bash
   # Run Playwright in non-headless mode to inspect page
   playwright codegen https://santaclaracounty.telleronline.net/search/1
   ```

2. **Update `scraper.py:_extract_property_data()`:**
   - Locate HTML elements containing property data
   - Extract: address, tax amounts, installment info, payment status
   - Handle various page states (found/not found, paid/unpaid, etc.)

3. **Test with Real Data:**
   ```bash
   # Test scraper directly
   python -c "import asyncio; from scraper import scrape_property_tax; print(asyncio.run(scrape_property_tax('288-13-033')))"
   ```

## Docker Deployment

### Build

```bash
docker build -t mcp-santa-clara .
```

### Run

```bash
docker run -d \
  -p 3002:3000 \
  -e MCP_API_KEY=your-api-key-here \
  -e MY_APN=288-13-033 \
  -e USE_SCRAPER=true \
  --name mcp-santa-clara \
  mcp-santa-clara
```

### Health Check

```bash
curl http://localhost:3002/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "santa-clara",
  "api_key_configured": true,
  "scraper_available": true,
  "scraper_enabled": true,
  "my_apn_configured": true,
  "my_apn": "288-13-033",
  "cache_stats": {
    "total_entries": 0,
    "valid_entries": 0,
    "expired_entries": 0,
    "cache_ttl_hours": 24
  }
}
```

## Development

### Local Testing

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Run server:**
   ```bash
   export MCP_API_KEY=test-key
   export MY_APN=288-13-033
   python server.py
   ```

3. **Test endpoint:**
   ```bash
   curl -X POST http://localhost:3000/messages \
     -H "Authorization: Bearer test-key" \
     -H "Content-Type: application/json" \
     -d '{"method":"tools/call","params":{"name":"get_property_info","arguments":{"apn":"288-13-033"}},"jsonrpc":"2.0","id":1}'
   ```

### Debugging Scraper

Enable debug logging to see scraper activity:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Cache Management

Clear cache programmatically:

```python
from scraper import clear_cache
clear_cache()
```

## Troubleshooting

### Scraper Not Available

**Symptom:** Health endpoint shows `scraper_available: false`

**Causes:**
- Playwright not installed
- `scraper.py` import failed
- Missing system dependencies

**Fix:**
```bash
pip install playwright
playwright install chromium
```

### Scraper Timeout

**Symptom:** Requests timeout or take >30 seconds

**Causes:**
- TellerOnline website slow/down
- Network issues
- Chromium not installed properly

**Fix:**
- Check TellerOnline website is accessible
- Increase timeout in `scraper.py`
- Disable scraper temporarily: `USE_SCRAPER=false`

### APN Not Found

**Symptom:** "APN not found" error

**Causes:**
- Invalid APN format
- Property doesn't exist in Santa Clara County
- Scraper extraction logic not finding data

**Fix:**
- Verify APN format (XXX-XX-XXX)
- Check property exists on TellerOnline website manually
- Debug extraction logic in `_extract_property_data()`

## Rate Limiting

The scraper implements caching to minimize requests to TellerOnline:

- **Cache TTL**: 24 hours
- **Cache Storage**: In-memory (resets on container restart)
- **Recommendation**: Don't query same APN more than once per day

## Legal & Ethics

⚠️ **Important Notices:**

1. **Public Data**: Property tax information is public record
2. **Terms of Service**: Respect TellerOnline's terms of service
3. **Rate Limiting**: Cache aggressively to minimize server load
4. **No Warranty**: This is a demonstration project

## Future Enhancements

Potential improvements:

- [ ] Persistent cache (Redis/database)
- [ ] Retry logic with exponential backoff
- [ ] Support for multiple counties
- [ ] Historical data tracking
- [ ] Email notifications for payment due dates
- [ ] Batch APN lookups

## Support

For issues or questions:
- Check server logs: `docker logs mcp-santa-clara`
- Review health endpoint: `curl http://localhost:3002/health`
- See deployment guide: `/mcp-dev-environment/DEPLOYMENT.md`
