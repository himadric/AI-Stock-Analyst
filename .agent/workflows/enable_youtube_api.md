---
description: How to enable the YouTube Data API and get an API Key
---

1.  **Go to Google Cloud Console**: Visit [console.cloud.google.com](https://console.cloud.google.com/).
2.  **Create a New Project**: Click the project dropdown in the top bar and select **"New Project"**. Name it "AI Analyst" and click **Create**.
3.  **Enable API**:
    *   Go to **APIs & Services > Library**.
    *   Search for **"YouTube Data API v3"**.
    *   Click on it and click **Enable**.
4.  **Create Credentials**:
    *   Go to **APIs & Services > Credentials**.
    *   Click **+ CREATE CREDENTIALS** > **API key**.
    *   Copy the generated API Key.
5.  **Configure `.env`**:
    *   Open `api/.env` in your editor.
    *   Add: `YOUTUBE_API_KEY=your_copied_key_here`
