/**
 * GET request handler to serve the UI.
 */
function doGet() {
  return HtmlService.createTemplateFromFile('Index')
      .evaluate()
      .setTitle('Keyword News Gadget')
      .addMetaTag('viewport', 'width=device-width, initial-scale=1')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/**
 * Fetch and parse Google News RSS for a given keyword.
 * Prioritizes Nikkei-related articles and scrapes OG images.
 */
function getNews(keyword) {
  if (!keyword) return [];

  const encodedQuery = encodeURIComponent(keyword);
  const url = `https://news.google.com/rss/search?q=${encodedQuery}&hl=ja&gl=JP&ceid=JP:ja`;

  try {
    const response = UrlFetchApp.fetch(url, {
      'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      },
      'muteHttpExceptions': true
    });

    if (response.getResponseCode() !== 200) {
      throw new Error(`Failed to fetch RSS: ${response.getResponseCode()}`);
    }

    const content = response.getContentText();
    const document = XmlService.parse(content);
    const root = document.getRootElement();
    const channel = root.getChild('channel');
    const items = channel.getChildren('item');

    let entries = items.map(item => {
      const title = item.getChild('title').getText();
      const link = item.getChild('link').getText();
      const pubDate = item.getChild('pubDate').getText();
      const source = item.getChild('source') ? item.getChild('source').getText() : 'News';
      const timestamp = new Date(pubDate).getTime();

      const isNikkei = source.includes('日本経済新聞') || title.includes('日経');

      return {
        title,
        link,
        pubDate,
        source,
        timestamp,
        isNikkei
      };
    });

    // Sort: Nikkei first, then latest date
    entries.sort((a, b) => {
      if (a.isNikkei !== b.isNikkei) {
        return a.isNikkei ? -1 : 1;
      }
      return b.timestamp - a.timestamp;
    });

    // Process top 10 and fetch images for top 3
    const processedEntries = entries.slice(0, 10).map((entry, index) => {
      if (index < 3) {
        entry.image = getOgImage(entry.link);
      }
      return entry;
    });

    return processedEntries;

  } catch (e) {
    Logger.log(`Error fetching keyword "${keyword}": ${e.toString()}`);
    return { error: e.toString() };
  }
}

/**
 * Scrape og:image metadata from a URL.
 */
function getOgImage(url) {
  try {
    const response = UrlFetchApp.fetch(url, {
      'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      },
      'muteHttpExceptions': true,
      'followRedirects': true
    });

    if (response.getResponseCode() !== 200) return null;

    const html = response.getContentText();
    // Using regex as XmlService doesn't work for non-valid XML/HTML
    const match = html.match(/<meta [^>]*property=["']og:image["'] [^>]*content=["']([^"']+)["']/i) ||
                  html.match(/<meta [^>]*content=["']([^"']+)["'] [^>]*property=["']og:image["']/i);

    if (match && match[1]) {
      let imgUrl = match[1];
      if (imgUrl.startsWith('//')) imgUrl = 'https:' + imgUrl;
      return imgUrl;
    }
  } catch (e) {
    // Ignore image fetch errors
  }
  return null;
}
