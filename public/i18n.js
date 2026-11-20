import { interfaceTranslations, englishChoices } from "./js/i18n/messages.js";
import { decorateIcons } from "./js/i18n/icons.js";

// Translate interface text in place so switching language preserves live form values.
let counterLanguage = "my";
try {
  counterLanguage =
    localStorage.getItem("counter-language") === "en" ? "en" : "my";
} catch {}
const originalText = new WeakMap(),
  originalAttributes = new WeakMap();
function translated(text) {
  const core = text.trim();
  let value =
    counterLanguage === "my"
      ? interfaceTranslations[core]
      : englishChoices[core];
  if (value === undefined && counterLanguage === "my") {
    const decorations = core.match(/^([＋↓−]?\s*)(.*?)(\s*→)?$/u);
    if (decorations && interfaceTranslations[decorations[2]])
      value =
        decorations[1] +
        interfaceTranslations[decorations[2]] +
        (decorations[3] || "");
    if (/^\d+ accounts combined$/.test(core))
      value = core.replace(" accounts combined", " အကောင့် စုစုပေါင်း");
    if (core.startsWith("/ ") && interfaceTranslations[core.slice(2)])
      value = "/ " + interfaceTranslations[core.slice(2)];
    if (
      /^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),/.test(core)
    ) {
      const date = new Date(core);
      if (!Number.isNaN(date.getTime()))
        value = date.toLocaleDateString("my-MM", {
          weekday: "long",
          month: "long",
          day: "numeric",
          year: "numeric",
        });
    }
    const cashError = core.match(
      /^Insufficient shop cash\. Available: ([\d,]+) MMK; required: ([\d,]+) MMK\.$/,
    );
    if (cashError)
      value =
        "ဆိုင်ငွေသား မလုံလောက်ပါ။ ရှိငွေ " +
        cashError[1] +
        " ကျပ်၊ လိုအပ်ငွေ " +
        cashError[2] +
        " ကျပ်။";
    if (/^Expected: /.test(core))
      value = core.replace("Expected: ", "ရှိရမည့်လက်ကျန် - ");
    if (/^Recorded by /.test(core))
      value = core.replace("Recorded by ", "စာရင်းသွင်းသူ - ");
    if (/^Reversed: /.test(core))
      value = core.replace("Reversed: ", "ပြန်လှန်ရသည့်အကြောင်း - ");
    if (/ MMK difference$/.test(core))
      value = core.replace(" MMK difference", " ကျပ် ကွာဟချက်");
    if (core.startsWith("Receive "))
      value = core
        .replace("Receive ", "လက်ခံရန် ")
        .replace(" · Wallet −", " · အကောင့်မှ နုတ်ရန် −");
    if (core.startsWith("Pay "))
      value = core
        .replace("Pay ", "ပေးရန် ")
        .replace(" AND collect ", " နှင့် ဝန်ဆောင်ခယူရန် ")
        .replace(" MMK fee", " MMK")
        .replace(" · Wallet +", " · အကောင့်သို့ ပေါင်းရန် +");
    if (core.startsWith("Counted balance for "))
      value = core.replace("Counted balance for ", "ရေတွက်ထားသော လက်ကျန် - ");
  }
  return value === undefined ? text : text.replace(core, value);
}
let languageObserver;
function applyCounterLanguage() {
  languageObserver?.disconnect();
  // User-entered names, notes, numbers and account labels never become translation keys.
  const skip =
    "script,style,svg,[data-no-i18n],.brand,.wallet h3,.wallet p,.userrow .avatar,.userrow div,.status,.closingrow b,td:first-child b,td:nth-child(3),td:nth-child(9)";
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    if (!node.parentElement || node.parentElement.closest(skip)) continue;
    if (
      node.parentElement.tagName === "OPTION" &&
      ["f_account_id", "walletfilter", "stafffilter", "f_active"].includes(
        node.parentElement.parentElement.id,
      ) &&
      node.parentElement.value !== ""
    )
      continue;
    const previous = originalText.get(node);
    const source =
      previous && previous.rendered === node.data ? previous.source : node.data;
    const rendered = translated(source);
    if (rendered !== node.data) node.data = rendered;
    originalText.set(node, { source, rendered });
  }
  document.querySelectorAll("[placeholder],[aria-label]").forEach((element) => {
    let record = originalAttributes.get(element) || {};
    for (const attr of ["placeholder", "aria-label"]) {
      if (!element.hasAttribute(attr)) continue;
      const current = element.getAttribute(attr),
        previous = record[attr];
      const source =
        previous && previous.rendered === current ? previous.source : current;
      const rendered = translated(source);
      element.setAttribute(attr, rendered);
      record[attr] = { source, rendered };
    }
    originalAttributes.set(element, record);
  });
  document.documentElement.lang = counterLanguage;
  document
    .querySelectorAll(".language-picker")
    .forEach((e) => (e.value = counterLanguage));
  decorateIcons();
  languageObserver?.observe(document.body, {
    subtree: true,
    childList: true,
    characterData: true,
  });
}
function languageControl() {
  const label = document.createElement("label");
  label.className = "language-control";
  label.dataset.noI18n = "";
  label.innerHTML =
    '<span aria-hidden="true">◎</span><select class="language-picker" aria-label="Language / ဘာသာစကား"><option value="my">မြန်မာ</option><option value="en">English</option></select>';
  label.querySelector("select").onchange = (e) => {
    counterLanguage = e.target.value;
    try {
      localStorage.setItem("counter-language", counterLanguage);
    } catch {}
    applyCounterLanguage();
  };
  return label;
}
document.body.prepend(languageControl());
const dialog = document.querySelector("#modal");
// A modal has its own selector because background controls are inert while it is open.
new MutationObserver(() => {
  if (dialog.open && !dialog.querySelector(".language-control"))
    dialog.prepend(languageControl());
}).observe(dialog, {
  attributes: true,
  attributeFilter: ["open"],
  childList: true,
});
languageObserver = new MutationObserver(applyCounterLanguage);
applyCounterLanguage();
