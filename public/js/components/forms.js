// Reusable modal and input controls.
import { toast } from "./common.js";
import { $, esc, money } from "../core/format.js";
import { formatMoneyInputs, plainMoneyFormData } from "./money-input.js";
import { render } from "../shell.js";

export function field(label, name, type = "text", value = "", extra = "") {
  const monetary = type === "number";
  const displayValue = monetary && value !== "" ? money(value) : value;
  return `<div class="field">
<label for="f_${name}">${label}</label>
<input id="f_${name}" name="${name}" type="${monetary ? "text" : type}" value="${esc(displayValue)}" ${monetary ? 'data-money inputmode="numeric"' : ""} ${extra}>
</div>`;
}

export function select(label, name, options) {
  return `<div class="field">
<label for="f_${name}">${label}</label>
<select id="f_${name}" name="${name}">${options}</select>
</div>`;
}

export function openForm(
  title,
  body,
  onSave,
  { successMessage = "Saved successfully" } = {},
) {
  const m = $("#modal");
  m.innerHTML = `<div class="sectionhead">
<h2>${title}</h2>
<button class="quiet" onclick="document.querySelector('#modal').close()" aria-label="Close">✕</button>
</div>
<form id="form">${body}<div class="error" role="alert">
</div>
<div class="actions">
<button type="button" onclick="document.querySelector('#modal').close()">Cancel</button>
<button class="primary" id="save">Confirm and save</button>
</div>
</form>`;
  formatMoneyInputs(m);
  m.showModal();
  $("#form").onsubmit = async (e) => {
    e.preventDefault();
    $("#save").disabled = true;
    try {
      const result = await onSave(plainMoneyFormData(e.target));
      if (result === false || !m.open || !e.target.isConnected) return;
      m.close();
      render();
      if (successMessage) toast(successMessage);
    } catch (err) {
      if (!m.open || !e.target.isConnected) return;
      $("#form .error").textContent = err.message;
      $("#save").disabled = false;
    }
  };
}
