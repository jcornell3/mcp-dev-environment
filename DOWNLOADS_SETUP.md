# YouTube to MP3 Downloads Setup

## Current Configuration

The YouTube to MP3 service uses a **symbolic link** approach to write files directly to your Windows Downloads folder while maintaining Docker volume compatibility.

- **WSL Symbolic Link:** `/home/jcornell/downloads` → `/mnt/c/Users/jcorn/Downloads`
- **Container Path:** `/downloads`
- **Docker Volume:** `/home/jcornell/downloads:/downloads` (which resolves to Windows Downloads)
- **Windows Path:** `C:\Users\jcorn\Downloads`

## How It Works

1. A symbolic link is created in WSL that points to your Windows Downloads folder
2. Docker mounts this symbolic link as a volume
3. When the container writes to `/downloads`, it follows the symbolic link
4. Files appear directly in your Windows Downloads folder (`C:\Users\jcorn\Downloads`)

## Initial Setup

When setting up this project on a new machine:

```bash
# Replace YOUR_USERNAME with your Windows username
ln -s /mnt/c/Users/YOUR_USERNAME/Downloads ~/downloads
```

**To find your Windows username:**
```bash
ls /mnt/c/Users/
```

## Verification

To verify the setup is working:

1. **Check the symbolic link exists:**
   ```bash
   ls -la ~/downloads
   ```

   Should show: `downloads -> /mnt/c/Users/YOUR_USERNAME/Downloads`

2. **Test file creation:**
   ```bash
   docker exec mcp-youtube-to-mp3 sh -c 'echo "test" > /downloads/test-$(date +%s).txt'
   ```

3. **Check Windows Downloads folder:**
   - Open Windows File Explorer
   - Navigate to your Downloads folder
   - The test file should appear there immediately

4. **Clean up test file:**
   ```bash
   rm ~/downloads/test-*.txt
   ```

## Accessing Downloads

Downloads appear directly in your Windows Downloads folder:
- **Windows:** `C:\Users\YOUR_USERNAME\Downloads`
- **WSL:** `/home/jcornell/downloads` (via symbolic link)
- **WSL (direct):** `/mnt/c/Users/YOUR_USERNAME/Downloads`

No special access needed - just use your normal Windows Downloads folder!

## Troubleshooting

### Symbolic link doesn't exist

If `~/downloads` doesn't exist or isn't a symbolic link:

```bash
# Remove if it's a regular directory
rm -rf ~/downloads  # WARNING: Only if it's empty!

# Create the symbolic link
ln -s /mnt/c/Users/YOUR_USERNAME/Downloads ~/downloads
```

### Files not appearing in Windows Downloads

1. **Verify symbolic link:**
   ```bash
   ls -la ~/downloads
   ```
   Should show it's a link to `/mnt/c/Users/YOUR_USERNAME/Downloads`

2. **Check Windows path is accessible:**
   ```bash
   ls /mnt/c/Users/YOUR_USERNAME/Downloads
   ```

3. **Restart Docker containers:**
   ```bash
   export MCP_API_KEY=your_api_key_here
   docker compose down
   docker compose up -d
   ```

### Permission issues

If you get permission errors:

```bash
# Make the Windows Downloads folder accessible
chmod 755 /mnt/c/Users/YOUR_USERNAME/Downloads
```

### Docker can't write to the volume

This usually means the symbolic link was created after the container started:

```bash
# Recreate containers
export MCP_API_KEY=your_api_key_here
docker compose down
docker compose up -d
```

## Why This Approach?

**Symbolic Link Method (Current):**
- ✅ Files appear in Windows Downloads folder
- ✅ Docker volume compatibility
- ✅ Easy to access from Windows
- ✅ One command setup on new machines
- ✅ No need to remember special paths

**Previous Approach (WSL-only directory):**
- ❌ Required special `\\wsl$` path to access from Windows
- ❌ Files not in standard Downloads folder
- ❌ Extra steps for Windows access

**Direct `/mnt/c` Mount (Doesn't work):**
- ❌ Docker volume mount failures
- ❌ Permission issues
- ❌ Files reported as saved but don't appear

The symbolic link combines the best of both worlds: Docker gets a WSL-native path it can reliably write to, and the files appear in your normal Windows Downloads folder.
