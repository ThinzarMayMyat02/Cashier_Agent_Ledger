// Receipt evidence uses Myanmar wall time; never convert through browser timezone.
export function splitReceiptTime(value = "") {
  const text = String(value).trim();
  const legacy = text.match(
    /^(\d{2})\/(\d{2})\/(\d{4})(?:\s+(\d{2}:\d{2}(?::\d{2})?))?$/,
  );
  if (legacy)
    return {
      date: `${legacy[3]}-${legacy[2]}-${legacy[1]}`,
      time: legacy[4] || "",
    };
  const iso = text.match(
    /^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}(?::\d{2})?))?$/,
  );
  return { date: iso?.[1] || "", time: iso?.[2] || "" };
}

export function joinReceiptTime(date, time) {
  if (time && !date) throw Error("Choose a receipt date before the time");
  if (!date) return "";
  const [year, month, day] = date.split("-");
  const clock = time ? (time.length === 5 ? time + ":00" : time) : "";
  return `${day}/${month}/${year}${clock ? " " + clock : ""}`;
}
