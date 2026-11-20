// Owner-managed staff screens.
import { heading } from "../components/common.js";
import { field, openForm } from "../components/forms.js";
import { api } from "../core/api.js";
import { $, esc } from "../core/format.js";
import { store } from "../core/store.js";

export function team() {
  $("#view").innerHTML =
    heading(
      "Your team",
      "Each transaction is linked to the person who recorded it.",
      '<button class="primary" onclick="staffForm()">＋ Add staff</button>',
    ) +
    `<section class="card">
<div class="tablewrap">
<table>
<thead>
<tr>
<th>Login name</th>
<th>Role</th>
</tr>
</thead>
<tbody>${store.data.staff
      .map(
        (u) => `<tr>
<td>${esc(u.name)}</td>
<td>
<span class="badge">${esc(u.role)}</span>
</td>
</tr>`,
      )
      .join("")}</tbody>
</table>
</div>
<div class="infobox">
<p>Staff can record transactions, expenses and daily counts. Only the owner can manage accounts, add or remove funds, create staff and reverse records.</p>
</div>
</section>`;
}

export function staffForm() {
  openForm(
    "Create staff login",
    field(
      "Staff login name",
      "name",
      "text",
      "",
      'required maxlength="80" autocomplete="off"',
    ) +
      field(
        "Temporary password (10+ characters)",
        "password",
        "password",
        "",
        'required minlength="10" autocomplete="new-password"',
      ),
    async (d) => (store.data = await api("staff", d)),
  );
}
