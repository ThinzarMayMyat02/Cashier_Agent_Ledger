// Daily reconciliation form and saved counts.
import { toast, heading } from "../components/common.js";

import { formatMoneyInputs, parseMoney } from "../components/money-input.js";
import { api } from "../core/api.js";
import { $, money, esc } from "../core/format.js";
import { store } from "../core/store.js";

import { mountClosingExport } from "./reports.js";
import { render } from "../shell.js";

export function closing() {
  const sources = [
    { id: "cash", name: "Shop cash", balance: store.data.cash },
    ...store.data.accounts,
  ];
  $("#view").innerHTML =
    heading(
      "Daily closing",
      "All counts must match. Closing locks financial writes until the next Myanmar business day.",
      '<div id="closing-export" class="closing-export" role="group" aria-label="Export daily report"></div>',
    ) +
    `<div class="columns">
<section class="card">
<div class="sectionhead">
<h2>Count your cash & wallets</h2>
<span class="muted">MMK</span>
</div>
<form id="closingform">${sources
      .map(
        (a) => `<div class="closingrow">
<div>
<b>${esc(a.name)}</b>
<small>Expected: ${money(a.balance)} MMK</small>
</div>
<input type="text" data-money inputmode="numeric" required min="0" max="100000000000" name="${a.id}" placeholder="Actual count" aria-label="Counted balance for ${esc(a.name)}">
</div>`,
      )
      .join("")}<div class="field" style="margin-top:20px">
<label for="closingnote">Closing note</label>
<textarea id="closingnote" placeholder="Closing note…">
</textarea>
</div>
<div id="difference" class="feeinfo">Enter actual balances to see differences.</div>
<div class="error" role="alert">
</div>
<button class="primary">Close this day</button>
</form>
</section>
<section class="card">
<h2>Recent closings</h2>
<div class="closinglist">${
      store.data.closings.length
        ? store.data.closings
            .map((c) => {
              let s = JSON.parse(c.snapshot);
              let diffs = Object.keys(s.expected).filter(
                (k) => s.counted[k] !== s.expected[k],
              );
              return `<div class="infobox" style="margin:0">
<h3>${new Date(c.created).toLocaleString()}</h3>
<p>Recorded by ${esc(c.staff_name)}</p>
<p>${diffs.length ? diffs.map((k) => esc(k === "cash" ? "Shop cash" : store.data.accounts.find((a) => String(a.id) === k)?.name || "Account") + ": " + money(s.counted[k] - s.expected[k]) + " MMK difference").join("<br>") : "All balances matched"}</p>
<p data-no-i18n>${esc(s.note)}</p>
</div>`;
            })
            .join("")
        : '<div class="empty">No closing counts yet.</div>'
    }</div>
</section>
</div>`;
  mountClosingExport();
  formatMoneyInputs($("#closingform"));
  $("#closingform").oninput = () => {
    let vals = Object.fromEntries(new FormData($("#closingform")));
    $("#difference").textContent =
      sources
        .filter((a) => vals[a.id] !== "")
        .map(
          (a) =>
            a.name + ": " + money(parseMoney(vals[a.id]) - a.balance) + " MMK",
        )
        .join(" · ") || "Enter actual balances.";
  };
  $("#closingform").onsubmit = async (e) => {
    e.preventDefault();
    let b = e.target.querySelector("button");
    b.disabled = true;
    try {
      store.data = await api("closing", {
        counts: Object.fromEntries(
          [...new FormData(e.target)].map(([k, v]) => [k, parseMoney(v)]),
        ),
        note: $("#closingnote").value,
      });
      render();
      toast("Business day closed");
    } catch (err) {
      $("#closingform .error").textContent = err.message;
      b.disabled = false;
    }
  };
}
