/**
 * Graba un video (webm) de la app haciendo la tarea completa del brief:
 * clima -> evento al aire libre -> aviso por email. Pensado para correr
 * contra `backend/scripts/demo_server.py` (LLM simulado, sin gastar API
 * key real) + el frontend normal (`npm run dev`), pero funciona igual
 * contra un backend con LLM real si tenés paciencia con la latencia.
 *
 * Uso:
 *   cd backend && python -m scripts.demo_server        # terminal 1
 *   cd frontend && VITE_API_URL=http://localhost:8010 npm run dev   # terminal 2
 *   cd demo && npm install && node record.js            # terminal 3
 *
 * El video queda en demo/videos/*.webm.
 */
const { chromium } = require("playwright");
const path = require("path");

const VIDEO_DIR = path.join(__dirname, "videos");
const APP_URL = process.env.DEMO_APP_URL || "http://localhost:5173";
const TASK_MESSAGE =
  process.env.DEMO_TASK_MESSAGE ||
  "Revisá el clima de mañana y si tenemos un evento al aire libre ese día en la agenda, avisá al equipo por email.";

// En algunos sandboxes (incl. este) Playwright no puede descargar su propio
// Chromium y hay que apuntarlo a un binario preinstalado. Si no está seteado
// se usa el que trae Playwright por defecto.
const EXECUTABLE_PATH = process.env.DEMO_CHROMIUM_PATH || undefined;

async function waitForTraceSteps(page, expectedCount) {
  await page.waitForFunction(
    (n) => document.querySelectorAll(".trace-step").length >= n,
    expectedCount,
    { timeout: 20000 }
  );
}

async function waitForTraceStepsPaced(page, totalSteps, pauseMs) {
  for (let n = 1; n <= totalSteps; n++) {
    await waitForTraceSteps(page, n);
    await page.waitForTimeout(pauseMs);
  }
}

async function main() {
  const browser = await chromium.launch({
    executablePath: EXECUTABLE_PATH,
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    recordVideo: { dir: VIDEO_DIR, size: { width: 1280, height: 800 } },
  });

  const page = await context.newPage();

  await page.goto(APP_URL, { waitUntil: "networkidle" });
  // Pausa inicial para que se alcance a ver la pantalla vacía antes de escribir.
  await page.waitForTimeout(2500);

  const input = page.locator(".composer input");
  await input.click();
  await input.pressSequentially(TASK_MESSAGE, { delay: 45 });
  await page.waitForTimeout(1200);

  await page.locator(".composer button[type=submit]").click();

  // 3 acciones + 3 observaciones = 6 pasos en la traza. Si el backend tiene
  // el delay artificial de scripts/demo_server.py, cada uno va apareciendo
  // de a poco; el pequeño respiro extra acá es solo estético.
  await waitForTraceStepsPaced(page, 6, 900);

  await page.waitForFunction(
    () => {
      const bubbles = document.querySelectorAll(".bubble.assistant");
      return bubbles.length > 0 && bubbles[bubbles.length - 1].innerText.length > 10;
    },
    { timeout: 20000 }
  );

  // Dejamos unos segundos con todo visible en pantalla antes de cerrar.
  await page.waitForTimeout(6000);

  await context.close();
  await browser.close();

  console.log("Video guardado en:", VIDEO_DIR);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
