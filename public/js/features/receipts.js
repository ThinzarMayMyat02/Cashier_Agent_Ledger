// Photo extraction into a reviewable transaction form.
import { field, select, openForm } from "../components/forms.js";
import { api } from "../core/api.js";
import { $ } from "../core/format.js";
import { entryForm } from "./transactions.js";

export function importReceipt() {
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
      const image = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(",")[1]);
        reader.onerror = () => reject(Error("Could not read image"));
        reader.readAsDataURL(file);
      });
      const draft = await api("receipt/extract", {
        provider: d.provider,
        image,
      });
      draft.previewUrl = URL.createObjectURL(file);
      // openForm closes the import modal after this callback returns.
      setTimeout(() => entryForm("cash_in", draft), 0);
    },
  );
  $("#save").textContent = "Read receipt";
}
