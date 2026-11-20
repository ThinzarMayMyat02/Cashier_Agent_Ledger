// History filters and CSV export.
import { heading, rows } from "../components/common.js";

import { $, esc, today, day, title, money } from "../core/format.js";
import { store } from "../core/store.js";

export function history() {
  $("#view").innerHTML =
    heading(
      "Transactions",
      "A complete record of your shop’s money movements.",
      '<button onclick="importReceipt()">Import receipt photo</button><button class="primary" onclick="entryForm(\'cash_in\')">＋ New transaction</button>',
    ) +
    `<section class="card">
<div class="filters">
<input id="search" placeholder="Search phone, customer or note…" aria-label="Search transactions">
<select id="typefilter" aria-label="Filter type">
<option value="">All types</option>${["cash_in", "cash_out", "expense", "funds_in", "funds_out", "reversal"].map((t) => `<option value="${t}">${title(t)}</option>`).join("")}</select>
<select id="walletfilter" aria-label="Filter account">
<option value="">All accounts</option>${store.data.accounts.map((a) => `<option value="${a.id}">${esc(a.name)}</option>`).join("")}</select>
<input id="datefilter" type="date" aria-label="Filter date">
<select id="stafffilter" aria-label="Filter staff">
<option value="">All staff</option>${[...new Set(store.data.entries.map((e) => e.staff_name))].map((n) => `<option>${esc(n)}</option>`).join("")}</select>
</div>
<div id="records">
</div>
</section>`;
  const filter = () => {
    $("#records").innerHTML = rows(historyEntries());
  };
  ["search", "typefilter", "walletfilter", "datefilter", "stafffilter"].forEach(
    (id) => ($("#" + id).oninput = filter),
  );
  filter();
}

function historyEntries() {
  if (!$("#search")) return store.data.entries;
  const q = $("#search").value.toLowerCase();
  return store.data.entries.filter(
    (e) =>
      (!q ||
        (
          (e.phone || e.customer_phone_masked || "") +
          " " +
          e.customer +
          " " +
          e.note +
          " " +
          (e.provider_transaction_id || "")
        )
          .toLowerCase()
          .includes(q)) &&
      (!$("#typefilter").value || e.type === $("#typefilter").value) &&
      (!$("#walletfilter").value ||
        String(e.account_id) === $("#walletfilter").value) &&
      (!$("#datefilter").value ||
        (e.business_date || day(e.created)) === $("#datefilter").value) &&
      (!$("#stafffilter").value || e.staff_name === $("#stafffilter").value),
  );
}
