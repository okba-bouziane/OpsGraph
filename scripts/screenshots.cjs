// README screenshots via puppeteer-core + local Chrome. Stack must be up and the graph ingested.
const puppeteer = require("/Users/okba/Documents/portflio/job-search/outreach/node_modules/puppeteer-core");
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const OUT = __dirname + "/../docs/screenshots/";
const Q = "main-db is running out of connections: who do I page first?";
const CYPHER = "MATCH p=(s:Service)-[:DEPENDS_ON]->(db:Service {id: 'SVC-MAINDB'}) MATCH o=(db)-[:OWNED_BY]->(t:Team)<-[:COVERS]-(r:Rota)<-[:ON_CALL]-(:Person) OPTIONAL MATCH i=(:Postmortem)-[:ROOT_CAUSE]->(db) RETURN p, o, i";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const BROWSER_URL = process.env.NEO4J_BROWSER || "http://localhost:7475";
const BOLT_URL = process.env.NEO4J_BOLT || "bolt://localhost:7688";
const EVAL_HTML = process.env.EVAL_HTML || "/tmp/lg_eval.html";

(async () => {
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new", args: ["--no-sandbox"] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1512, height: 982 });
  await page.goto("http://localhost:8090/", { waitUntil: "networkidle0" });
  await page.type("#q", Q);
  await page.select("#retriever", "graph");
  await page.click("button.primary");
  await page.waitForSelector("#out:not([hidden])", { timeout: 120000 });
  await sleep(4000);
  await page.screenshot({ path: OUT + "ui-graph-view.png" });

  const ev = await browser.newPage();
  await ev.setViewport({ width: 900, height: 1100 });
  await ev.goto("file://" + EVAL_HTML);
  await ev.screenshot({ path: OUT + "eval-report.png", fullPage: true });

  const n = await browser.newPage();
  await n.setViewport({ width: 1512, height: 982 });
  await n.goto(BROWSER_URL + "/browser/?connectURL=" + encodeURIComponent(BOLT_URL), { waitUntil: "networkidle2" });
  await sleep(3000);
  await n.evaluate((pass) => {
    const set = (el, v) => { const d = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value"); d.set.call(el, v); el.dispatchEvent(new Event("input", { bubbles: true })); };
    const inputs = [...document.querySelectorAll("input")];
    const user = inputs.find((i) => i.type === "text" && /user/i.test(i.name + i.id + (i.getAttribute("data-testid") || "")));
    const pw = inputs.find((i) => i.type === "password");
    if (user) set(user, "neo4j");
    if (pw) set(pw, pass);
  }, process.env.NEO4J_PASSWORD || "opsgraph-pass");
  await n.keyboard.press("Enter");
  await sleep(4000);
  await n.click(".cm-content, .monaco-editor, [data-testid=editor-wrapper]").catch(() => {});
  await n.keyboard.type(CYPHER);
  const clickText = (t) => n.evaluate((t) => { const b = [...document.querySelectorAll("button")].find((x) => x.textContent.trim() === t); if (b) b.click(); return !!b; }, t);
  await clickText("Dismiss");
  await sleep(500);
  await clickText("Run");
  await sleep(7000);
  await n.screenshot({ path: OUT + "neo4j-browser.png" });
  await browser.close();
})();
