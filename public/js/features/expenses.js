// Expense listing and totals.
import { heading, rows } from "../components/common.js";
import { $, money } from "../core/format.js";
import { store } from "../core/store.js";

export function expenses() {
  let e = store.data.entries.filter(
    (e) =>
      e.type === "expense" ||
      (e.reversal_of &&
        store.data.entries.find((r) => r.id === e.reversal_of)?.type ===
          "expense"),
  );
  $("#view").innerHTML =
    heading(
      "Shop expenses",
      "Record extra spending from cash or any wallet.",
      '<button class="primary" onclick="entryForm(\'expense\')">＋ Add expense</button>',
    ) +
    `<section class="card">
<div class="sectionhead">
<h2>Total expenses</h2>
<b>${money(e.filter((x) => !x.reversed || store.data.entries.some((r) => r.reversal_of === x.id)).reduce((n, x) => n + x.amount, 0))} MMK</b>
</div>${rows(e)}</section>`;
}
