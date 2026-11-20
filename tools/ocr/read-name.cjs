// Local OCR only. Both the WebAssembly engine and Myanmar model are local files.
const path = require("path");
const { createWorker, PSM } = require("tesseract.js");
(async () => {
  const worker = await createWorker("mya", 1, {
    langPath: path.resolve(__dirname, "../../counter/receipts/tessdata"),
    gzip: false,
    cacheMethod: "none",
  });
  try {
    await worker.setParameters({ tessedit_pageseg_mode: PSM.SINGLE_LINE });
    const { data } = await worker.recognize(process.argv[2]);
    process.stdout.write(JSON.stringify({ text: data.text, confidence: data.confidence }));
  } finally {
    await worker.terminate();
  }
})().catch(() => { process.exitCode = 1; });
