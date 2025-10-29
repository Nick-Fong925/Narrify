# YouTube OAuth Setup Guide

## 📋 Overview

This guide will help you set up YouTube OAuth credentials so Narrify can automatically upload videos to your YouTube channel.

## 🔐 Where to Put Your OAuth Credentials

Your OAuth credentials file should be placed at:

```
/Users/nicholasfong/Documents/projects/Narrify/backend/config/youtube_credentials.json
```

## 📥 How to Get OAuth Credentials

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Create Project"** or select an existing project
3. Give your project a name (e.g., "Narrify YouTube Automation")
4. Click **"Create"**

### Step 2: Enable YouTube Data API v3

1. In the Google Cloud Console, go to **"APIs & Services"** → **"Library"**
2. Search for **"YouTube Data API v3"**
3. Click on it and click **"Enable"**

### Step 3: Create OAuth Credentials

1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
3. If prompted, configure the OAuth consent screen:

   - **User Type**: External (unless you have a Google Workspace)
   - **App name**: Narrify
   - **User support email**: Your email
   - **Developer contact**: Your email
   - Click **"Save and Continue"**
   - **Scopes**: Skip for now (click "Save and Continue")
   - **Test users**: Add your Google account email
   - Click **"Save and Continue"**

4. Back to creating OAuth client ID:

   - **Application type**: Desktop app
   - **Name**: Narrify Desktop Client
   - Click **"Create"**

5. Download the credentials:
   - Click the **Download** button (⬇️) next to your newly created OAuth client
   - Save the file as `youtube_credentials.json`

### Step 4: Place Credentials File

Move the downloaded file to the correct location:

```bash
# Create config directory if it doesn't exist
mkdir -p /Users/nicholasfong/Documents/projects/Narrify/backend/config

# Move your downloaded file (adjust source path as needed)
mv ~/Downloads/client_secret_*.json /Users/nicholasfong/Documents/projects/Narrify/backend/config/youtube_credentials.json
```

## 🧪 Test Your Setup

### Run the Test Script

The test script will:

- Generate ONE video from your highest-scoring unpublished post
- Upload it to YouTube as **UNLISTED** (pending)
- Show you the URL to preview it

```bash
cd /Users/nicholasfong/Documents/projects/Narrify/backend

# Basic test (uploads as unlisted)
python scripts/test_video_upload.py

# Upload as private instead
python scripts/test_video_upload.py --privacy private

# Test specific post by ID
python scripts/test_video_upload.py --post-id 123

# Keep video file after upload
python scripts/test_video_upload.py --keep-video
```

### First-Time Authentication

The **first time** you run the test script:

1. A browser window will open automatically
2. Sign in to your Google account (the one that owns the YouTube channel)
3. Click **"Continue"** when warned about unverified app
4. Click **"Allow"** to grant permissions
5. You'll see "The authentication flow has completed"
6. Close the browser - the script will continue

A token file will be saved at `config/youtube_token.json` for future use.

## 📁 File Structure

After setup, your config directory should look like this:

```
backend/config/
├── automation.yaml                  # Automation schedule config
├── youtube_credentials.json         # OAuth credentials (from Google Cloud)
└── youtube_token.json              # Generated after first auth (auto-created)
```

## 🎬 Privacy Options

| Privacy Status | Description                         | When to Use                           |
| -------------- | ----------------------------------- | ------------------------------------- |
| **unlisted**   | Only people with the link can view  | Testing - review before making public |
| **private**    | Only you can view in YouTube Studio | Testing - maximum privacy             |
| **public**     | Everyone can find and view          | Production - automatic posting        |

The test script defaults to **unlisted** so you can preview the video before making it public.

## ✅ Verification Checklist

- [ ] Google Cloud Project created
- [ ] YouTube Data API v3 enabled
- [ ] OAuth credentials downloaded
- [ ] Credentials file placed at `config/youtube_credentials.json`
- [ ] Test script runs without errors
- [ ] Browser opens for authentication
- [ ] Successfully authenticated
- [ ] Token file created at `config/youtube_token.json`
- [ ] Test video uploaded to YouTube
- [ ] Video visible on YouTube

## 🚨 Troubleshooting

### Error: "credentials file not found"

- Make sure the file is at the exact path: `config/youtube_credentials.json`
- Check the filename - it should be exactly `youtube_credentials.json`, not `client_secret_*.json`

### Error: "Access blocked: Authorization Error"

- Add your Google account as a test user in OAuth consent screen
- Make sure you're signing in with the correct Google account

### Error: "The OAuth client was not found"

- Re-download the credentials file from Google Cloud Console
- Make sure you selected "Desktop app" as the application type

### Error: "Quota exceeded"

- YouTube API free tier: 10,000 units/day (~6 uploads)
- Wait 24 hours or apply for quota increase at Google Cloud Console

### Browser doesn't open for authentication

- The script will print a URL - copy and paste it into your browser manually
- Make sure you're running from a machine with a browser

## 🔒 Security Notes

⚠️ **IMPORTANT**:

- Never commit `youtube_credentials.json` or `youtube_token.json` to git
- These files are already in `.gitignore`
- Keep these files secure - they grant access to your YouTube channel

## 📖 Next Steps

After successful test upload:

1. **Check your video**: Visit the URL provided by the test script
2. **Verify quality**: Make sure video, audio, and subtitles look good
3. **Make public** (optional): Change privacy in YouTube Studio if satisfied
4. **Run automation**: Start the full automation system

```bash
# Start the backend server (includes automatic scheduling)
python -m uvicorn app.main:app --reload

# Or run automation manually
python scripts/run_automation.py

# Dry run (preview without generating/uploading)
python scripts/run_automation.py --dry-run
```

## 📞 Support

If you encounter issues:

1. Check the logs: `tail -f logs/narrify.log`
2. Review this guide
3. Check Google Cloud Console for API errors
4. Verify YouTube API is enabled

---

**Last Updated**: October 22, 2025
