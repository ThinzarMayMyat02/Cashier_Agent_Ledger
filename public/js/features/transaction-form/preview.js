// Display-only fee and movement previews. The server validates final amounts.
import { $, money } from "../../core/format.js";
import { parseMoney, formatMoneyInput } from "../../components/money-input.js";

export function calculateSuggestedFee(entryType, amount) {
  if (entryType === "cash_in") return Math.ceil(amount / 100000) * 100;
  if (amount <= 10000) return 100;
  if (amount <= 50000) return 300;
  if (amount < 2000000) return Math.max(1, Math.floor(amount / 100000)) * 500;
  return Math.floor((amount + 125) / 250);
}

export function bindTransactionPreview(receiptDraft, walletAccounts) {
  const updatePreview = (resetCollectedFee) => {
    const entryType = $("#f_type").value,
      principal = parseMoney($("#f_amount").value),
      suggestedFee =
        principal > 0 ? calculateSuggestedFee(entryType, principal) : 0;
    if (resetCollectedFee) {
      $("#f_fee").value = suggestedFee;
      formatMoneyInput($("#f_fee"));
    }

    $("#feevalue").textContent = money(suggestedFee) + " MMK";
    $("#f_fee_mode").disabled = entryType === "cash_in";

    if (!entryType) {
      $("#cashpreview").textContent =
        "Choose Cash In or Cash Out after checking the shop wallet movement.";
      return;
    }
    const walletDelta =
      (entryType === "cash_in" ? -principal : principal) +
      (receiptDraft?.receipt_format === "wave_channel"
        ? parseMoney($("#f_provider_commission").value) -
          parseMoney($("#f_provider_fee").value)
        : 0);
    const cashDelta =
      entryType === "cash_in"
        ? principal + parseMoney($("#f_fee").value)
        : parseMoney($("#f_fee").value) - principal;
    const account = walletAccounts.find(
      (account) => String(account.id) === $("#f_account_id").value,
    );
    $("#cashpreview").textContent =
      "Wallet " +
      (walletDelta >= 0 ? "+" : "−") +
      money(Math.abs(walletDelta)) +
      " MMK · Cash " +
      (cashDelta >= 0 ? "+" : "−") +
      money(Math.abs(cashDelta)) +
      " MMK" +
      (account
        ? " · Wallet balance " +
          money(account.balance) +
          " → " +
          money(account.balance + walletDelta) +
          " MMK"
        : "");
  };
  $("#f_amount").oninput = () => updatePreview(true);
  $("#f_type").onchange = () => updatePreview(true);
  $("#f_account_id").onchange = () => updatePreview(true);
  $("#f_fee").oninput = () => updatePreview(false);
  $("#f_fee_mode").onchange = () => updatePreview(false);
  if (receiptDraft?.receipt_format === "wave_channel") {
    $("#f_provider_commission").oninput = () => updatePreview(false);
    $("#f_provider_fee").oninput = () => updatePreview(false);
  }

  updatePreview(true);
}
