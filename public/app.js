// Browser entry point. Inline button handlers are bridged explicitly for existing templates.
import { load, go } from "./js/shell.js";
import { logout } from "./js/features/auth.js";
import { entryForm, reverseEntry } from "./js/features/transactions.js";
import { accountForm } from "./js/features/accounts.js";
import { staffForm } from "./js/features/team.js";
import { importReceipt } from "./js/features/receipts.js";

Object.assign(window, {
  load,
  go,
  logout,
  entryForm,
  reverseEntry,
  accountForm,
  staffForm,
  importReceipt,
});
load();
