// Shared-password gate. The cookie holds a hash of the password, never the password itself.

export const AUTH_COOKIE = "sp_auth";

export async function authToken(password: string): Promise<string> {
  const bytes = new TextEncoder().encode(`storypulls:${password}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

export function passwordRequired(): boolean {
  return Boolean(process.env.APP_PASSWORD);
}
