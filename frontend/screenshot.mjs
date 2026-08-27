import puppeteer from 'puppeteer';

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

(async () => {
  console.log('Starting puppeteer...');
  const browser = await puppeteer.launch({
    headless: 'new',
    defaultViewport: null,
    executablePath: CHROME,
  });
  const page = await browser.newPage();
  const baseUrl = 'http://localhost:52008';

  // Helper: clear sessionStorage so we always see cover page
  const clearSession = async () => {
    await page.evaluate(() => sessionStorage.clear());
  };

  try {
    /* ---- COVER PAGE screenshots ---- */
    // Clear entry flag so we land on cover
    await page.goto(baseUrl, { waitUntil: 'networkidle2' });
    await clearSession();
    await page.reload({ waitUntil: 'networkidle2' });

    // Cover 1366x768
    await page.setViewport({ width: 1366, height: 768 });
    await page.reload({ waitUntil: 'networkidle2' });
    await page.screenshot({ path: 'C:\\tmp\\evrag-cover-1366.png' });
    console.log('Saved cover 1366');

    // Cover 1920x1080
    await page.setViewport({ width: 1920, height: 1080 });
    await page.screenshot({ path: 'C:\\tmp\\evrag-cover-1920.png' });
    console.log('Saved cover 1920');

    // Cover 1024x768
    await page.setViewport({ width: 1024, height: 768 });
    await page.screenshot({ path: 'C:\\tmp\\evrag-cover-1024.png' });
    console.log('Saved cover 1024');

    /* ---- Smoke existing routes ---- */
    // Enter the app
    await page.setViewport({ width: 1366, height: 768 });
    const enterBtn = await page.$('button.cover-btn-primary');
    if (enterBtn) {
      await enterBtn.click();
      await new Promise(r => setTimeout(r, 600));
    }

    // Home
    await page.screenshot({ path: 'C:\\tmp\\evrag-final-home-1366.png' });
    console.log('Saved home');

    // New Document
    await page.goto(baseUrl + '/yeni-evrak', { waitUntil: 'networkidle2' });
    await page.screenshot({ path: 'C:\\tmp\\evrag-final-new-document-1366.png' });
    console.log('Saved new-document');

    // Workspace
    const docId = '193kanun';
    await page.goto(baseUrl + '/evrak/' + docId, { waitUntil: 'networkidle2' });
    await page.screenshot({ path: 'C:\\tmp\\evrag-final-workspace-hidden-1366.png' });
    console.log('Saved workspace hidden');

    // Show document
    const btns = await page.$$('button');
    for (const btn of btns) {
      const text = await page.evaluate(el => el.textContent, btn);
      if (text && text.includes('Belgeyi Göster')) { await btn.click(); await new Promise(r => setTimeout(r, 800)); break; }
    }
    await page.screenshot({ path: 'C:\\tmp\\evrag-final-workspace-a4-1366.png' });
    console.log('Saved workspace A4');

    // AI Operations
    await page.goto(baseUrl + '/ai-operasyon', { waitUntil: 'networkidle2' });
    await page.screenshot({ path: 'C:\\tmp\\evrag-final-ai-operations-1366.png' });
    console.log('Saved AI ops');

  } catch (err) {
    console.error('Error:', err);
  } finally {
    await browser.close();
  }
})();
