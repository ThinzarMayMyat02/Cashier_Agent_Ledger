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
      "Choose how to save your closing. Saving locks financial writes until the next Myanmar business day.",
      '<div id="closing-export" class="closing-export" role="group" aria-label="Export daily report"></div>',
    ) +
    `<div class="columns">
<section class="card">
<div class="sectionhead closing-count-heading">
<h2>Count your cash & wallets</h2>
<div class="closing-mode-heading">
<label class="closing-mode-control"><input type="checkbox" role="switch" id="closing-allow-variance" form="closingform" aria-label="Save differences with a note" aria-describedby="closing-mode-label"></label>
<p id="closing-mode-label" class="muted">Save only when balances match</p>
</div>
</div>
<form id="closingform">
${sources
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
<textarea id="closingnote" maxlength="500" placeholder="Closing note…">
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
<label for="closing-history-date">Closing date</label>
<input type="date" id="closing-history-date">
<div id="closing-history-list" class="closing-history-list" aria-live="polite"></div>
<button type="button" id="closing-history-more" hidden>Load more</button>
<p id="closing-history-status" role="status"></p>
</section>
</div>`;
  mountClosingHistory();
  mountClosingExport();
  formatMoneyInputs($("#closingform"));
  const updateClosingPreview = () => {
    const hasDifference = sources.some((source) => {
      const input = $('#closingform input[name="' + source.id + '"]');
      return input.value !== "" && parseMoney(input.value) !== source.balance;
    });
    const allowVariance = $("#closing-allow-variance").checked;
    $("#closing-mode-label").textContent = allowVariance
      ? "Save differences with a note"
      : "Save only when balances match";
    $("#closingnote").required = allowVariance && hasDifference;
    $("#difference").textContent =
      sources
        .filter(
          (source) =>
            $('#closingform input[name="' + source.id + '"]').value !== "",
        )
        .map(
          (source) =>
            source.name +
            ": " +
            money(
              parseMoney(
                $('#closingform input[name="' + source.id + '"]').value,
              ) - source.balance,
            ) +
            " MMK",
        )
        .join(" · ") || "Enter actual balances.";
  };
  $("#closingform").oninput = updateClosingPreview;
  $("#closing-allow-variance").onchange = updateClosingPreview;
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
        closing_mode: $("#closing-allow-variance").checked
          ? "allow_variance"
          : "strict",
      });
      render();
      toast("Business day closed");
    } catch (err) {
      $("#closingform .error").textContent = err.message;
      b.disabled = false;
    }
  };
}

function mountClosingHistory() {
  const dateInput = $("#closing-history-date");
  const list = $("#closing-history-list");
  const more = $("#closing-history-more");
  const status = $("#closing-history-status");
  let revision = 0;
  let page = 0;
  let records = [];
  async function fetchPage(reset) {
    const request = ++revision;
    const nextPage = reset ? 1 : page + 1;
    if (reset) {
      records = [];
      page = 0;
      more.hidden = true;
      list.replaceChildren();
    }
    more.disabled = true;
    status.textContent = "Loading report…";
    try {
      const result = await api(
        "closings?" +
          new URLSearchParams({
            date: dateInput.value,
            page: String(nextPage),
          }),
      );
      if (request !== revision || !list.isConnected) return;
      page = nextPage;
      records.push(...result.records);
      list.innerHTML = records
        .map(
          (record, index) =>
            `<button type="button" class="closing-history-row" data-record="${index}"><span data-no-i18n>${esc(record.closing_date)}</span><span>View closing record</span><span class="badge">${closingStatus(JSON.parse(record.snapshot))}</span><small data-no-i18n>${esc(record.staff_name)}</small></button>`,
        )
        .join("");
      more.hidden = records.length >= result.total;
      status.textContent = result.total
        ? ""
        : "No closing counts for this date.";
    } catch (error) {
      if (request === revision && status.isConnected)
        status.textContent = error.message;
    } finally {
      if (request === revision) more.disabled = false;
    }
  }
  dateInput.onchange = () => fetchPage(true);
  more.onclick = () => fetchPage(false);
  list.onclick = (event) => {
    const button = event.target.closest("[data-record]");
    if (button) showClosingRecord(records[Number(button.dataset.record)]);
  };
  fetchPage(true);
}

function showClosingRecord(record) {
  const snapshot = JSON.parse(record.snapshot);
  const recordedAt = new Date(record.created).toLocaleString("en-GB", {
    timeZone: "Asia/Yangon",
  });
  const rows = Object.entries(snapshot.expected)
    .map(([id, expected]) => {
      const name =
        id === "cash"
          ? "Shop cash"
          : store.data.accounts.find((account) => String(account.id) === id)
              ?.name || `Account ${id}`;
      const counted = snapshot.counted[id];
      return `<tr><td data-no-i18n>${esc(name)}</td><td>${money(expected)}</td><td>${counted == null ? "—" : money(counted)}</td><td>${counted == null ? "—" : money(counted - expected)}</td></tr>`;
    })
    .join("");
  const modal = $("#modal");
  modal.classList.add("closing-record-modal");
  modal.innerHTML = `<div class="sectionhead"><h2>Closing record</h2><button type="button" class="quiet" aria-label="Close">✕</button></div>
    <p class="badge">${closingStatus(snapshot)}</p>
    <p data-no-i18n>${esc(record.closing_date)} · ${esc(recordedAt)} · ${esc(record.staff_name)}</p>
    <div class="tablewrap"><table><thead><tr><th>Money source</th><th>Expected balance</th><th>Counted balance</th><th>Difference</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p data-no-i18n>${esc(snapshot.note || "—")}</p>`;
  modal.querySelector("button").onclick = () => modal.close();
  modal.addEventListener(
    "close",
    () => modal.classList.remove("closing-record-modal"),
    { once: true },
  );
  modal.showModal();
}

function closingStatus(snapshot) {
  return Object.keys(snapshot.expected).every(
    (key) => snapshot.expected[key] === snapshot.counted[key],
  )
    ? "Matched"
    : "With differences";
}
