// JSON requests share authentication handling and preserve server error messages.
import { auth } from "../features/auth.js";

export async function api(path, data) {
  const response = await fetch(
    "/api/" + path,
    data
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        }
      : {},
  );
  const result = await response.json();
  if (!response.ok) {
    if (response.status === 401) {
      auth(result.setup);
      if (path === "state") return null;
    }
    throw Error(result.error || "Please sign in");
  }
  return result;
}
