// Photo extraction into a reviewable transaction form.
import { field, select, openForm } from "../components/forms.js";
import { api } from "../core/api.js";
import { $ } from "../core/format.js";
import { entryForm } from "./transactions.js";

export function importReceipt() {
  const controller = new AbortController();
  let cancelled = false;
  let readyForReview = false;
  let reader;

  openForm(
    "Import receipt photo",
    select(
      "Receipt provider",
      "provider",
      '<option value="KBZPay">KBZPay</option><option value="WavePay">WavePay</option>',
    ) +
      field(
        "Receipt image (PNG or JPEG, up to 5 MB)",
        "image",
        "file",
        "",
        'required accept="image/png,image/jpeg"',
      ) +
      '<p>Read the receipt, then check and confirm the transaction form.</p><div id="importstatus" role="status"></div>',
    async (d) => {
      const file = $("#f_image").files[0];
      if (!file || file.size > 5 * 1024 * 1024)
        throw Error("Choose a PNG or JPEG image up to 5 MB");
      $("#importstatus").textContent = "Reading receipt…";
      let image = await new Promise((resolve, reject) => {
        reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(",")[1]);
        reader.onabort = () =>
          reject(new DOMException("Cancelled", "AbortError"));
        reader.onerror = () => reject(Error("Could not read image"));
        reader.readAsDataURL(file);
      });
      let extraction;
      try {
        extraction = await api(
          "receipt/extract",
          { provider: d.provider, image },
          controller.signal,
        );
      } finally {
        image = "";
        reader.onload = reader.onerror = reader.onabort = null;
        reader = null;
      }
      if (cancelled) return false;
      extraction.previewUrl = URL.createObjectURL(file);
      readyForReview = true;
      // Wait for the upload close event before attaching review cleanup handlers.
      $("#modal").addEventListener(
        "close",
        () => {
          setTimeout(() => entryForm("cash_in", extraction), 0);
        },
        { once: true },
      );
    },
    { successMessage: null },
  );
  $("#save").textContent = "Read receipt";
  const uploadForm = $("#form");
  $("#modal").addEventListener(
    "close",
    () => {
      if (!readyForReview) {
        cancelled = true;
        controller.abort();
        if (reader?.readyState === FileReader.LOADING) reader.abort();
      }
      uploadForm.reset();
      uploadForm.remove();
    },
    { once: true },
  );
}
