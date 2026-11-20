// Formatting helpers keep displayed values separate from financial calculations.
import { store } from "./store.js";

export function $(selector) {
  return document.querySelector(selector);
}

export function money(amount) {
  return new Intl.NumberFormat("en-US").format(amount || 0);
}

export function esc(value) {
  const entities = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  };
  return String(value ?? "").replace(
    /[&<>"']/g,
    (character) => entities[character],
  );
}

export function today() {
  return (
    store.data?.business_date ||
    new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Yangon" })
  );
}

export function day(timestamp) {
  return new Date(timestamp).toLocaleDateString("en-CA", {
    timeZone: "Asia/Yangon",
  });
}

export function title(entryType) {
  return (
    {
      cash_in: "Cash in",
      cash_out: "Cash out",
      expense: "Expense",
      funds_in: "Funds added",
      funds_out: "Funds removed",
      reversal: "Reversal",
    }[entryType] || entryType
  );
}
