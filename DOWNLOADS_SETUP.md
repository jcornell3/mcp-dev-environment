# YouTube to MP3 Downloads Setup

## Current Configuration

The YouTube to MP3 service downloads files to a **WSL-native directory** to ensure reliable Docker volume mounting:

- **WSL Path:** `/home/jcornell/downloads`
- **Container Path:** `/downloads`
- **Docker Volume:** `/home/jcornell/downloads:/downloads`

This approach avoids WSL/Windows path translation issues that can cause files to not appear when using `/mnt/c/` paths.

## Accessing Downloads from Windows

You have three options to access downloaded MP3 files from Windows:

### Option 1: Access via Windows Explorer (Recommended)

Open Windows Explorer and navigate to:

```
\\wsl$\Ubuntu\home\jcornell\downloads
```

Or type this in the Windows Explorer address bar:
```
\\wsl.localhost\Ubuntu\home\jcornell\downloads
```

**Tip:** Bookmark this location in Windows Explorer for quick access!

### Option 2: Create Windows Shortcut

1. Open Windows Explorer
2. Navigate to: `\\wsl$\Ubuntu\home\jcornell\downloads`
3. Right-click in the address bar → "Copy address"
4. Right-click on your Desktop → New → Shortcut
5. Paste the address: `\\wsl$\Ubuntu\home\jcornell\downloads`
6. Name it "MCP Downloads" or similar

### Option 3: Create Symbolic Link (Advanced)

**WARNING:** This requires Administrator privileges and will replace your existing Downloads folder with a link.

**Only do this if you want ALL downloads to go to the WSL location.**

1. Open Command Prompt or PowerShell **as Administrator**

2. Backup your current Downloads folder (if needed):
   ```cmd
   move C:\Users\jcorn\Downloads C:\Users\jcorn\Downloads.backup
   ```

3. Create a symbolic link:
   ```cmd
   mklink /D C:\Users\jcorn\Downloads \\wsl$\Ubuntu\home\jcornell\downloads
   ```

4. Verify:
   ```cmd
   dir C:\Users\jcorn\Downloads
   ```

**To Undo:**
```cmd
rmdir C:\Users\jcorn\Downloads
move C:\Users\jcorn\Downloads.backup C:\Users\jcorn\Downloads
```

## Verification

To verify the setup is working:

1. Run this command in WSL:
   ```bash
   docker exec mcp-youtube-to-mp3 sh -c 'echo "test" > /downloads/test-$(date +%s).txt'
   ```

2. Check that the file appears:
   - **In WSL:** `ls -lh /home/jcornell/downloads/`
   - **In Windows:** Open `\\wsl$\Ubuntu\home\jcornell\downloads` in Explorer

## Troubleshooting

### Files not appearing in Windows Explorer

1. Refresh Windows Explorer (F5)
2. Verify WSL is running: `wsl --list --running`
3. Check file exists in WSL: `ls -lh /home/jcornell/downloads/`
4. Try accessing via: `\\wsl.localhost\Ubuntu\home\jcornell\downloads` (alternative path)

### Cannot access `\\wsl$` path

- Ensure WSL is running: `wsl --list --running`
- Try the alternative: `\\wsl.localhost\Ubuntu\home\jcornell\downloads`
- Restart WSL: `wsl --shutdown` then `wsl`

### Permission issues

If you get permission errors accessing files from Windows:

```bash
# In WSL, make files world-readable
chmod 644 /home/jcornell/downloads/*
```

## Why This Approach?

The previous configuration used `/mnt/c/Users/jcorn/Downloads` which maps to the Windows filesystem. However, Docker containers running in WSL have issues writing to `/mnt/c/` paths due to:

1. File system translation layers
2. Permission mapping differences
3. Windows file locking behavior

Using a WSL-native path (`/home/jcornell/downloads`) ensures:
- ✅ Reliable file writes from Docker containers
- ✅ No permission issues
- ✅ Better performance (native filesystem)
- ✅ Files still accessible from Windows via `\\wsl$`
