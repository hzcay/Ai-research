"use client";

import { useState } from "react";
import { Check } from "lucide-react";

type User = { id: string; email: string; display_name: string };

export function AuthScreen({ onAuthenticated }: { onAuthenticated: (user: User) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(form: FormData) {
    setBusy(true); setError("");
    try {
      const response = await fetch(`/api/backend/auth/${mode}`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: form.get("email"), password: form.get("password"), display_name: form.get("display_name") }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Authentication failed");
      onAuthenticated(payload);
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  return <main className="authPage"><section className="authStory"><div className="authBrand"><span>R</span> Research Workspace</div><div><p className="eyebrow">Evidence before answers</p><h1>Turn a research question into a review you can defend.</h1><p>Plan the scope, coordinate reviewers, trace every decision, and keep AI grounded in project evidence.</p></div><div className="authProof"><span><Check size={15}/> Reproducible workflow</span><span><Check size={15}/> Human approval gates</span><span><Check size={15}/> Project-scoped evidence</span></div></section><section className="authPanel"><div className="authCard"><span className="authKicker">{mode === "login" ? "Welcome back" : "Create your workspace"}</span><h2>{mode === "login" ? "Sign in to continue" : "Start your research account"}</h2><p>{mode === "login" ? "Access the projects and reviews shared with you." : "Create an account before starting or joining a project."}</p><form action={submit}>{mode === "register" && <label>Full name<input name="display_name" minLength={2} required autoFocus placeholder="Nguyen Van A"/></label>}<label>Email address<input name="email" type="email" required autoFocus={mode === "login"} placeholder="you@university.edu"/></label><label>Password<input name="password" type="password" minLength={8} required placeholder="At least 8 characters"/></label>{error && <div className="authError">{error}</div>}<button className="authSubmit" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button></form><div className="authSwitch">{mode === "login" ? "New to Research Workspace?" : "Already have an account?"}<button onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>{mode === "login" ? "Create an account" : "Sign in"}</button></div></div></section></main>;
}
