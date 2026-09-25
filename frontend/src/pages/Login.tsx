import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import IdentityGraphCanvas from "../components/IdentityGraphCanvas";

const STATS = [
  { value: "34", label: "serving tables" },
  { value: "40", label: "data-quality rules / 6 dimensions" },
  { value: "0.994", label: "identity precision (measured)" },
];

function EyeIcon({ open }: { open: boolean }) {
  return open ? (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5Z"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinejoin="round"
      />
      <circle cx="8" cy="8" r="2.1" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  ) : (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M1.5 1.5l13 13M6.6 6.7a2.1 2.1 0 0 0 2.9 2.9M2.3 4.1C1.2 5 .5 6.1.5 6.1s.5 1 1.8 2.4c1.3 1.4 3.2 2.5 5.7 2.5 1 0 1.9-.2 2.7-.5M11.4 4.3C10.4 3.7 9.3 3 8 3c-.5 0-1 .1-1.4.2"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [touched, setTouched] = useState(false);

  const emailInvalid = touched && email.length > 0 && !/^\S+@\S+\.\S+$/.test(email);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setTouched(true);
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex bg-surface">
      {/* Hero panel -- hidden on small screens to keep the login form the
          fast, primary experience on mobile. */}
      <div className="relative hidden lg:flex lg:w-[58%] xl:w-[60%] flex-col justify-between overflow-hidden border-r border-surface-border">
        <div
          className="absolute inset-0 bg-gradient-to-br from-surface via-surface to-surface-raised"
          aria-hidden="true"
        />
        <IdentityGraphCanvas className="absolute inset-0 h-full w-full motion-reduce:hidden" />
        <div
          className="absolute inset-0 bg-[radial-gradient(ellipse_at_30%_20%,rgba(45,212,167,0.07),transparent_55%)]"
          aria-hidden="true"
        />

        <div className="relative z-10 px-14 pt-14">
          <div className="flex items-center gap-2.5">
            <div className="h-7 w-7 rounded-md bg-accent/15 border border-accent/30 flex items-center justify-center">
              <div className="h-2 w-2 rounded-full bg-accent" />
            </div>
            <span className="text-sm font-semibold tracking-tight text-ink">Customer360</span>
          </div>
        </div>

        <div className="relative z-10 px-14 pb-16 max-w-xl motion-safe:animate-fade-in">
          <h1 className="text-3xl font-semibold text-ink leading-tight tracking-tight">
            One canonical view of every customer, assembled from contradictory sources.
          </h1>
          <p className="mt-4 text-sm text-ink-muted leading-relaxed">
            Customer360 resolves fragmented identity across a CRM, a loyalty programme, an app,
            and orders into a single auditable customer — with every merge traceable to the rule
            and identifier that caused it, never a guess.
          </p>
          <dl className="mt-10 grid grid-cols-3 gap-6 border-t border-surface-border pt-6">
            {STATS.map((s) => (
              // Values sit on one baseline even when a label wraps to two lines.
              <div key={s.label} className="flex flex-col justify-between">
                <dt className="stat-label">{s.label}</dt>
                <dd className="text-xl font-semibold text-ink mt-1 font-mono">{s.value}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-6 text-[11px] text-ink-faint leading-relaxed">
            Measured against generator ground truth on synthetic data — see benchmarks/IDENTITY_EVAL.md.
          </p>
        </div>
      </div>

      {/* Login panel */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 sm:px-10">
        <div className="w-full max-w-sm motion-safe:animate-fade-in-up">
          <div className="mb-8 lg:hidden">
            <div className="flex items-center gap-2.5 justify-center">
              <div className="h-7 w-7 rounded-md bg-accent/15 border border-accent/30 flex items-center justify-center">
                <div className="h-2 w-2 rounded-full bg-accent" />
              </div>
              <span className="text-base font-semibold tracking-tight text-ink">Customer360</span>
            </div>
          </div>

          <div className="mb-7 text-center lg:text-left">
            <h2 className="text-xl font-semibold text-ink">Sign in</h2>
            <p className="text-sm text-ink-muted mt-1.5">
              Unified Customer Data &amp; Personalization Platform
            </p>
          </div>

          <form onSubmit={onSubmit} className="card p-6 space-y-4 shadow-[0_0_0_1px_rgba(255,255,255,0.02)]" noValidate>
            <div>
              <label htmlFor="email" className="block text-xs text-ink-muted mb-1.5">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="username"
                required
                value={email}
                aria-invalid={emailInvalid}
                aria-describedby={emailInvalid ? "email-error" : undefined}
                onChange={(e) => setEmail(e.target.value)}
                onBlur={() => setTouched(true)}
                className={`w-full bg-surface border rounded px-3 py-2.5 text-sm text-ink transition-colors focus:outline-none focus:ring-1 ${
                  emailInvalid
                    ? "border-danger focus:ring-danger"
                    : "border-surface-border focus:ring-accent focus:border-accent"
                }`}
              />
              {emailInvalid && (
                <p id="email-error" className="mt-1 text-[11px] text-danger">
                  Enter a valid email address.
                </p>
              )}
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label htmlFor="password" className="block text-xs text-ink-muted">
                  Password
                </label>
              </div>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-surface border border-surface-border rounded px-3 py-2.5 pr-10 text-sm text-ink transition-colors focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  aria-pressed={showPassword}
                  className="absolute inset-y-0 right-0 flex items-center px-3 text-ink-faint hover:text-ink-muted focus:outline-none focus-visible:text-accent transition-colors"
                >
                  <EyeIcon open={showPassword} />
                </button>
              </div>
            </div>

            {error && (
              <div role="alert" className="rounded bg-danger/10 border border-danger/25 px-3 py-2 text-xs text-danger">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full inline-flex items-center justify-center gap-2 bg-accent text-surface font-medium rounded px-3 py-2.5 text-sm hover:bg-accent-dim active:scale-[0.99] transition-all disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
            >
              {submitting && (
                <span
                  className="h-3.5 w-3.5 rounded-full border-2 border-surface/40 border-t-surface motion-safe:animate-spin"
                  aria-hidden="true"
                />
              )}
              {submitting ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <p className="mt-6 text-center lg:text-left text-[11px] text-ink-faint leading-relaxed">
            Demo access is provisioned per deployment and is not a public self-serve account —
            see <code className="font-mono">docs/SETUP.md</code> for creating a local login.
          </p>
        </div>
      </div>
    </div>
  );
}
