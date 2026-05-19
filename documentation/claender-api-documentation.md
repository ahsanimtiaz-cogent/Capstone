# Google Calendar API Setup

## Step 1: Open Google Cloud Console

Go to the following URL:

https://console.cloud.google.com/marketplace/product/google/calendar-json.googleapis.com?q=search&referrer=search

---

## Step 2: Enable Google Calendar API

Click on:

- **Enable**

This will enable the Google Calendar API for your project.

---

## Step 3: Open Credentials Section

From the left sidebar navigation:

- Go to **APIs & Services**
- Click on **Credentials**

Direct URL:

https://console.cloud.google.com/apis/credentials

---

## Step 4: Create OAuth 2.0 Client ID

Inside the Credentials page:

- Click **Create Credentials**
- Select **OAuth Client ID**

---

## Step 5: Configure OAuth Consent Screen (If Prompted)

If Google asks you to configure the consent screen:

- Select **External**
- Fill required application details
- Save and continue

---

## Step 6: Select Application Type

For local Python development:

- Choose **Desktop App**

Then:

- Enter application name
- Click **Create**

---

## Step 7: Download Credentials File

After creation:

- Download the generated JSON file
- Rename it to:

```bash
credentials.json