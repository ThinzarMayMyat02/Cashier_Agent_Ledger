// Field markup only. Keep input names aligned with the REST command contract.
import { field, select } from "../../components/forms.js";
import { money, esc } from "../../core/format.js";

export function renderTransactionFields({
  entryType,
  isCustomerTransaction,
  receiptDraft,
  walletAccounts,
  customerSuggestions,
}) {
  const walletOptions =
    (isCustomerTransaction ? "" : '<option value="">Shop cash</option>') +
    walletAccounts
      .filter((account) => account.active)
      .map(
        (account) =>
          `<option value="${account.id}">${esc(account.name)} · ${money(account.balance)} MMK</option>`,
      )
      .join("");
  return (
    (receiptDraft
      ? '<div class="infobox"><img class="receipt-preview" alt="Receipt preview"></div>'
      : "") +
    (isCustomerTransaction
      ? select(
          "Transaction type",
          "type",
          '<option value="cash_in">Cash in</option><option value="cash_out">Cash out</option>',
        )
      : "") +
    select(
      isCustomerTransaction ? "Wallet account" : "Money source",
      "account_id",
      walletOptions,
    ) +
    (isCustomerTransaction
      ? field(
          "Customer phone (optional)",
          "phone",
          "tel",
          "",
          'list="customers"',
        ) +
        field(
          "Customer name",
          "customer",
          "text",
          "",
          'required maxlength="100" pattern=".*\\S.*"',
        ) +
        `<datalist id="customers">${customerSuggestions.map((customer) => `<option value="${esc(customer.phone)}">${esc(customer.customer)}</option>`).join("")}</datalist>`
      : "") +
    (isCustomerTransaction
      ? field(
          "Provider transaction ID (optional)",
          "provider_transaction_id",
          "text",
          receiptDraft?.provider_transaction_id || "",
          'maxlength="80"',
        ) +
        field(
          "Receipt time (optional)",
          "receipt_time",
          "text",
          receiptDraft?.receipt_time || "",
          'maxlength="80"',
        )
      : "") +
    field(
      receiptDraft?.receipt_format === "wave_channel"
        ? "Customer amount · MMK"
        : receiptDraft
          ? "Total amount · MMK"
          : "Amount · MMK",
      "amount",
      "number",
      "",
      'required min="1" max="100000000000" step="1" inputmode="numeric"',
    ) +
    (receiptDraft?.receipt_format === "wave_channel"
      ? field(
          "Provider commission · MMK",
          "provider_commission",
          "number",
          receiptDraft.provider_commission ?? 0,
          'required min="0" step="1"',
        ) +
        field(
          "Provider fee · MMK",
          "provider_fee",
          "number",
          receiptDraft.provider_fee ?? 0,
          'required min="0" step="1"',
        ) +
        field(
          "Receipt wallet movement · MMK",
          "receipt_wallet_delta",
          "text",
          money(receiptDraft.receipt_wallet_delta ?? 0),
          "readonly",
        )
      : "") +
    (receiptDraft && receiptDraft.masked_phone
      ? field(
          "Masked phone from receipt",
          "masked_phone",
          "text",
          receiptDraft.masked_phone,
          "readonly data-no-i18n",
        )
      : "") +
    (isCustomerTransaction
      ? '<div class="feeinfo">Suggested fee <b id="feevalue">0 MMK</b></div>' +
        field(
          "Collected fee · MMK (editable)",
          "fee",
          "number",
          0,
          'required min="0" step="1"',
        ) +
        select(
          "Cash Out fee collection",
          "fee_mode",
          '<option value="separate">သက်သက်ပေးပါမယ်</option><option value="deduct" selected>တခါတည်းပေါင်းယူလိုက်ပါ</option>',
        ) +
        field("Reason for changing fee (optional)", "override_reason") +
        '<div class="feeinfo" id="cashpreview"></div>'
      : "") +
    field(
      entryType === "expense"
        ? "Expense category / description"
        : isCustomerTransaction
          ? "Note"
          : "Reason / source of funds",
      "note",
      "",
      "",
      isCustomerTransaction ? "" : "required",
    ) +
    (receiptDraft
      ? '<label class="receipt-confirm"><input type="checkbox" name="receipt_confirmed" checked required> <span>I checked this is the shop wallet receipt, amount, wallet and cash direction.</span></label>'
      : "")
  );
}
