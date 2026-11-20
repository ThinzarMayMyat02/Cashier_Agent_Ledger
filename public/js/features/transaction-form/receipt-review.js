// Populate an unposted receipt draft; the operator always selects the wallet.
import { $ } from "../../core/format.js";
import { formatMoneyInput } from "../../components/money-input.js";

export function populateReceiptFields(receiptDraft, walletAccounts) {
  $("#f_type").insertAdjacentHTML(
    "afterbegin",
    '<option value="">Choose Cash In or Cash Out</option>',
  );
  $("#f_type").value = receiptDraft.transaction_type || "";
  $("#f_type").required = true;
  $("#f_customer").value = receiptDraft.customer || "";
  $("#f_phone").value = receiptDraft.phone || "";
  $("#f_account_id").insertAdjacentHTML(
    "afterbegin",
    '<option value="">Choose wallet account</option>',
  );
  $("#f_account_id").value = "";
  $("#f_account_id").required = true;
  for (const option of $("#f_account_id").options) {
    const account = walletAccounts.find(
      (wallet) => String(wallet.id) === option.value,
    );
    if (
      account &&
      (account.provider.toLowerCase() !== receiptDraft.provider.toLowerCase() ||
        (receiptDraft.account_kind &&
          account.kind.toLowerCase() !==
            receiptDraft.account_kind.toLowerCase()))
    )
      option.disabled = true;
  }
  $("#f_amount").value = receiptDraft.amount || "";
  formatMoneyInput($("#f_amount"));
  $("#modal .receipt-preview").src = receiptDraft.previewUrl;
  $("#modal").addEventListener(
    "close",
    () => URL.revokeObjectURL(receiptDraft.previewUrl),
    { once: true },
  );
}
