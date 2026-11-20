// Account creation, editing and funding controls.
import { heading, wallet, toast } from "../components/common.js";
import { field, select, openForm } from "../components/forms.js";
import { api } from "../core/api.js";
import { $, esc } from "../core/format.js";
import { store } from "../core/store.js";

export function accounts() {
  const owner = store.data.user.role === "owner";
  const restricted = owner
    ? ""
    : 'disabled aria-disabled="true" data-owner-only';
  $("#view").innerHTML =
    heading(
      "Wallet accounts",
      owner
        ? "Create and customize the accounts your shop uses."
        : "View only. Only the owner can change wallet accounts or funds.",
      `<button ${restricted} onclick="entryForm('funds_in')">＋ Add funds</button>
       <button ${restricted} onclick="entryForm('funds_out')">− Remove funds</button>
       <button ${restricted} class="primary" onclick="accountForm()">＋ Add account</button>`,
    ) +
    `<div class="accountgrid">${store.data.accounts.map((a) => wallet(a, true)).join("")}</div>`;
}

export function accountForm(id) {
  if (store.data.user.role !== "owner") {
    toast("Owner access required");
    return;
  }
  const a = store.data.accounts.find((a) => a.id === id) || {};
  openForm(
    id ? "Edit wallet account" : "Add wallet account",
    field(
      "Account display name",
      "name",
      "text",
      a.name || "",
      'required maxlength="100"',
    ) +
      `<div class="formrow">${field("Provider", "provider", "text", a.provider || "KBZPay", 'required list="providers"')}${field("Account type", "kind", "text", a.kind || "Normal", 'required list="types"')}</div>
<datalist id="providers">
<option>KBZPay</option>
<option>WavePay</option>
</datalist>
<datalist id="types">${["Normal", "Merchant", "MMQR Business", "Channel", ...store.data.accounts.map((a) => a.kind)].map((t) => `<option>${esc(t)}</option>`).join("")}</datalist>` +
      field("Account phone (optional)", "phone", "tel", a.phone || "") +
      (id
        ? select(
            "Status",
            "active",
            `<option value="1" ${a.active ? "selected" : ""}>Active</option>
<option value="0" ${!a.active ? "selected" : ""}>Archived</option>`,
          )
        : field(
            "Opening wallet balance · MMK",
            "opening",
            "number",
            0,
            'required min="0" step="1"',
          )) +
      '<p style="font-size:12px">Provider and type are customizable. Editing an account preserves its transaction history. Use Add funds or Remove funds to change existing balances.</p>',
    async (d) => {
      d.id = id;
      d.active = d.active !== "0";
      store.data = await api("account", d);
    },
  );
}
