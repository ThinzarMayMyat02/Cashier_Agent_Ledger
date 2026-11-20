// Date/account reports and the export controls hosted only on Daily Closing.
import { api } from "../core/api.js";
import { $, esc, money, today } from "../core/format.js";
import { store } from "../core/store.js";
import { heading } from "../components/common.js";

const WALLET_REPORT_COLUMNS = [
  ["opening", "Opening balance"],
  ["cash_in", "Cash in"],
  ["cash_out", "Cash out"],
  ["fees", "Total fees"],
  ["provider_commission", "Provider commission"],
  ["provider_fee", "Provider fees"],
  ["movement", "Wallet movement"],
  ["closing", "Closing balance"],
];

function renderReportFilters(prefix) {
  return (
    '<div class="filters"><label>Report date<input type="date" id="' +
    prefix +
    '-date" value="' +
    today() +
    '" max="' +
    today() +
    '" required></label>' +
    '<label>Wallet account<select id="' +
    prefix +
    '-wallet"><option value="">All accounts</option>' +
    store.data.accounts
      .map(
        (account) =>
          '<option value="' +
          account.id +
          '">' +
          esc(account.name) +
          "</option>",
      )
      .join("") +
    "</select></label></div>"
  );
}
function selectedReportQuery(prefix) {
  return new URLSearchParams({
    date: $("#" + prefix + "-date").value,
    account_id: $("#" + prefix + "-wallet").value,
  });
}
function renderReportSummary(report) {
  const totals = report.totals;
  return (
    '<div class="stats">' +
    [
      ["Cash in", totals.cash_in],
      ["Cash out", totals.cash_out],
      ["Total fees", totals.fees],
      ["Provider commission", totals.provider_commission],
      ["Provider fees", totals.provider_fee],
      ["Opening balance", totals.opening],
      ["Closing balance", totals.closing],
    ]
      .map(
        ([label, value]) =>
          '<div class="card stat"><div class="statlabel">' +
          label +
          '</div><div class="statvalue">' +
          money(value) +
          " <small>MMK</small></div></div>",
      )
      .join("") +
    "</div>" +
    "<p>Net totals include reversals on their posting date. Balance movement includes funding and expenses.</p>" +
    '<div class="tablewrap"><table><thead><tr>' +
    ["Wallet account", ...WALLET_REPORT_COLUMNS.map(([, label]) => label)]
      .map((label) => "<th>" + label + "</th>")
      .join("") +
    "</tr></thead><tbody>" +
    report.accounts
      .map(
        (account) =>
          "<tr><td data-no-i18n>" +
          esc(account.name) +
          "</td>" +
          WALLET_REPORT_COLUMNS.map(
            ([key]) => "<td>" + money(account[key]) + "</td>",
          ).join("") +
          "</tr>",
      )
      .join("") +
    "</tbody></table></div>"
  );
}
export function reports() {
  $("#view").innerHTML =
    heading(
      "Daily summary",
      "Choose a date and wallet to view the ledger summary.",
    ) +
    '<section class="card">' +
    renderReportFilters("report") +
    '<div id="report-result" aria-live="polite"></div></section>';
  let revision = 0;
  const update = async () => {
    const current = ++revision;
    $("#report-result").textContent = "Loading report…";
    try {
      const report = await api(
        "reports/daily?" + selectedReportQuery("report"),
      );
      if (current === revision && store.page === "reports")
        $("#report-result").innerHTML = renderReportSummary(report);
    } catch (error) {
      if (current === revision && $("#report-result"))
        $("#report-result").textContent = error.message;
    }
  };
  $("#report-date").onchange = update;
  $("#report-wallet").onchange = update;
  update();
}
export function mountClosingExport() {
  $("#closing-export").innerHTML =
    renderReportFilters("export") +
    '<button type="button" id="export-report">Export CSV</button><p id="export-error" role="alert"></p>';
  $("#export-report").onclick = async () => {
    const button = $("#export-report");
    button.disabled = true;
    $("#export-error").textContent = "";
    try {
      const report = await api(
        "reports/daily?" + selectedReportQuery("export"),
      );
      const labels = [
        "Wallet account",
        "Date",
        "Status",
        "Closing status",
        "Closing note",
        ...WALLET_REPORT_COLUMNS.map(([, label]) => label),
        "Counted balance",
        "Difference",
      ];
      const records = report.accounts.map((account) => {
        const counted = report.closing?.counted[String(account.id)];
        const expected = report.closing?.expected[String(account.id)];
        return [
          account.name,
          report.business_date,
          report.closing ? "CLOSED" : "OPEN",
          report.closing
            ? Object.keys(report.closing.expected).every(
                (key) =>
                  report.closing.expected[key] === report.closing.counted[key],
              )
              ? "MATCHED"
              : "WITH_DIFFERENCES"
            : "",
          report.closing?.note || "",
          ...WALLET_REPORT_COLUMNS.map(([key]) => money(account[key])),
          counted == null ? "" : money(counted),
          counted == null || expected == null ? "" : money(counted - expected),
        ];
      });
      const countedValues = report.accounts.map(
        (account) => report.closing?.counted[String(account.id)],
      );
      const expectedValues = report.accounts.map(
        (account) => report.closing?.expected[String(account.id)],
      );
      const complete =
        report.closing &&
        countedValues.every((value) => value != null) &&
        expectedValues.every((value) => value != null);
      const countedTotal = complete
        ? countedValues.reduce((sum, value) => sum + value, 0)
        : null;
      const expectedTotal = complete
        ? expectedValues.reduce((sum, value) => sum + value, 0)
        : null;
      records.push([
        "TOTAL",
        report.business_date,
        report.closing ? "CLOSED" : "OPEN",
        report.closing
          ? Object.keys(report.closing.expected).every(
              (key) =>
                report.closing.expected[key] === report.closing.counted[key],
            )
            ? "MATCHED"
            : "WITH_DIFFERENCES"
          : "",
        report.closing?.note || "",
        ...WALLET_REPORT_COLUMNS.map(([key]) => money(report.totals[key])),
        complete ? money(countedTotal) : "",
        complete ? money(countedTotal - expectedTotal) : "",
      ]);
      const quote = (value) =>
        '"' +
        String(value)
          .replace(/^[=+@-]/, (character) =>
            /^-?\d[\d,]*$/.test(String(value)) ? character : "'" + character,
          )
          .replaceAll('"', '""') +
        '"';
      const csv = [labels, ...records]
        .map((row) => row.map(quote).join(","))
        .join("\r\n");
      const url = URL.createObjectURL(
        new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = "counter-daily-" + report.business_date + ".csv";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      $("#export-error").textContent = error.message;
    } finally {
      button.disabled = false;
    }
  };
}
