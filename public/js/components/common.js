// Shared cards, transaction tables and notifications.
import { $, money, esc, title } from "../core/format.js";
import { store } from "../core/store.js";

export function toast(t) {
  $("#toast").textContent = t;
  $("#toast").style.display = "block";
  setTimeout(() => ($("#toast").style.display = "none"), 4000);
}

export function heading(t, p, buttons = "") {
  return `<div class="heading">
<div>
<h1>${t}</h1>
<p>${p}</p>
</div>
<div class="actions">${buttons}</div>
</div>`;
}

export function wallet(a, edit = false) {
  return `<div class="wallet ${a.provider.toLowerCase().includes("wave") ? "wave" : ""} ${a.kind.includes("MMQR") ? "red" : ""} ${!a.active ? "inactive" : ""}">
<div class="logo">${a.provider.toLowerCase().includes("wave") ? "W" : "K"}</div>
<h3>${esc(a.name)}</h3>
<p>${esc(a.provider)} · ${esc(a.kind)}</p>${edit ? `<p>${esc(a.phone || "No phone added")} ${!a.active ? "· Archived" : ""}</p>` : ""}<strong>${money(a.balance)} <small>MMK</small>
</strong>${edit ? `<button ${store.data.user.role === "owner" ? "" : 'disabled aria-disabled="true" data-owner-only'} onclick="accountForm(${a.id})">Edit account</button>` : ""}</div>`;
}

export function rows(entries) {
  return entries.length
    ? `<div class="tablewrap">
<table>
<thead>
<tr>
<th>Customer / note</th>
<th>Type</th>
<th>Wallet account</th>
<th>Provider transaction ID</th>
<th>Amount</th>
<th>Fee</th>
<th>Provider commission</th>
<th>Provider fees</th>
<th>Cash movement</th>
<th>Wallet movement</th>
<th>Recorded by</th>
<th>
</th>
</tr>
</thead>
<tbody>${entries
        .map(
          (e) => `<tr class="${e.reversed ? "reversed" : ""}">
<td>
<b>${esc(e.customer || e.note || "—")}</b>
<small>${esc(e.phone || e.customer_phone_masked || "")} ${new Date(e.created).toLocaleString()}</small>${e.reversed ? `<small>Reversed: ${esc(e.reverse_note)}</small>` : ""}</td>
<td>
<span class="badge ${e.type === "cash_out" ? "out" : e.type === "expense" ? "expense" : ""}">${title(e.type)}</span>
</td>
<td>${esc(e.account_name || "Shop cash")}</td>
<td data-no-i18n>${esc(e.provider_transaction_id || "—")}</td>
<td>${money(e.amount)}</td>
<td>${e.fee_review_required ? "Review cash / fee" : money(e.fee)}</td>
<td>${money(e.provider_commission || 0)}</td>
<td>${money(e.provider_fee || 0)}</td>
<td>${e.cash_delta > 0 ? "+" : ""}${money(e.cash_delta)}</td>
<td>${e.wallet_delta > 0 ? "+" : ""}${money(e.wallet_delta)}</td>
<td>${esc(e.staff_name)}</td>
<td>${store.data.user.role === "owner" && !e.reversed && !e.reversal_of ? `<button class="quiet danger" onclick="reverseEntry('${esc(e.id)}')">Reverse</button>` : ""}</td>
</tr>`,
        )
        .join("")}</tbody>
</table>
</div>`
    : '<div class="empty">No records yet. Your next transaction starts here.</div>';
}
