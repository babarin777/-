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
    - Copy the contents of `Index.html` from this repository and paste it into the `Index.html` file in the GAS editor.

3.  **Deploy as Web App**:
    - Click **Deploy** > **New Deployment**.
    - Select type **Web App**.
    - Description: "News Gadget Initial Version".
    - Execute as: **Me**.
    - Who has access: **Anyone** (or "Only myself" if you want to keep it private).
    - Click **Deploy**.

4.  **Authorize**:
    - You will be asked to authorize the script to connect to an external service (Google News). Click **Review Permissions** and allow it.

5.  **Access the App**:
    - After deployment, you will get a **Web App URL**. Open this URL in your browser to use the gadget.

## Features
- **3 Keyword Input**: Input keywords to fetch matching latest news.
- **Pale Color Theme**: Distinctive pale blue, pink, and green sections for each keyword.
- **Nikkei Priority**: Articles from "日本経済新聞" or containing "日経" are sorted to the top and marked with a badge.
- **Image Support**: Displays article thumbnails by scraping OG images (for top entries).
- **Responsive Web App**: Works on both desktop and mobile browsers.
