/**
 * GET request handler to serve the UI.
 * Using createHtmlOutputFromFile to minimize template parsing errors.
 */
function doGet() {
  try {
    return HtmlService.createHtmlOutputFromFile('Index')
        .setTitle('Keyword News Gadget')
        .addMetaTag('viewport', 'width=device-width, initial-scale=1')
        .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
  } catch (e) {
    return HtmlService.createHtmlOutput('<html><body><h1>Initialization Error</h1><p>' + e.toString() + '</p><p>Please ensure you have created an HTML file named <b>Index</b> (case-sensitive) in your GAS project.</p></body></html>');
  }
}

/**
 * Fetch and parse Google News RSS for a given keyword.
 * Prioritizes Nikkei-related articles and scrapes OG images.
 */
function getNews(keyword) {
  if (!keyword) return [];

  const encodedQuery = encodeURIComponent(keyword);
  // Ensure the URL is valid and targets Japanese results
  const url = 'https://news.google.com/rss/search?q=' + encodedQuery + '&hl=ja&gl=JP&ceid=JP:ja';

  try {
    console.log('Fetching RSS for: ' + keyword);
    const response = UrlFetchApp.fetch(url, {
      'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      },
      'muteHttpExceptions': true,
      'timeoutInSeconds': 20
    });

    if (response.getResponseCode() !== 200) {
      console.error('RSS Fetch Failed: ' + response.getResponseCode());
      return { error: 'Failed to fetch news (HTTP ' + response.getResponseCode() + ')' };
    }

    const content = response.getContentText().trim();
    if (!content) return [];

    const document = XmlService.parse(content);
    const root = document.getRootElement();
    const channel = root.getChild('channel');
    if (!channel) return [];

    const items = channel.getChildren('item');
    if (!items || items.length === 0) return [];

    let entries = items.map(function(item) {
      const title = item.getChild('title') ? item.getChild('title').getText() : 'No Title';
      const link = item.getChild('link') ? item.getChild('link').getText() : '#';
      const pubDate = item.getChild('pubDate') ? item.getChild('pubDate').getText() : '';
      const sourceElement = item.getChild('source');
      const source = sourceElement ? sourceElement.getText() : 'News';

      // Basic timestamp parsing
      let timestamp = 0;
      try { timestamp = new Date(pubDate).getTime(); } catch(err) {}

      const isNikkei = source.indexOf('日本経済新聞') !== -1 || title.indexOf('日経') !== -1;

      return {
        title: title,
        link: link,
        pubDate: pubDate,
        source: source,
        timestamp: timestamp,
        isNikkei: isNikkei
      };
    });

    // Sort logic: Nikkei prioritized, then latest date
    entries.sort(function(a, b) {
      if (a.isNikkei !== b.isNikkei) {
        return a.isNikkei ? -1 : 1;
      }
      return b.timestamp - a.timestamp;
    });

    // Process top 10 items, fetch images for top 3
    const processedEntries = entries.slice(0, 10).map(function(entry, index) {
      if (index < 3) {
        entry.image = getOgImage(entry.link);
      }
      return entry;
    });

    return processedEntries;

  } catch (e) {
    console.error('Error in getNews: ' + e.toString());
    return { error: 'Execution error: ' + e.message };
  }
}

/**
 * Scrape og:image metadata from a URL.
 */
function getOgImage(url) {
  if (!url || url === '#') return null;
  try {
    const response = UrlFetchApp.fetch(url, {
      'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      },
      'muteHttpExceptions': true,
      'followRedirects': true,
      'timeoutInSeconds': 5
    });

    if (response.getResponseCode() !== 200) return null;

    const html = response.getContentText();
    // Case-insensitive regex for og:image
    const match = html.match(/<meta [^>]*property=["']og:image["'] [^>]*content=["']([^"']+)["']/i) ||
                  html.match(/<meta [^>]*content=["']([^"']+)["'] [^>]*property=["']og:image["']/i);

    if (match && match[1]) {
      let imgUrl = match[1];
      if (imgUrl.indexOf('//') === 0) imgUrl = 'https:' + imgUrl;
      return imgUrl;
    }
  } catch (e) {
    // Ignore individual image errors to maintain overall performance
  }
  return null;
}
