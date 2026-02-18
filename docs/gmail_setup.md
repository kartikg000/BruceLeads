# Gmail API Setup Guide

This guide walks you through setting up Gmail API access for BruceLeads.

## Prerequisites

- A Google account
- Access to [Google Cloud Console](https://console.cloud.google.com)

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click the project dropdown at the top → **New Project**
3. Name it `BruceLeads` (or anything you prefer)
4. Click **Create**
5. Select your new project from the dropdown

## Step 2: Enable Gmail API

1. Go to **APIs & Services** → **Library**
2. Search for "Gmail API"
3. Click on **Gmail API**
4. Click **Enable**

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** user type → Click **Create**
3. Fill in required fields:
   - **App name**: BruceLeads
   - **User support email**: Your email
   - **Developer contact**: Your email
4. Click **Save and Continue**
5. On Scopes page, click **Add or Remove Scopes**
6. Find and select:
   - `https://www.googleapis.com/auth/gmail.compose`
   - `https://www.googleapis.com/auth/gmail.send`
7. Click **Update** → **Save and Continue**
8. On Test users page, click **Add Users**
9. Add your Gmail address
10. Click **Save and Continue** → **Back to Dashboard**

## Step 4: Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Select **Desktop app** as application type
4. Name it `BruceLeads Desktop`
5. Click **Create**
6. Click **Download JSON**
7. Rename the downloaded file to `gmail_credentials.json`
8. Move it to `BruceLeads/credentials/gmail_credentials.json`

## Step 5: Authenticate

Run the setup script:

```bash
python emailer/oauth_setup.py
```

A browser window will open. Sign in with your Google account and grant permissions.

Once complete, a token file will be saved and you can use Gmail features in BruceLeads.

## Troubleshooting

### "Access blocked: This app's request is invalid"

Your OAuth consent screen may not be configured correctly. Make sure:
- You've added your email as a test user
- The app is in "Testing" mode (not "In production")

### "Credentials file not found"

Make sure you've:
1. Downloaded the credentials JSON from Google Cloud Console
2. Renamed it to `gmail_credentials.json`
3. Placed it in the `credentials/` folder

### "Token has been expired or revoked"

Delete the token file and re-authenticate:

```bash
del credentials\gmail_token.json  # Windows
python emailer/oauth_setup.py
```

## Security Notes

- **Never commit credentials to git** - The `.gitignore` file excludes the credentials folder
- **Keep your credentials safe** - Anyone with these files can access your Gmail
- **Use a dedicated account** - Consider using a separate Gmail for outreach
