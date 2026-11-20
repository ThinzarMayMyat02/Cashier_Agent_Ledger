// Navigation shell and refreshing the server snapshot.
import { toast } from "./components/common.js";
import { api } from "./core/api.js";
import { $, esc } from "./core/format.js";
import { store } from "./core/store.js";
import { accounts } from "./features/accounts.js";

import { closing } from "./features/closing.js";
import { expenses } from "./features/expenses.js";
import { history } from "./features/history.js";
import { overview } from "./features/overview.js";
import { reports } from "./features/reports.js";
import { team } from "./features/team.js";

const pages = { overview, history, reports, accounts, expenses, closing, team };

function allowedPage(page) {
  if (!Object.hasOwn(pages, page)) return "overview";
  if (page === "team" && store.data?.user.role !== "owner") return "overview";
  return page;
}

function pageFromAddress() {
  return window.location.hash.slice(1) || "overview";
}

export function render() {
  const nav = [
    ["overview", "◫", "Overview"],
    ["history", "⇄", "Transactions"],
    ["reports", "◫", "Daily summary"],
    ["accounts", "▣", "Wallet accounts"],
    ["expenses", "↗", "Expenses"],
    ["closing", "✓", "Daily closing"],
    ...(store.data.user.role === "owner" ? [["team", "♙", "Team"]] : []),
  ];
  store.page = allowedPage(store.page);
  $("#app").innerHTML = `<div class="shell">
<aside class="sidebar">
<div class="brand">
<span class="mark">↗</span>counter<span style="color:#96aa9c">.</span>
</div>
<div class="subbrand">AGENT SHOP LEDGER</div>
<div class="navlabel">WORKSPACE</div>
<nav class="nav" aria-label="Workspace navigation">${nav
    .map(
      ([
        id,
        i,
        t,
      ]) => `<button type="button" aria-label="${t}" aria-current="${store.page === id ? "page" : "false"}" data-nav="${id}" class="${store.page === id ? "active" : ""}">
<span>${i}</span>${t}</button>`,
    )
    .join("")}</nav>
<div class="sidebottom">
<div class="store">
<b>Your shop, in balance.</b>
<br>
<span class="muted">KBZPay & WavePay ledger</span>
</div>
<div class="userrow">
<span class="avatar">${esc(store.data.user.name[0].toUpperCase())}</span>
<div>${esc(store.data.user.name)}<small>${esc(store.data.user.role)}</small>
</div>
<button class="quiet" onclick="logout()" aria-label="Sign out">↪</button>
</div>
</div>
</aside>
<main class="main">
<header class="topbar">
<span>Workspace <span class="muted"> / ${nav.find((x) => x[0] === store.page)?.[2] || "Overview"}</span>
</span>
<div class="actions">
<span class="status">
<i class="dot">
</i> ${esc(store.data.user.name)}</span>
<button class="quiet" onclick="load()" aria-label="Refresh balances">↻</button>
<button class="quiet" onclick="logout()" aria-label="Sign out">↪</button>
</div>
</header>
<div class="content" id="view">
</div>
<div class="footer">COUNTER · Your daily money flow, clearly recorded. · All amounts in MMK</div>
</main>
</div>`;
  pages[store.page]();
  // Keep the selected item visible after rebuilding a narrow-screen navigation bar.
  const selected = document.querySelector(
    '.nav [data-nav="' + store.page + '"]',
  );
  selected?.scrollIntoView({ block: "nearest", inline: "nearest" });
}

export function go(page, updateAddress = true) {
  if (!store.data) return;
  const next = allowedPage(page);
  const dialog = document.querySelector("#modal");
  if (dialog?.open) dialog.close();
  store.page = next;
  if (updateAddress && window.location.hash !== "#" + next) {
    window.history.pushState(null, "", "#" + next);
  }
  render();
}

document.addEventListener("click", (event) => {
  const button = event.target.closest?.(".nav [data-nav]");
  if (!button || button.disabled) return;
  event.preventDefault();
  go(button.dataset.nav);
});

function restoreNavigation() {
  if (store.data && store.page !== allowedPage(pageFromAddress())) {
    go(pageFromAddress(), false);
  }
}
window.addEventListener("popstate", restoreNavigation);
window.addEventListener("hashchange", restoreNavigation);

export async function load() {
  try {
    store.data = await api("state");
    if (store.data) {
      store.page = allowedPage(pageFromAddress());
      render();
    }
  } catch (e) {
    toast(e.message);
  }
}
