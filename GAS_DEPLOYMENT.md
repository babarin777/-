# Keyword News Gadget for Google Apps Script (GAS)

This project is a port of the Python news gadget to Google Apps Script. It provides a web app that displays latest news for 3 keywords, prioritizing Nikkei-related content.

## Setup Instructions

1.  **Create a New GAS Project**:
    - Go to [script.google.com](https://script.google.com/).
    - Click **New Project**.
    - Rename the project to "Keyword News Gadget".

2.  **Add Files**:
    - Copy the contents of `Code.gs` from this repository and paste it into the `Code.gs` file in the GAS editor.
    - Click the **+** button next to "Files", select **HTML**, and name it `Index`.
      - **CRITICAL**: The name must be exactly `Index` (case-sensitive).

3.  **Deploy as Web App**:
    - Click **Deploy** > **New Deployment**.
    - Select type **Web App**.
    - Execute as: **Me**.
    - Who has access: **Anyone** (or "Only myself").
    - Click **Deploy**.

4.  **Authorize**:
    - Click **Review Permissions** and allow it.
    - (If it says "Google hasn't verified this app", click "Advanced" and then "Go to Keyword News Gadget (unsafe)").

5.  **Access the App**:
    - After deployment, you will get a **Web App URL**. Open this URL in your browser.

## Troubleshooting

- **Error: "Index" not found**:
  - Make sure you created an HTML file and named it exactly `Index`.
- **Empty Feed / Loading Stuck**:
  - Check the **Execution Logs** in the GAS editor (left sidebar icon). Any errors during RSS fetching will be logged there.
  - Sometimes Google News RSS is temporarily unavailable. Try again after a few minutes.
- **Permission Denied**:
  - Ensure you are signed into only one Google account in your browser, or open the Web App URL in an Incognito/Private window.

## Features
- **3 Keyword Input**: Input keywords to fetch matching latest news.
- **Pale Color Theme**: Distinctive pale blue, pink, and green sections.
- **Nikkei Priority**: Articles from "日本経済新聞" are sorted to the top.
- **Responsive**: Works on desktop and mobile.
