// Transaction form orchestration and explicit submission; no writes during preview.
import { toast } from "../components/common.js";
import { field, openForm } from "../components/forms.js";
import { api } from "../core/api.js";
import { $, title } from "../core/format.js";
import { store } from "../core/store.js";
import { renderTransactionFields } from "./transaction-form/template.js";
import { populateReceiptFields } from "./transaction-form/receipt-review.js";
import { bindTransactionPreview } from "./transaction-form/preview.js";

export function entryForm(entryType, receiptExtraction = null) {
  if (
    ["funds_in", "funds_out"].includes(entryType) &&
    store.data.user.role !== "owner"
  ) {
    toast("Owner access required");
    return;
  }
  const transactionId = crypto.randomUUID();
  const isCustomerTransaction = ["cash_in", "cash_out"].includes(entryType);
  const walletAccounts = store.data.accounts;
  const customerSuggestions = getCustomerSuggestions(store.data.entries);
  openForm(
    receiptExtraction ? "Imported wallet transaction" : title(entryType),
    renderTransactionFields({
      entryType,
      isCustomerTransaction,
      receiptExtraction,
      walletAccounts,
      customerSuggestions,
    }),
    async (formData) => {
      const command = prepareEntryCommand(
        formData,
        entryType,
        transactionId,
        receiptExtraction,
      );
      store.data = await api("entry", command);
    },
  );
  if (!isCustomerTransaction) return;

  $("#f_type").value = entryType;
  $("#f_phone").oninput = () => {
    const customer = customerSuggestions.find(
      (customer) => customer.phone === $("#f_phone").value,
    );
    if (customer) $("#f_customer").value = customer.customer;
  };
  if (receiptExtraction)
    populateReceiptFields(receiptExtraction, walletAccounts);
  bindTransactionPreview(receiptExtraction, walletAccounts);
}

function getCustomerSuggestions(entries) {
  return [
    ...new Map(
      entries
        .filter((entry) => entry.phone)
        .map((entry) => [entry.phone, entry])
        .reverse(),
    ).values(),
  ];
}

function prepareEntryCommand(
  formData,
  entryType,
  transactionId,
  receiptExtraction,
) {
  const isCustomerTransaction = ["cash_in", "cash_out"].includes(entryType);
  const command = {
    ...formData,
    id: transactionId,
    type: isCustomerTransaction ? formData.type : entryType,
    amount: Number(formData.amount),
  };
  if (isCustomerTransaction) {
    command.customer = command.customer.trim();
    if (!command.customer) throw Error("Customer name is required");
    command.fee = Number(command.fee);
    if (command.type === "cash_out" && command.fee_mode === "separate")
      command.fee_cash_received = command.fee;
  }
  if (receiptExtraction) {
    command.receipt = {
      provider: receiptExtraction.provider,
      receipt_format: receiptExtraction.receipt_format,
      masked_phone: receiptExtraction.masked_phone || "",
    };
    command.receipt_confirmed = command.receipt_confirmed === "on";
  }
  return command;
}

export function reverseEntry(id) {
  openForm(
    "Reverse record",
    '<p style="margin-bottom:20px">This restores the original balance changes and preserves the record in history.</p>' +
      field("Reason for reversal", "reason", "text", "", "required"),
    async (command) => (store.data = await api("reverse", { id, ...command })),
  );
}
