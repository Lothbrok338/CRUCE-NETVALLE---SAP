// Flujo de extremo a extremo con navegador real. Uso:
//   WEB_URL=http://localhost:3100 CRUCE=/ruta/CRUCE.xlsx SAP=/ruta/SAP.xlsx [PASSWORD=...] node web/e2e/smoke.cjs
// Requiere la API y la web levantadas. Con archivos reales, ajustar las cifras esperadas.
const { chromium } = require("playwright");
const fs = require("fs");
const assert = require("assert");

(async () => {
  const url = process.env.WEB_URL || "http://localhost:3000";
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    acceptDownloads: true,
    viewport: { width: 1400, height: 900 },
    ...(process.env.PASSWORD ? { httpCredentials: { username: "u", password: process.env.PASSWORD } } : {}),
  });
  const page = await ctx.newPage();
  const shots = process.env.SHOTS_DIR;
  const shot = (n) => shots && page.screenshot({ path: `${shots}/${n}.png`, fullPage: true });

  await page.goto(url);
  await page.getByTestId("entrada-archivos").setInputFiles([process.env.CRUCE, process.env.SAP]);
  await page.getByText("Clasificación automática").waitFor();
  assert.equal(await page.getByLabel(/Tipo de CRUCE/).inputValue(), "NETVALLE");
  assert.equal(await page.getByLabel(/Tipo de SAP/).inputValue(), "SAP");
  await shot("1-nuevo-control");

  await page.getByRole("button", { name: "Generar control" }).click();
  await page.waitForURL(/\/controles\/[0-9a-f]{32}$/);
  await page.getByText("Resultado del control").waitFor({ timeout: 30000 });
  const tarjetas = page.getByTestId("tarjeta");
  assert.equal(await tarjetas.count(), 6);
  const tonos = await tarjetas.evaluateAll((els) => els.map((e) => e.getAttribute("data-tono")));
  console.log("tonos:", tonos.join(","));
  await shot("2-resultado");

  const [descarga] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Descargar Excel" }).click(),
  ]);
  assert.equal(descarga.suggestedFilename(), "CONTROL_TRIBUTARIO_INTEGRAL_V3.xlsx");
  const ruta = await descarga.path();
  assert.ok(fs.statSync(ruta).size > 5000);
  assert.equal(fs.readFileSync(ruta).subarray(0, 2).toString(), "PK");

  await page.getByRole("link", { name: /Ver observaciones/ }).click();
  await page.getByTestId("total").filter({ hasText: "observación" }).waitFor();
  console.log("total:", await page.getByTestId("total").innerText());
  await page.getByLabel("Buscar").fill("2003");
  await page.getByTestId("total").filter({ hasText: /^1 observación/ }).waitFor();
  await page.getByLabel("Buscar").fill("");
  await page.getByLabel("Filtrar por PUNTO").selectOption("SFC103");
  await page.waitForTimeout(500);
  console.log("SFC103:", await page.getByTestId("total").innerText());
  await shot("3-observaciones");

  await page.goto(url + "/historial");
  await page.getByText("listo").first().waitFor();
  await shot("4-historial");
  await browser.close();
  console.log("E2E OK");
})().catch((e) => { console.error(e); process.exit(1); });
