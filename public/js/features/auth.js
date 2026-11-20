// Owner and staff sign-in screens.
import { toast } from "../components/common.js";

import { api } from "../core/api.js";
import { $ } from "../core/format.js";
import { store } from "../core/store.js";
import { load } from "../shell.js";

export function auth(setup = false) {
  store.data = null;
  $("#app").innerHTML = `<div class="auth">
<div class="auth-tools" data-language-slot></div>
<div class="brand">
<span class="mark">↗</span>counter<span style="color:#96aa9c">.</span>
</div>
<h1>${setup ? "Open your shop ledger" : "Welcome back"}</h1>
<p>${setup ? "Create the owner login. Your shop starts with zero balances; add opening funds after signing in." : "Sign in to manage your shop’s daily money flow."}</p>
<form id="authform">
<div class="field">
<label for="name">${setup ? "Owner name" : "Login name"}</label>
<input id="name" name="name" required autocomplete="username" maxlength="80">
</div>
<div class="field">
<label for="password">Password</label>
<input id="password" name="password" type="password" required minlength="${setup ? 10 : 1}" autocomplete="${setup ? "new-password" : "current-password"}">
</div>
<div class="error" role="alert">
</div>
<button class="primary">${setup ? "Create shop" : "Sign in"} →</button>
</form>
</div>`;
  $("#authform").onsubmit = async (e) => {
    e.preventDefault();
    const b = e.target.querySelector("button");
    b.disabled = true;
    try {
      await api(
        setup ? "setup" : "login",
        Object.fromEntries(new FormData(e.target)),
      );
      await load();
    } catch (err) {
      e.target.querySelector(".error").textContent = err.message;
    } finally {
      b.disabled = false;
    }
  };
}

export async function logout() {
  try {
    await api("logout", {});
    auth();
  } catch (e) {
    toast(e.message);
  }
}
