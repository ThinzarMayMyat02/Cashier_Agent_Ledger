// Whole-MMK inputs display grouping while commands keep plain numeric values.
import { money } from "../core/format.js";

const MONEY_INPUT_SELECTOR = "input[data-money]";
const ALLOWED_MONEY_CHARACTERS = /^[0-9၀-၉,]*$/;
const acceptedInputValues = new WeakMap();

function normalizeDigits(value) {
  return String(value).replace(/[၀-၉]/g, (digit) =>
    String(digit.charCodeAt(0) - 0x1040),
  );
}

export function parseMoney(value) {
  const digits = normalizeDigits(value).replaceAll(",", "");
  if (!/^\d+$/.test(digits)) return NaN;
  const amount = Number(digits);
  return Number.isSafeInteger(amount) ? amount : NaN;
}

export function formatMoneyInput(input) {
  // Reject the whole invalid edit: turning "1e6" into "16" would change money.
  if (!ALLOWED_MONEY_CHARACTERS.test(input.value)) {
    input.value = acceptedInputValues.get(input) ?? "";
  }
  const source = input.value;
  acceptedInputValues.set(input, source);
  const amount = parseMoney(source);
  const minimum = Number(input.getAttribute("min") || 0);
  const maximum = Number(input.getAttribute("max") || 100000000000);
  const invalid =
    source !== "" &&
    (!Number.isFinite(amount) || amount < minimum || amount > maximum);
  input.setCustomValidity(
    invalid
      ? document.documentElement.lang === "my"
        ? "ကျပ်ပြည့်ငွေပမာဏကို သတ်မှတ်ထားသော အတိုင်းအတာအတွင်း ဖြည့်ပါ။"
        : "Enter a whole MMK amount within the allowed range."
      : "",
  );
  if (!Number.isFinite(amount)) return;

  const caret = input.selectionStart;
  const digitsBeforeCaret = normalizeDigits(
    source.slice(0, caret ?? source.length),
  ).replace(/\D/g, "").length;
  const formatted = money(amount);
  input.value = formatted;
  acceptedInputValues.set(input, formatted);
  if (document.activeElement !== input || caret === null) return;
  let position = 0,
    seen = 0;
  while (position < formatted.length && seen < digitsBeforeCaret) {
    if (/\d/.test(formatted[position])) seen++;
    position++;
  }
  input.setSelectionRange(position, position);
}

export function formatMoneyInputs(root) {
  root.querySelectorAll(MONEY_INPUT_SELECTOR).forEach(formatMoneyInput);
}

export function plainMoneyFormData(form) {
  const data = Object.fromEntries(new FormData(form));
  form.querySelectorAll("input[data-money][name]").forEach((input) => {
    data[input.name] = String(parseMoney(input.value));
  });
  return data;
}

// Block typed characters before they enter the field. Deletion/navigation and
// English/Myanmar digits remain available on desktop and mobile keyboards.
document.addEventListener(
  "beforeinput",
  (event) => {
    if (
      event.target.matches(MONEY_INPUT_SELECTOR) &&
      event.data != null &&
      !ALLOWED_MONEY_CHARACTERS.test(event.data)
    )
      event.preventDefault();
  },
  true,
);

document.addEventListener(
  "paste",
  (event) => {
    if (!event.target.matches(MONEY_INPUT_SELECTOR)) return;
    const pastedText = event.clipboardData?.getData("text/plain");
    if (pastedText != null && !ALLOWED_MONEY_CHARACTERS.test(pastedText)) {
      event.preventDefault();
    }
  },
  true,
);

// Fallback for drop, autofill and browsers without cancelable beforeinput.
// Capture runs before fee previews and reconciliation handlers.
document.addEventListener(
  "input",
  (event) => {
    if (event.target.matches(MONEY_INPUT_SELECTOR))
      formatMoneyInput(event.target);
  },
  true,
);
