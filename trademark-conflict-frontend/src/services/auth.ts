import { UserManager, WebStorageStateStore, type User } from "oidc-client-ts";

const authority = import.meta.env.VITE_OIDC_AUTHORITY as string | undefined;
const clientId = import.meta.env.VITE_OIDC_CLIENT_ID as string | undefined;

export const oidcEnabled = Boolean(authority && clientId);

const manager = authority && clientId
  ? new UserManager({
      authority,
      client_id: clientId,
      redirect_uri: `${window.location.origin}/auth/callback`,
      post_logout_redirect_uri: window.location.origin,
      response_type: "code",
      scope: import.meta.env.VITE_OIDC_SCOPE || "openid profile email",
      userStore: new WebStorageStateStore({ store: window.sessionStorage }),
    })
  : null;

export async function finishSignInCallback(): Promise<void> {
  if (manager && window.location.pathname === "/auth/callback") {
    await manager.signinRedirectCallback();
    window.history.replaceState({}, document.title, "/");
  }
}

export async function getCurrentUser(): Promise<User | null> {
  return manager?.getUser() ?? null;
}

export async function getAccessToken(): Promise<string | null> {
  if (!manager) return null;
  const user = await manager.getUser();
  if (!user || user.expired) {
    throw new Error("Your sign-in has expired. Sign in again to continue.");
  }
  return user.access_token;
}

export async function signIn(): Promise<void> {
  if (!manager) return;
  await manager.signinRedirect();
}

export async function signOut(): Promise<void> {
  if (!manager) return;
  await manager.signoutRedirect();
}
