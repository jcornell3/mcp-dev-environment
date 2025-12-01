# MCP Development Environment Setup - Fresh Windows Workstation
## Claude-Driven Development Approach

This guide starts from a completely fresh Windows machine and sets up a professional MCP development environment where Claude/Claude Code does most of the work.

---

## Philosophy: Let Claude Build It

**Human does:** Minimal manual installation (only what Claude can't do)  
**Claude does:** Build configs, write code, troubleshoot errors, test endpoints  

---

## Phase 1: Essential Manual Installations (30 minutes)

These are prerequisites that Claude needs to be able to help you.

### Step 1: Install Windows Package Manager (winget)

**Check if already installed:**
```powershell
winget --version
```

**If not installed:**
- Windows 11: Already included
- Windows 10: Install from Microsoft Store - search "App Installer"

---

### Step 2: Install WSL2 (Windows Subsystem for Linux)

**Open PowerShell as Administrator** and run:

```powershell
# Install WSL2 with Ubuntu
wsl --install -d Ubuntu

# This will:
# - Enable WSL feature (if not already enabled)
# - Download Ubuntu (2-5 minutes)
# - Install Ubuntu
# - Launch Ubuntu automatically
```

**What to expect:**
```
Downloading: Ubuntu
Installing: Ubuntu
Distribution successfully installed. It can be launched via 'wsl.exe -d Ubuntu'
Launching Ubuntu...
Provisioning the new WSL instance Ubuntu
This might take a while...
```

**Ubuntu First-Time Setup:**
1. You'll be prompted: `Create a default Unix user account:`
2. **Enter username** (e.g., `jcornell`) - use lowercase, no spaces
3. **Enter password** (you won't see characters as you type - this is normal)
4. **Retype password** to confirm
5. You'll see: `passwd: password updated successfully`

**⚠️ Important:** Remember your username and password! You'll need them for `sudo` commands.

**After setup completes:**
- Your PowerShell prompt will change to: `username@MACHINE-NAME:/mnt/c/Windows/system32$`
- This means you're now inside Ubuntu (WSL)

**Exit back to PowerShell:**
```bash
exit
```

**Verify installation (from PowerShell):**
```powershell
# Check WSL version
wsl --status

# List installed distributions
wsl -l -v
```

**Expected output:**
```
  NAME      STATE           VERSION
* Ubuntu    Running         2
```

**Test Ubuntu is WSL 2:**
```powershell
# Enter WSL
wsl

# Check kernel version (should contain "microsoft")
uname -r

# Check Ubuntu version
lsb_release -a

# Exit back to PowerShell
exit
```

✅ **You should see:**
- Kernel: `6.6.x.x-microsoft-standard-WSL2` (confirms WSL 2)
- Ubuntu: `24.04` or similar

---

### Troubleshooting WSL Installation

**Issue: "WSL1 is not supported with your current machine configuration"**

This means WSL2 features aren't enabled. Run these commands:

```powershell
# Enable WSL feature
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# Enable Virtual Machine Platform
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Restart Windows (REQUIRED)
shutdown /r /t 0
```

**After restart:**
```powershell
# Set WSL 2 as default
wsl --set-default-version 2

# Install Ubuntu
wsl --install -d Ubuntu
```

---

**Issue: "Windows Subsystem for Linux has no installed distributions"**

Run:
```powershell
wsl --install -d Ubuntu
```

This specifically installs Ubuntu (the `-d Ubuntu` is important).

---

**Issue: Can't find `wsl` command**

- Ensure you're running Windows 10 version 2004+ or Windows 11
- Check version: Press `Win+R`, type `winver`, press Enter
- If version is too old, update Windows

---

---

### Step 3: Install Docker Desktop

**Install using winget:**
```powershell
winget install Docker.DockerDesktop
```

**Manual download alternative:**
- Go to: https://www.docker.com/products/docker-desktop/
- Download for Windows
- Run installer
- **Important:** During install, ensure "Use WSL 2 instead of Hyper-V" is checked

---

### **First Launch: Run as Administrator**

⚠️ **Important:** Docker Desktop must be run as administrator the first time.

**After installation completes:**

1. **Close any Docker Desktop windows if opened**
2. Press **Windows key**
3. Type **"Docker Desktop"**
4. **Right-click** on "Docker Desktop"
5. Select **"Run as administrator"**
6. Click **"Yes"** at UAC prompt

**What happens:**
- Docker Desktop starts (may take 2-3 minutes first time)
- You'll see initialization messages in the UI

---

### **Accept Docker Subscription Agreement**

1. When Docker starts, you'll see the **Docker Subscription Service Agreement**
2. Read it (or scroll to bottom)
3. Click **"Accept"**

---

### **Skip Welcome Screen**

1. You'll see **"Welcome to Docker"** with email signup
2. Click **"Skip"** in the top-right corner
   - You don't need a Docker Hub account for local development
   - Can always create one later if needed

---

### **Configure WSL Integration (CRITICAL)**

Docker needs to connect to your Ubuntu installation:

1. Click the **⚙️ Settings** icon (top-right of Docker Desktop)
2. Go to **"Resources"** → **"WSL Integration"**
3. Ensure **"Enable integration with my default WSL distro"** is ✅ checked
4. Under **"Enable integration with additional distros:"**
   - Find **"Ubuntu"** in the list
   - Toggle the slider **ON** (to the right, turns blue)
5. Click **"Apply & Restart"**

**Wait 2-3 minutes** for Docker to restart.

---

### **Verify Docker Installation**

After Docker restarts, test in both PowerShell and WSL:

**In PowerShell:**
```powershell
# Check versions
docker --version
docker-compose --version

# Test Docker is running
docker ps
```

**Expected output:**
```
Docker version 29.0.1, build edd969
Docker Compose version v2.40.3-desktop.1
CONTAINER ID   IMAGE   COMMAND   CREATED   STATUS   PORTS   NAMES
```

**In WSL:**
```powershell
# Enter WSL
wsl

# Test Docker in WSL
docker --version
docker ps

# Exit
exit
```

**You should see the same Docker version in both.**

✅ **Docker is now installed and integrated with WSL!**

---

### **Troubleshooting Docker Desktop**

**Issue: "Access is denied" errors on startup**

**Solution:** Run as administrator (see above)

---

**Issue: Docker Desktop won't start or shows errors**

**Solution 1 - Reset to factory defaults:**
1. Right-click Docker Desktop system tray icon
2. Select **"Troubleshoot"**
3. Click **"Reset to factory defaults"**
4. Confirm reset
5. Wait for reset to complete
6. Run Docker Desktop as administrator
7. Reconfigure WSL integration

**Solution 2 - Check virtualization:**
```powershell
systeminfo
```

Look for:
```
Hyper-V Requirements:      VM Monitor Mode Extensions: Yes
                           Virtualization Enabled In Firmware: Yes
```

If "No", you need to:
1. Restart computer
2. Enter BIOS (F2, F10, or Del during boot)
3. Enable "Virtualization" or "Intel VT-x" or "AMD-V"
4. Save and exit

---

**Issue: "Docker Desktop is starting..." never finishes**

**Solution:**
1. Open Task Manager (Ctrl+Shift+Esc)
2. End all "Docker" processes
3. Close Docker Desktop completely
4. Run Docker Desktop as administrator again
5. Wait 5 minutes for first startup

---

**Issue: WSL integration toggle not available**

**Solution:**
1. Verify WSL is running: `wsl -l -v`
2. Ensure Ubuntu shows "VERSION 2" (not 1)
3. If version 1, convert: `wsl --set-version Ubuntu 2`
4. Restart Docker Desktop

---

### Step 4: Install Claude Desktop

**Using winget:**
```powershell
winget install Anthropic.Claude
```

**Manual download alternative:**
- Go to: https://claude.ai/download
- Download Windows installer
- Run installer

**After installation:**
- Launch Claude Desktop
- Sign in with your Anthropic account

---

### Step 5: Install VS Code (for Claude Code)

⚠️ **Important:** Run PowerShell as Administrator for this installation.

**Using winget:**
```powershell
# In PowerShell as Administrator
winget install Microsoft.VisualStudioCode
```

**If you get an error about administrator rights:**
1. Close PowerShell
2. Press **Windows key**
3. Type **"PowerShell"**
4. **Right-click** "Windows PowerShell"
5. Select **"Run as administrator"**
6. Run the winget command again

**Manual download alternative:**
- Go to: https://code.visualstudio.com/
- Download for Windows
- Run installer

---

### **Install Required Extensions**

**After VS Code is installed:**

1. **Launch VS Code**
2. Click the **Extensions** icon (or press `Ctrl+Shift+X`)
3. Search and install these extensions:

**Required Extensions:**

1. **WSL** (by Microsoft)
   - **NOT "Remote - WSL"** - the extension is simply called **"WSL"**
   - Allows VS Code to connect to your Ubuntu environment
   - Look for the penguin icon

2. **Docker** (by Microsoft)
   - Manage Docker containers from VS Code
   - Look for the whale icon

3. **Python** (by Microsoft)
   - Python language support
   - Look for the blue/yellow snake icon

**How to install each:**
1. Search for extension name
2. Click on the correct extension (verify it's by Microsoft)
3. Click **"Install"** button
4. Wait for installation to complete

---

### **Connect VS Code to WSL**

Once extensions are installed:

1. Press **F1** (or `Ctrl+Shift+P`)
2. Type: **"WSL: Connect to WSL"**
3. Select it from the dropdown
4. Or just type **"WSL"** and select **"WSL: Connect to WSL"**

**What happens:**
- A new VS Code window opens
- Bottom-left corner shows: **"WSL: Ubuntu"** in green
- You're now connected to your Ubuntu environment

**Verify WSL connection:**
1. Press `` Ctrl+` `` (backtick) to open terminal
2. You should see a Linux bash prompt: `username@MACHINE-NAME:~$`
3. Try: `pwd` - should show `/home/jcornell` or your username

✅ **VS Code is now set up with WSL integration!**

---

### **Troubleshooting VS Code**

**Issue: Can't find "WSL" extension, only see "Remote - WSL"**

**Solution:** The extension may be called "WSL" or "Remote - WSL" depending on your region/VS Code version. Install whichever one you see from Microsoft. They're the same extension.

---

**Issue: "WSL: Connect to WSL" doesn't work**

**Solution:**
1. Ensure WSL is running: `wsl -l -v` in PowerShell
2. Restart VS Code
3. Try opening a WSL terminal first: `wsl` in PowerShell
4. Then launch VS Code from WSL: `code .`

---

**Issue: Terminal in VS Code shows PowerShell, not bash**

**Solution:**
1. You're in Windows VS Code, not WSL VS Code
2. Press F1 → "WSL: Connect to WSL"
3. Or close VS Code and run from WSL: `code .`

---

### Step 6: Install Git

**In WSL terminal:**
```bash
sudo apt update
sudo apt install -y git
git --version
```

**Configure Git:**
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

✅ **Git is now installed and configured!**

---

### Step 6b: Set Up GitHub Authentication (SSH)

To push code to GitHub from WSL, you need to set up SSH keys.

**Why SSH:**
- ✅ No password prompts when pushing
- ✅ More secure than HTTPS
- ✅ Works seamlessly with Copilot
- ✅ Industry standard

---

#### **Generate SSH Key**

```bash
# Generate SSH key (use your GitHub email)
ssh-keygen -t ed25519 -C "your.email@example.com"
```

**When prompted:**
- **"Enter file to save the key"** → Press **Enter** (default location)
- **"Enter passphrase"** → Press **Enter** (no passphrase) or enter one for extra security
- **"Enter same passphrase again"** → Press **Enter** or repeat passphrase

**You'll see:**
```
Your identification has been saved in /home/username/.ssh/id_ed25519
Your public key has been saved in /home/username/.ssh/id_ed25519.pub
```

---

#### **Start SSH Agent and Add Key**

```bash
# Start SSH agent
eval "$(ssh-agent -s)"

# Add your SSH key
ssh-add ~/.ssh/id_ed25519
```

**Expected:** `Identity added: /home/username/.ssh/id_ed25519`

---

#### **Copy Public Key**

```bash
# Display your public key
cat ~/.ssh/id_ed25519.pub
```

**Copy the entire output** (starts with `ssh-ed25519 AAAA...` and ends with your email)

---

#### **Add SSH Key to GitHub**

**In your web browser:**
1. Go to **https://github.com/settings/keys**
2. Click **"New SSH key"** (green button)
3. **Title:** `WSL Ubuntu on [Your PC Name]` (e.g., "WSL Ubuntu on MyPC")
4. **Key type:** `Authentication Key`  
5. **Key:** Paste the public key you copied
6. Click **"Add SSH key"**
7. **Confirm** with your GitHub password if prompted

✅ **SSH key added to GitHub!**

---

#### **Test SSH Connection**

```bash
# Test GitHub SSH connection
ssh -T git@github.com
```

**First time:** Type `yes` when asked about authenticity

**Expected success:**
```
Hi YOUR_USERNAME! You've successfully authenticated, but GitHub does not provide shell access.
```

✅ **GitHub SSH authentication is working!**

---

#### **Make SSH Persistent (Optional but Recommended)**

Add this to your `~/.bashrc` so SSH agent starts automatically:

```bash
# Add SSH agent auto-start to bashrc
cat >> ~/.bashrc << 'EOF'

# Start SSH agent and add key automatically
if [ -z "$SSH_AUTH_SOCK" ]; then
  eval "$(ssh-agent -s)" > /dev/null
  ssh-add ~/.ssh/id_ed25519 2>/dev/null
fi
EOF

# Reload bashrc
source ~/.bashrc
```

---

#### **Troubleshooting SSH**

**Issue: "Permission denied (publickey)"**
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
ssh-add -l  # Verify key is loaded
```

**Issue: "Could not open a connection to your authentication agent"**
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

---

✅ **GitHub authentication complete! You can now push/pull without passwords.**

---

## Phase 1 Complete! ✅

**What you have:**
- ✅ WSL2 with Ubuntu 24.04
- ✅ Docker Desktop with WSL integration
- ✅ Claude Desktop
- ✅ VS Code with extensions
- ✅ Git configured
- ✅ GitHub SSH authentication

**Ready for Phase 2:** Let Claude/Copilot build your development environment!

---

## Phase 2: Automated Environment Setup with GitHub Copilot (10-15 minutes)

Now that prerequisites are installed, we'll use **GitHub Copilot** in VS Code to automatically build the entire MCP development environment.

### **What is GitHub Copilot?**

**GitHub Copilot** is an AI coding assistant that:
- ✅ Executes commands directly in your WSL terminal
- ✅ Creates and edits files automatically
- ✅ Does the work while you supervise
- ✅ Iterates and fixes errors automatically

**Important Notes:**
- ⚠️ Long-running commands may cause terminal sessions to drop - this is normal
- ✅ Copilot adapts by saving outputs to files instead of streaming
- ✅ The process may take multiple iterations - let Copilot continue working
- ⏱️ Expect 10-15 minutes total (including troubleshooting)

---

### **Step 7: Sign in to GitHub Copilot**

When you click "CHAT" in VS Code, you'll see a sign-in screen.

**Sign in:**
1. Click **"Continue with GitHub"** (recommended)
2. **Sign in** to your GitHub account (create free account if needed)
3. **Authorize GitHub Copilot** when prompted
4. **Return to VS Code**

✅ **You're now signed in to GitHub Copilot**

---

### **Step 7b: Enable Claude Models (When Prompted)**

**During setup, Copilot may ask to enable Claude Haiku 4.5:**

**What you'll see:**
```
Sorry, your request failed.
Reason: The requested model is not supported.

Enable Claude Haiku 4.5 for all clients?
[Enable button]
```

**What to do:**
- ✅ Click **"Enable"**
- ✅ This is a one-time authorization
- ✅ Gives Copilot access to better models
- ✅ Completely safe and recommended

**After enabling:**
- Click **"Try Again"** to retry the failed request
- Copilot will continue where it left off

---

### **Step 8: Give Copilot the Complete Setup Prompt**

**Important:** Use this exact prompt for best results:

```
I need you to build a complete MCP development environment in ~/mcp-dev-environment with these requirements:

CRITICAL INSTRUCTIONS:
- If terminal sessions drop, save outputs to files in logs/diagnostics/ instead of streaming
- Use shorter commands when possible to avoid timeouts
- Create actual working MCP server code, not just placeholders

SETUP TASKS:

1. Create directory structure:
   - nginx/conf.d
   - servers/santa-clara/tests  
   - servers/shared
   - certs
   - logs/nginx
   - data/fixtures
   - scripts

2. Install system dependencies:
   - Python 3 and pip
   - Node.js 20.x
   - mkcert (for SSL certificates)
   - jq, tree, curl, wget
   - libnss3-tools

3. Generate SSL certificates:
   - Install local CA with mkcert
   - Generate certificates: mkcert -cert-file certs/localhost.pem -key-file certs/localhost-key.pem localhost 127.0.0.1 ::1
   - IMPORTANT: Use -cert-file and -key-file flags to name files correctly

4. Create docker-compose.yml:
   - DON'T include "version" attribute (it's obsolete)
   - Nginx reverse proxy on port 8443 (not 443)
   - Santa Clara MCP server container
   - Proper networking and volumes
   - Health checks

5. Create Makefile with commands:
   - make start, stop, restart, logs, test, health, clean

6. Create Nginx configuration:
   - nginx/Dockerfile (FROM nginx:alpine, install wget)
   - nginx/nginx.conf (main config)
   - nginx/conf.d/mcp-servers.conf (routing config)
   - Listen on port 443 inside container (mapped to 8443 on host)

7. Create working MCP server:
   - servers/santa-clara/server.py (Flask app with /mcp endpoint and /health endpoint)
   - servers/santa-clara/Dockerfile (Python with Flask)
   - servers/santa-clara/requirements.txt (flask, flask-cors)
   - Implement basic MCP protocol: tools/list returns example tools

8. Create additional files:
   - .env, .gitignore
   - scripts/test-endpoints.sh
   - SETUP_COMPLETE.md with usage instructions

EXECUTION STRATEGY:
- If commands fail, save diagnostics to logs/diagnostics/
- Parse error logs and apply fixes iteratively
- Don't give up if terminal drops - continue with file-based approach
- Build and test containers at the end

Execute all steps automatically. Show progress and handle errors.
```

---

### **Step 9: Supervise and Guide Copilot**

**What to expect:**
1. ⏳ Copilot executes commands (you'll see progress)
2. ⚠️ Terminal may close unexpectedly - **this is normal**
3. 📁 Copilot saves diagnostics to `logs/diagnostics/` when sessions drop
4. 🔄 Copilot iterates through fixes automatically
5. ✅ Eventually reports success

**Your role:**
- Watch progress updates
- When Copilot asks for decisions:
  - **"Should I proceed?"** → Answer: **"Yes, proceed"**
  - **"Which option?"** → Choose the **file-based option** (avoids terminal drops)
  - **"Keep or undo changes?"** → Answer: **"Keep"**

**Common scenarios:**

**Scenario 1: Terminal session drops**
- ✅ **Normal** - long commands cause this
- ✅ Copilot will adapt and save to files instead
- ✅ Just let it continue

**Scenario 2: Copilot asks about diagnostics**
- ✅ Choose **Option B** (short output to reduce drops)
- ✅ Or let Copilot save to files and read them

**Scenario 3: Certificate naming issues**
- ✅ Copilot should use `-cert-file` and `-key-file` flags (prompt specifies this)
- ✅ If not, tell Copilot: "Rename localhost+2.pem to localhost.pem"

---

### **Step 10: Verify Everything Works**

After Copilot completes, verify the setup:

**Check containers are running:**
```bash
cd ~/mcp-dev-environment
docker compose ps
```

**Expected output:**
```
NAME                            STATUS
mcp-dev-environment-nginx-1     Up
mcp-dev-environment-santa-clara-1   Up
```

**Test endpoints:**
```bash
# Test root endpoint
curl -k https://localhost:8443/

# Test health endpoint  
curl -k https://localhost:8443/health
```

**Expected responses:**
- Root: `{"service":"santa-clara","status":"running"}`
- Health: `{"status":"ok"}`

✅ **If you see these responses, everything is working!**

---

### **Step 11: Review Setup Documentation**

Copilot created `~/mcp-dev-environment/SETUP_COMPLETE.md` with:
- ✅ What was built
- ✅ Services running and ports
- ✅ Management commands (make start/stop/logs)
- ✅ How to test endpoints
- ✅ Claude Desktop configuration

**Read this file:**
```bash
cat ~/mcp-dev-environment/SETUP_COMPLETE.md
```

---

## Troubleshooting Common Issues

### **Issue: Copilot stops after each task**

**Solution:** Tell Copilot:
```
Please continue automatically without asking for confirmation after each step. Proceed until all tasks are complete.
```

---

### **Issue: Terminal command hangs with no output**

**Symptoms:**
- Command runs but shows no output
- Cursor just sits there
- Nothing happens for 30+ seconds

**Solution:**
1. Press `Ctrl+C` to cancel
2. Add `--verbose` flag to the command
3. Retry

**Example:**
```bash
# Instead of:
git push -u origin main

# Use:
git push -u origin main --verbose
```

**Common commands that benefit from --verbose:**
- `git push --verbose`
- `docker-compose up --verbose`
- `make start VERBOSE=1`

---

### **Issue: Terminal process terminated unexpectedly**

**Symptoms:**
- Red error: "The terminal process '/bin/bash' terminated with exit code 1/2/130"
- Command was running but stopped

**This is normal!** The terminal session dropped due to long-running command.

**Solution:**
1. **Check if it actually worked:** Run status check commands
2. **If it didn't work:** Just retry the command
3. **Continue:** This doesn't break anything

**Example:**
```bash
# Terminal crashed during: docker-compose up -d

# Check if it worked:
docker-compose ps

# If containers aren't running, just retry:
docker-compose up -d
```

---

### **Issue: Containers fail to start**

**Solution:** Tell Copilot:
```
Containers failed to start. Please:
1. Show me docker compose logs
2. Identify the specific errors
3. Fix the issues
4. Rebuild: docker compose down --remove-orphans && docker compose up -d --build
5. Verify services are healthy

Continue until working.
```

---

### **Issue: Certificate errors in nginx logs**

**Solution:** Tell Copilot:
```
Nginx can't find certificate files. Please:
1. Check what certificate files exist in certs/
2. Ensure they're named localhost.pem and localhost-key.pem
3. Update nginx config if needed
4. Rebuild nginx container
```

---

### **Issue: Port 8443 already in use**

**Solution:** Tell Copilot:
```
Port 8443 is already in use. Please:
1. Change docker-compose.yml to use port 8444 instead
2. Update test scripts and documentation
3. Rebuild and restart containers
```

---

### **Issue: MCP server returns 404**

**Solution:** Check that `servers/santa-clara/server.py` actually exists and implements:
```python
@app.route('/mcp', methods=['POST'])
@app.route('/health', methods=['GET'])
```

Tell Copilot to create the actual server code if it's missing.

---

## Tips for Success

### **✅ DO:**
- Let Copilot work through multiple iterations
- Choose file-based options when terminal drops
- Be patient - full setup takes 10-15 minutes
- Keep responding "yes, proceed" to keep Copilot going

### **❌ DON'T:**
- Interrupt Copilot mid-task
- Panic when terminal sessions close (it's normal)
- Manually edit files while Copilot is working
- Give up after first error - let Copilot iterate

---

## Phase 2 Success Criteria

You'll know Phase 2 is complete when:

✅ All directories exist in `~/mcp-dev-environment`  
✅ SSL certificates generated (localhost.pem, localhost-key.pem)  
✅ Docker containers built and running  
✅ `docker compose ps` shows both services "Up"  
✅ `curl -k https://localhost:8443/health` returns `{"status":"ok"}`  
✅ SETUP_COMPLETE.md exists with instructions  
✅ No errors in `docker compose logs`  

---

## Estimated Time

**Phase 1 (Prerequisites):** 30-45 minutes
- WSL installation: 10-15 minutes
- Docker Desktop: 10-15 minutes  
- VS Code + extensions: 5-10 minutes
- Git + GitHub SSH: 10-15 minutes

**Phase 2 (Environment Setup):** 15-25 minutes
- Ideal case: 10-15 minutes (if everything works first try)
- Realistic case: 15-20 minutes (with 1-2 iterations)
- Complex case: 20-25 minutes (with multiple fixes needed)

**Phase 2b (Git Push):** 5-10 minutes
- Create GitHub repo: 2 minutes
- Push to GitHub: 3-5 minutes
- Troubleshooting (if needed): 5 minutes

**Total Time: 50-80 minutes** for complete setup from fresh Windows machine to working MCP environment in GitHub.

**Most common:** 60-70 minutes with normal troubleshooting.

---

## Phase 2 Complete! ✅

**You'll know Phase 2 is complete when:**

✅ All directories exist in `~/mcp-dev-environment`  
✅ All configuration files created  
✅ SSL certificates generated  
✅ Docker containers built successfully  
✅ Services running: `docker-compose ps` shows "Up"  
✅ Endpoints accessible: `curl https://localhost:8443/`  
✅ MCP server responds to requests  

---

## Advantages of This Approach

**Compared to manual setup:**
- ⚡ **10x faster** - Copilot does everything in minutes
- 🎯 **Fewer errors** - Copilot knows correct syntax
- 🔄 **Auto-fixing** - Copilot detects and fixes issues
- 📚 **Learning** - You see commands being executed
- 🤖 **Iterative** - Copilot retries until it works

**Compared to copy/paste:**
- No manual copying
- No typos
- No missed steps
- Copilot handles errors automatically

---

## Alternative: Claude Desktop (Manual Method)

**If you don't want to use GitHub Copilot:**

You can use Claude Desktop (the app you're in now) to get copy/paste command blocks instead:

**Ask Claude Desktop:**
```
I don't have GitHub Copilot. Please provide command blocks I can copy/paste to build my MCP development environment in WSL.
```

Claude Desktop will provide complete bash blocks that you copy and paste into your terminal. Still fast, just more manual.

---

## Phase 2c: Push to GitHub (10 minutes)

Once your environment is working, push everything to GitHub for backup and version control.

### **Why Push to GitHub:**

✅ **Backup** - Your work is safe in the cloud  
✅ **Version control** - Full history preserved  
✅ **Portability** - Easy to clone on other machines  
✅ **Collaboration** - Can share or get help  

---

### **Step 13: Tell Copilot to Push**

**After verifying services work, tell Copilot:**

```
My environment is working! Now please push this to GitHub:

1. Create a new repository on GitHub named "mcp-dev-environment" (private)
2. Add the remote using my SSH: git@github.com:MY_USERNAME/mcp-dev-environment.git
3. Push all commits

If you can use gh CLI, do it automatically. Otherwise give me manual steps.
```

---

### **Step 14: Verify GitHub Username**

**IMPORTANT:** Copilot may guess your GitHub username incorrectly.

**Check the remote it added:**
```bash
git remote -v
```

**You'll see:**
```
origin  git@github.com:GUESSED_USERNAME/mcp-dev-environment.git (fetch)
origin  git@github.com:GUESSED_USERNAME/mcp-dev-environment.git (push)
```

**If GUESSED_USERNAME is wrong:**

```bash
# Remove wrong remote
git remote remove origin

# Add correct remote with YOUR actual username
git remote add origin git@github.com:YOUR_ACTUAL_USERNAME/mcp-dev-environment.git

# Verify
git remote -v
```

---

### **Step 15: Create Repository on GitHub**

**In your browser (Chrome):**

1. Go to: **https://github.com/new**
2. **Repository name:** `mcp-dev-environment`
3. **Description:** "Local MCP development environment with Docker, Nginx reverse proxy, and example MCP servers"
4. Select **Private** (recommended)
5. **Don't** check "Add a README file" (you already have files)
6. Click **"Create repository"**

✅ **Repository created!**

---

### **Step 16: Push to GitHub**

**In your WSL terminal:**

```bash
cd ~/mcp-dev-environment

# Push (may hang without output - this is normal)
git push -u origin main --verbose
```

**If command hangs:**
- Wait 30 seconds
- If still no output, press `Ctrl+C`
- Retry with `--verbose` flag (as shown above)

**Expected success output:**
```
Enumerating objects: 23, done.
Counting objects: 100% (23/23), done.
Compressing objects: 100% (18/18), done.
Writing objects: 100% (23/23), 7.89 KiB | 3.95 MiB/s, done.
Total 23 (delta 0), reused 0 (delta 0)
To github.com:YOUR_USERNAME/mcp-dev-environment.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.
```

✅ **Pushed to GitHub!**

---

### **Step 17: Verify on GitHub**

**Open in browser:**
```
https://github.com/YOUR_USERNAME/mcp-dev-environment
```

**You should see:**
- ✅ All files (docker-compose.yml, Makefile, nginx/, servers/, etc.)
- ✅ SETUP_COMPLETE.md
- ✅ Your commit message
- ✅ Private repository badge (if you chose private)

🎉 **Success! Your environment is backed up on GitHub!**

---

### **Troubleshooting Git Push**

**Issue: "Permission denied (publickey)"**

**Solution:** SSH key not loaded
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
ssh -T git@github.com  # Should say "Hi USERNAME!"
git push -u origin main --verbose
```

---

**Issue: "Repository not found"**

**Solution:** Wrong username or repo doesn't exist
```bash
# Check remote URL
git remote -v

# Fix if needed
git remote remove origin
git remote add origin git@github.com:CORRECT_USERNAME/mcp-dev-environment.git

# Ensure repo exists on GitHub (create it manually)
# Then retry push
```

---

**Issue: Command hangs with no output**

**Solution:** Terminal instability - normal behavior
```bash
# Press Ctrl+C to cancel
# Retry with verbose flag
git push -u origin main --verbose

# Or check if it actually worked:
git log --oneline
git remote -v
# Then try push again
```

---

**Issue: "fatal: The current branch main has no upstream branch"**

**Solution:** First push needs `-u` flag
```bash
git push -u origin main
```

---

✅ **Git push complete! Your code is safely on GitHub.**

---

## Next Steps After Phase 2

Once your environment is running:

1. ✅ **Connect Claude Desktop to local MCP server**
2. ✅ **Test MCP tools work correctly**
3. ✅ **Migrate existing MCP servers** (Santa Clara, AAA, etc.)
4. ✅ **Add authentication and security**
5. ✅ **Deploy to Google Cloud Run** (when ready)

Continue to Phase 3 for deployment to production!

---

## Phase 3: Connect Claude Desktop to Your MCP Server (15-20 minutes)

Now that your MCP development environment is running, connect Claude Desktop to use your local MCP server.

---

### **Prerequisites Check**

Before starting Phase 3, verify:

```bash
cd ~/mcp-dev-environment

# 1. Containers are running
docker compose ps

# Should show:
# - mcp-dev-environment-nginx-1 (Up)
# - mcp-dev-environment-santa-clara-1 (Up)

# 2. Get exact container name for santa-clara
docker compose ps | grep santa-clara

# Note the EXACT name (e.g., mcp-dev-environment-santa-clara-1)

# 3. Test MCP server responds
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | docker exec -i mcp-dev-environment-santa-clara-1 python -u /app/server.py

# Should return JSON with get_property_info tool
```

✅ **If all tests pass, continue to configuration.**

---

### **Step 14: Locate Claude Desktop Config File**

**Windows Path:**
```
C:\Users\YOUR_USERNAME\AppData\Roaming\Claude\claude_desktop_config.json
```

**To open:**

**Option A: File Explorer**
1. Press **Windows + R**
2. Type: `%AppData%\Claude`
3. Press **Enter**
4. Open `claude_desktop_config.json` in Notepad or VS Code

**Option B: Command**
1. Open PowerShell
2. Run: `notepad $env:APPDATA\Claude\claude_desktop_config.json`

---

### **Step 15: Add MCP Server Configuration**

**If file is empty or doesn't exist, create it with:**

```json
{
  "mcpServers": {
    "santa-clara-local": {
      "command": "wsl",
      "args": [
        "docker",
        "exec",
        "-i",
        "mcp-dev-environment-santa-clara-1",
        "python",
        "-u",
        "/app/server.py"
      ]
    }
  }
}
```

**If file already has other MCP servers:**

```json
{
  "mcpServers": {
    "existing-server": {
      ...existing config...
    },
    "santa-clara-local": {
      "command": "wsl",
      "args": [
        "docker",
        "exec",
        "-i",
        "mcp-dev-environment-santa-clara-1",
        "python",
        "-u",
        "/app/server.py"
      ]
    }
  }
}
```

**CRITICAL:**
- Use `"wsl"` as the command (not `"docker"` or `"bash"`)
- Use the EXACT container name from `docker compose ps`
- Include `-u` flag for unbuffered Python output
- Save the file

---

### **Step 16: Restart Claude Desktop**

**Complete restart required:**

1. **Close Claude Desktop:**
   - Right-click Claude Desktop icon in system tray (bottom-right)
   - Click **"Quit"** or **"Exit"**
   - **OR** close window and ensure it's not in system tray

2. **Wait 5 seconds**

3. **Restart Claude Desktop:**
   - Press Windows key
   - Type "Claude"
   - Open Claude Desktop

---

### **Step 17: Verify Connection**

**In Claude Desktop chat, ask:**

```
What MCP tools do you have access to?
```

**Expected Response:**

Claude should list:
- **santa-clara-local** server
- **get_property_info** tool
- Tool description and parameters

---

### **Step 18: Test the Tool**

**Ask Claude:**

```
Use the santa-clara-local server to get property information for APN 288-12-033
```

**Expected Result:**

Claude should call the tool and return property information including:
- Address
- Owner
- Property type
- Assessed value
- Tax amount
- Year built
- Lot and building sizes

✅ **If you see property data, Phase 3 is complete!**

---

### **Troubleshooting Phase 3**

#### **Issue: "Could not attach to MCP server" error on startup**

**Check 1: Container name is correct**
```bash
# Get exact name
docker compose ps | grep santa-clara

# Update config with exact name (including prefix)
# e.g., "mcp-dev-environment-santa-clara-1"
```

**Check 2: Container is running**
```bash
docker compose ps
docker compose up -d  # If stopped
```

**Check 3: Config file syntax**
- Valid JSON (no trailing commas, matching brackets)
- Use online JSON validator if unsure
- Check quotes are straight quotes, not curly quotes

---

#### **Issue: Server appears in tools list but can't execute tools**

**Check logs:**
```
C:\Users\YOUR_USERNAME\AppData\Roaming\Claude\logs\mcp-server-santa-clara-local.log
```

**Common causes:**
1. **Wrong container name** - Update config with exact name
2. **Container stopped** - Restart: `docker compose restart santa-clara`
3. **Python buffered output** - Ensure `-u` flag in config

---

#### **Issue: Tools list shows but timeout errors**

**Symptom:** Tools appear but Claude says "request timed out"

**Solution:** Server not responding fast enough

```bash
# Test response time (should be < 1 second)
time docker exec -i mcp-dev-environment-santa-clara-1 python -u /app/server.py <<< '{"jsonrpc":"2.0","method":"tools/list","id":1}'

# If slow, check container logs
docker logs mcp-dev-environment-santa-clara-1
```

---

#### **Issue: "No such container" error**

**Solution:** Container name in config doesn't match actual container

```bash
# Get correct name
docker compose ps

# Update claude_desktop_config.json with exact name
```

---

#### **Issue: Changes to config not taking effect**

**Solution:** Claude Desktop must be fully restarted

1. Close completely (check system tray)
2. Wait 5 seconds
3. Restart
4. Try again

**Also check:** Config file saved after editing

---

### **Verification Checklist**

Before considering Phase 3 complete:

- [ ] `docker compose ps` shows both containers running
- [ ] Manual test of MCP server succeeds
- [ ] Config file in correct location (`C:\Users\...\AppData\Roaming\Claude\`)
- [ ] Config uses `"wsl"` command
- [ ] Config has correct container name
- [ ] Config includes `-u` flag
- [ ] Config is valid JSON
- [ ] Claude Desktop restarted completely
- [ ] Tools appear in Claude's tool list
- [ ] Can successfully call `get_property_info` tool
- [ ] Property data is returned

✅ **All items checked = Phase 3 Complete!**

---

## Phase 3 Complete! 🎉

**What you have now:**

✅ **Phase 1:** Prerequisites installed (WSL, Docker, Git, VS Code, SSH)  
✅ **Phase 2:** MCP development environment running  
✅ **Phase 3:** Claude Desktop connected to local MCP server  

**What you can do:**

- Use Claude Desktop to query property information via your local MCP server
- Develop additional MCP servers in the same environment
- Test MCP integrations before deploying to production

---

## Phase 4: What Claude Will Build (Reference)

Claude will create this structure:

```
~/mcp-dev-environment/
├── docker-compose.yml           # Orchestration
├── .env.example                 # Environment template
├── Makefile                     # Commands (make start, make logs)
├── setup.sh                     # Automated setup
├── README.md                    # Documentation
│
├── nginx/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── conf.d/
│       └── mcp-servers.conf
│
├── certs/
│   ├── localhost.pem
│   └── localhost-key.pem
│
├── servers/
│   ├── santa-clara/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── server.py            # Your HTTP MCP server
│   │   └── tests/
│   │       └── test_server.py
│   │
│   └── shared/
│       ├── mcp_base.py
│       └── logging_config.py
│
├── logs/                        # Created by Docker
├── data/                        # Test data
└── scripts/
    ├── test-endpoints.sh
    ├── tail-logs.sh
    └── generate-certs.sh
```

---

## Phase 4: Iterative Development with Claude Code

Once the environment is set up, use Claude Code for development:

### Open Project in VS Code

```bash
# In WSL terminal
cd ~/mcp-dev-environment
code .
```

### Development Workflow

**1. Start Services:**
```bash
make start
# Or: docker-compose up -d
```

**2. Make Changes to Code:**
- Open `servers/santa-clara/server.py`
- Make your changes
- Save

**3. Ask Claude Code to Help:**

Press `Ctrl+L` (Claude Code chat) and say:
```
I changed the server.py file. Can you:
1. Review my changes for bugs
2. Rebuild the Docker container
3. Test the endpoint
4. Show me the logs if there are errors
```

**4. Claude Code Will:**
- Review your code
- Run `docker-compose build santa-clara-mcp`
- Run `docker-compose up -d santa-clara-mcp`
- Test with curl
- Read logs and diagnose errors
- Suggest fixes

**5. Iterate:**
- Claude Code suggests fixes
- You approve
- Claude Code applies fixes and tests again
- Repeat until working

---

## Phase 5: Troubleshooting with Claude

### When Something Fails

**Instead of googling, ask Claude:**

```
The Santa Clara MCP server is failing to start. Here are the logs:

[paste docker-compose logs santa-clara-mcp output]

Can you:
1. Identify the issue
2. Suggest a fix
3. Apply the fix
4. Rebuild and test
```

**Claude will:**
- Analyze the error
- Identify root cause (missing dependency, wrong port, etc.)
- Suggest fix with explanation
- Apply the fix to the appropriate file
- Rebuild and verify it works

### Common Issues Claude Will Fix

| Issue | Claude's Solution |
|-------|-------------------|
| Port already in use | Change port in docker-compose.yml |
| Python dependency missing | Add to requirements.txt and rebuild |
| Playwright not installing | Fix Dockerfile with correct dependencies |
| SSL certificate errors | Regenerate certs with proper CN |
| Permission denied | Fix volume permissions with chown |
| Container won't start | Check logs, fix config, rebuild |

---

## Phase 6: Connect Claude Desktop to Your Local MCP Server

Once everything is running, connect Claude Desktop:

### Step 1: Get Your Server URL

```bash
# Test that Nginx is running
curl -k https://localhost:8443/santa-clara/mcp \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

Should return JSON with your tools.

### Step 2: Update Claude Desktop Config

**In PowerShell:**
```powershell
notepad "$env:APPDATA\Claude\claude_desktop_config.json"
```

**Add:**
```json
{
  "mcpServers": {
    "santa-clara-dev": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://localhost:8443/santa-clara/mcp"
      ]
    }
  }
}
```

**Save and restart Claude Desktop.**

### Step 3: Test in Claude Desktop

Ask Claude Desktop:
```
What tools do you have available from the santa-clara-dev server?
```

Claude should list your MCP tools!

---

## Phase 7: Add More MCP Servers

To add a new MCP server (e.g., AAA Insurance):

**Ask Claude Code:**
```
I want to add a new MCP server for AAA Insurance. Can you:

1. Create the directory structure in servers/aaa-insurance/
2. Create a Dockerfile based on the santa-clara template
3. Create server.py with placeholder tools
4. Add it to docker-compose.yml
5. Add the Nginx route
6. Build and test it

The server should have two tools:
- get_policy_status(policy_number)
- get_last_claim(policy_number)
```

**Claude Code will:**
- Create all files
- Update configs
- Build and start the container
- Test the endpoints
- Show you the results

---

## Best Practices for Working with Claude

### 1. Be Specific About Errors

❌ **Bad:** "It's not working"

✅ **Good:** 
```
The santa-clara MCP container fails to start with this error:
[paste exact error message]

Here's the full docker-compose logs output:
[paste logs]
```

### 2. Let Claude Read Logs Directly

✅ **Good:**
```
Can you check the logs for santa-clara-mcp and tell me what's failing?

Run: docker-compose logs santa-clara-mcp --tail 50
```

### 3. Ask Claude to Verify After Fixes

✅ **Good:**
```
After applying that fix:
1. Rebuild the container
2. Start it
3. Test the /mcp endpoint
4. Confirm it's working
```

### 4. Request Explanations

✅ **Good:**
```
Before we make that change to nginx.conf, can you explain:
1. What the change does
2. Why it fixes the issue
3. Any potential side effects
```

---

## Advantages of This Approach

### For You
✅ **Minimal manual work** - Claude does the heavy lifting  
✅ **Learn as you go** - Claude explains each step  
✅ **Fast iteration** - Change → Test → Fix cycle is seconds  
✅ **No googling** - Claude troubleshoots errors instantly  

### For Claude
✅ **Full context** - Can read logs, configs, code  
✅ **Can execute** - Runs commands and sees results  
✅ **Can iterate** - Try fix → Test → Try again  
✅ **Can verify** - Tests endpoints to confirm fixes work  

### For Development
✅ **Production parity** - Same Docker setup as Cloud Run  
✅ **Reproducible** - Docker ensures consistency  
✅ **Isolated** - No conflicts with other projects  
✅ **Scalable** - Easy to add more MCP servers  

---

## Expected Timeline

| Phase | Time | Who Does It |
|-------|------|-------------|
| Install WSL, Docker, VS Code | 20 min | You (manual) |
| Install Claude Desktop | 5 min | You (manual) |
| Create dev environment | 5 min | Claude Desktop |
| Build first MCP server | 10 min | Claude Code |
| Debug and test | 10 min | Claude Code |
| Connect to Claude Desktop | 5 min | You |
| **Total** | **~1 hour** | Mostly automated |

---

## Success Criteria

You'll know it's working when:

✅ `docker-compose ps` shows all containers running  
✅ `curl https://localhost:8443/santa-clara/mcp` returns JSON  
✅ Claude Desktop shows your MCP server in connectors  
✅ Claude Desktop can call your MCP tools successfully  
✅ Logs appear in `~/mcp-dev-environment/logs/`  
✅ Claude Code can read logs and troubleshoot errors  

---

## Next Steps After Setup

Once your dev environment is running:

1. **Migrate your Santa Clara MCP** - Copy code into the template
2. **Add AAA Insurance MCP** - Create second server
3. **Add TurboTax MCP** - Create third server
4. **Add Chase MCP** - Create fourth server
5. **Test all locally** - Verify everything works
6. **Deploy to Cloud Run** - Same Docker images!

---

## Troubleshooting

### Issue: WSL won't install

**Fix:**
```powershell
# Enable Windows features manually
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Restart Windows
shutdown /r /t 0

# After restart, try again
wsl --install
```

### Issue: Docker Desktop won't start

**Fix:**
1. Open Docker Desktop
2. Go to Settings → Resources → WSL Integration
3. Enable Ubuntu
4. Click "Apply & Restart"
5. Wait 2-3 minutes for Docker daemon to start

### Issue: Claude Desktop can't connect to localhost

**Potential causes:**
- Firewall blocking port 8443
- Certificate not trusted
- Docker containers not running

**Ask Claude Code to diagnose:**
```
Claude, can you help me troubleshoot why Claude Desktop can't connect to https://localhost:8443/santa-clara/mcp?

Please:
1. Check if Docker containers are running
2. Test the endpoint with curl
3. Check Nginx logs
4. Verify the SSL certificate
```

---

## Reference: Essential Commands

```bash
# Start everything
make start
# Or: docker-compose up -d

# Stop everything
make stop
# Or: docker-compose down

# View logs (all services)
make logs
# Or: docker-compose logs -f

# View logs (specific service)
docker-compose logs -f santa-clara-mcp

# Rebuild after code changes
make rebuild
# Or: docker-compose up -d --build

# Test endpoint
make test
# Or: curl -k https://localhost:8443/santa-clara/mcp -X POST ...

# Restart single service
docker-compose restart santa-clara-mcp

# View running containers
docker-compose ps

# Execute command in container
docker-compose exec santa-clara-mcp bash
```

---

## Ready to Start?

**Your first prompt to Claude Desktop:**

```
I'm setting up a new Windows workstation for MCP server development. I've completed Phase 1 (installed WSL2, Docker Desktop, Claude Desktop, VS Code, and Git).

Now I need you to help me with Phase 2: Build the complete development environment.

Please:
1. Create ~/mcp-dev-environment directory structure
2. Check what system dependencies I need in WSL
3. Create docker-compose.yml with Nginx + example MCP server
4. Generate SSL certificates for localhost
5. Create Makefile with common commands
6. Build and test everything
7. Show me how to connect Claude Desktop to the local MCP server

Let's start with creating the directory structure and showing me what you're going to build.
```

**Claude will take it from there!**
