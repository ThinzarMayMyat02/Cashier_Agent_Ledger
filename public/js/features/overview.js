// Daily dashboard and wallet balances.
import { heading, wallet, rows } from "../components/common.js";
import { $, money, today, day } from "../core/format.js";
import { store } from "../core/store.js";

export function overview() {
  const live = store.data.entries.filter(
      (e) =>
        e.reversed !== true ||
        store.data.entries.some((r) => r.reversal_of === e.id),
    ),
    daily = live.filter((e) => (e.business_date || day(e.created)) === today()),
    fees = daily.reduce((n, e) => n + e.fee, 0),
    wallets = store.data.accounts.filter((a) => a.active),
    total = store.data.accounts.reduce((n, a) => n + a.balance, 0);
  $("#view").innerHTML =
    heading(
      "Your shop at a glance",
      new Date(today() + "T12:00:00+06:30").toLocaleDateString("en-US", {
        timeZone: "Asia/Yangon",
        weekday: "long",
        month: "long",
        day: "numeric",
        year: "numeric",
      }),
      '<button onclick="importReceipt()">Import receipt photo</button><button class="primary" onclick="entryForm(\'cash_in\')">＋ New transaction</button>',
    ) +
    `<div class="stats">${[
      ["Shop cash", store.data.cash, "Available at the counter", "▤"],
      [
        "Wallet balance",
        total,
        store.data.accounts.length + " accounts combined",
        "▣",
      ],
      ["Today’s fees", fees, "Collected fees, net of reversals", "↗"],
      [
        "Provider commission",
        daily.reduce((sum, e) => sum + (e.provider_commission || 0), 0),
        "Provider commission",
        "↗",
      ],
      [
        "Today’s transactions",
        daily.filter((e) => ["cash_in", "cash_out"].includes(e.type)).length,
        "Cash in & cash out",
        "⇄",
      ],
    ]
      .map(
        ([l, v, f, i], idx) =>
          `<div class="card stat">
<div class="statlabel">${l}<span>${i}</span>
</div>
<div class="statvalue">${money(v)} ${idx < 4 ? "<small>MMK</small>" : ""}</div>
<div class="statfoot">${f}</div>
</div>`,
      )
      .join("")}</div>
<div class="columns">
<div>
<section class="card">
<div class="sectionhead">
<div>
<h2>Your wallet accounts</h2>
<p>Every account, one clear view.</p>
</div>
<button class="quiet" onclick="go('accounts')">Manage →</button>
</div>
<div class="walletlist">${wallets.map((a) => wallet(a)).join("")}</div>
</section>
<section class="card panelgap">
<div class="sectionhead">
<div>
<h2>Recent transactions</h2>
<p>The latest activity across your counter.</p>
</div>
<button class="quiet" onclick="go('history')">View all →</button>
</div>${rows(store.data.entries.slice(0, 6))}</section>
</div>
<aside class="rightpanel">
<section class="card">
<h2>Quick actions</h2>
<p style="font-size:12px;margin-top:5px">Keep the queue moving.</p>
<div class="quickgrid">
<button aria-label="Cash in" onclick="entryForm('cash_in')">
<b>↙</b>Cash in</button>
<button aria-label="Cash out" onclick="entryForm('cash_out')">
<b>↗</b>Cash out</button>
<button onclick="entryForm('expense')">
<b>−</b>Add expense</button>
<button onclick="go('closing')">
<b>✓</b>Close the day</button>
</div>
<div class="infobox">
<h3>A balanced day starts here</h3>
<p>${store.data.cash === 0 ? "Add your opening cash and wallet funds before recording transactions." : "Match your counted cash and wallet balances before closing the day."}</p>${store.data.user.role === "owner" ? '<button class="quiet" onclick="entryForm(\'funds_in\')">＋ Add funds →</button>' : ""}</div>
</section>
<section class="card panelgap">
<h2>Today’s money flow</h2>${[
      [
        "Cash in",
        daily
          .filter(
            (e) =>
              e.type === "cash_in" ||
              (e.reversal_of &&
                store.data.entries.find((r) => r.id === e.reversal_of)?.type ===
                  "cash_in"),
          )
          .reduce((n, e) => n + e.amount, 0),
      ],
      [
        "Cash out",
        daily
          .filter(
            (e) =>
              e.type === "cash_out" ||
              (e.reversal_of &&
                store.data.entries.find((r) => r.id === e.reversal_of)?.type ===
                  "cash_out"),
          )
          .reduce((n, e) => n + e.amount, 0),
      ],
      [
        "Expenses",
        daily
          .filter(
            (e) =>
              e.type === "expense" ||
              (e.reversal_of &&
                store.data.entries.find((r) => r.id === e.reversal_of)?.type ===
                  "expense"),
          )
          .reduce((n, e) => n + e.amount, 0),
      ],
    ]
      .map(
        ([l, v]) =>
          `<div class="activity">
<span>${l}</span>
<b>${money(v)} <small>MMK</small>
</b>
</div>`,
      )
      .join("")}</section>
</aside>
</div>`;
}
