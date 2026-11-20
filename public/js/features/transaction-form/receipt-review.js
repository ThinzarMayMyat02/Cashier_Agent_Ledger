// Populate temporary OCR fields; the operator always selects the wallet.
import { $ } from "../../core/format.js";
import { formatMoneyInput } from "../../components/money-input.js";

export function populateReceiptFields(receiptExtraction, walletAccounts) {
  $("#f_type").insertAdjacentHTML(
    "afterbegin",
    '<option value="">Choose Cash In or Cash Out</option>',
  );
  $("#f_type").value = receiptExtraction.transaction_type || "";
  $("#f_type").required = true;
  $("#f_customer").value = receiptExtraction.customer || "";
  $("#f_phone").value = receiptExtraction.phone || "";
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
      (account.provider.toLowerCase() !==
        receiptExtraction.provider.toLowerCase() ||
        (receiptExtraction.account_kind &&
          account.kind.toLowerCase() !==
            receiptExtraction.account_kind.toLowerCase()))
    )
      option.disabled = true;
  }
  $("#f_amount").value = receiptExtraction.amount || "";
  formatMoneyInput($("#f_amount"));
  $("#modal .receipt-preview").src = receiptExtraction.previewUrl;
  const reviewForm = $("#form");
  $("#modal").addEventListener(
    "close",
    () => {
      URL.revokeObjectURL(receiptExtraction.previewUrl);
      reviewForm.querySelector(".receipt-preview")?.removeAttribute("src");
      reviewForm.reset();
      reviewForm.remove();
      for (const key of Object.keys(receiptExtraction))
        delete receiptExtraction[key];
    },
    { once: true },
  );
}
