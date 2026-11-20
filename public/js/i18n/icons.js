// One shared SVG icon set for navigation and transaction actions.
const svgPaths = {
  overview:
    '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  history: '<path d="M4 7h16m-4-4 4 4-4 4M20 17H4m4-4-4 4 4 4"/>',
  accounts:
    '<rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 9h18m-6 5h3"/>',
  expenses: '<path d="M5 12h14"/>',
  closing: '<path d="m5 12 4 4L19 6"/>',
  team: '<circle cx="9" cy="7" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 4a3 3 0 0 1 0 6m2 5a5 5 0 0 1 3 4v2"/>',
  in: '<path d="M18 6 6 18M6 7v11h11"/>',
  out: '<path d="M6 18 18 6M7 6h11v11"/>',
  refresh:
    '<path d="M20 7v5h-5M4 17v-5h5m-4-5a8 8 0 0 1 13-2l2 2M4 17l2 2a8 8 0 0 0 13-2"/>',
  logout: '<path d="M9 4H4v16h5m-1-8h13m-5-5 5 5-5 5"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  export: '<path d="M12 3v12m-4-4 4 4 4-4M4 16v5h16v-5"/>',
};
function counterIcon(name) {
  return (
    '<svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    (svgPaths[name] || svgPaths.accounts) +
    "</svg>"
  );
}
export function decorateIcons() {
  document.querySelectorAll("button").forEach((button) => {
    const text = button.firstChild;
    if (text?.nodeType !== Node.TEXT_NODE) return;
    const symbol = text.data.trimStart()[0];
    const name = { "＋": "plus", "↓": "export", "−": "expenses" }[symbol];
    if (name) {
      text.data = text.data.replace(symbol, "").trimStart();
      button.insertAdjacentHTML("afterbegin", counterIcon(name));
    }
  });

  document.querySelectorAll("[data-nav]").forEach((button) => {
    const span = button.querySelector("span");
    if (span && !span.querySelector("svg"))
      span.innerHTML = counterIcon(button.dataset.nav);
  });
  const symbols = {
    "↙": "in",
    "↗": "out",
    "−": "expenses",
    "✓": "closing",
    "↻": "refresh",
    "↪": "logout",
    "✕": "close",
    "◫": "overview",
    "⇄": "history",
    "▣": "accounts",
    "▤": "accounts",
  };
  document
    .querySelectorAll(".quickgrid b,.mark,.statlabel span,button.quiet")
    .forEach((element) => {
      const name = symbols[element.textContent.trim()];
      if (name) element.innerHTML = counterIcon(name);
    });
}
