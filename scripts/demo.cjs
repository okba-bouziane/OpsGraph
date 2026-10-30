// Records the demo video with puppeteer-core page.screencast(). Needs the stack up with the graph ingested.
const puppeteer = require("/Users/okba/Documents/portflio/job-search/outreach/node_modules/puppeteer-core");
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const OUT = __dirname + "/../docs/";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function ask(page, q, retriever) {
  await page.$eval("#q", (e) => (e.value = ""));
  await page.type("#q", q, { delay: 25 });
  await page.select("#retriever", retriever);
  await sleep(500);
  await page.click("button.primary");
  // The answer panel is already visible from the previous question, so wait for the request to start first.
  await page.waitForFunction(() => document.querySelector("button.primary").textContent !== "Ask", { timeout: 5000 }).catch(() => {});
  await page.waitForFunction(() => document.querySelector("#out") && document.querySelector("button.primary").textContent === "Ask", { timeout: 180000 });
  await sleep(7000);
}

(async () => {
  // HEADLESS=0 opens a visible window that fills the screen (maximized) and records at that size.
  const visible = process.env.HEADLESS === "0";
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: visible ? false : "new", defaultViewport: visible ? null : undefined, args: ["--no-sandbox", ...(visible ? ["--start-maximized", "--window-position=0,0", "--window-size=1512,982"] : [])] });
  const page = (await browser.pages())[0] || (await browser.newPage());
  if (!visible) await page.setViewport({ width: 1512, height: 982 });
  else {
    const cdp = await page.createCDPSession();
    const { windowId } = await cdp.send("Browser.getWindowForTarget");
    await cdp.send("Browser.setWindowBounds", { windowId, bounds: { windowState: "maximized" } });
    await sleep(1000);
  }
  await page.goto("http://localhost:8090/", { waitUntil: "networkidle0" });
  const rec = await page.screencast({ path: OUT + "demo.mp4" });
  await sleep(4000);
  await ask(page, "Who is the primary on-call engineer for checkout-api?", "auto");
  await ask(page, "SmsQueueBacklog fired at night: who is on call for the notifications worker?", "auto");
  await page.evaluate(() => window.scrollTo(0, 400));
  await sleep(3000);
  await page.evaluate(() => window.scrollTo(0, 0));
  await ask(page, "What breaks if main-db goes down?", "graph");
  // The screencast drops the last frames on stop, so nudge the page and hold the final answer for a while.
  for (let i = 0; i < 8; i++) {
    await page.evaluate((y) => window.scrollTo(0, y), i % 2);
    await sleep(1000);
  }
  await rec.stop();
  await browser.close();
})();
