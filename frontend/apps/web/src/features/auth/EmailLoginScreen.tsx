import { useState } from "react";
import { useNavigate, Link } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { authApi, parseApiError } from "@restaurantos/api";
import { useSessionStore } from "@restaurantos/stores";
import { Eye, EyeOff, ArrowLeft, LogIn } from "lucide-react";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

type FormData = z.infer<typeof schema>;

export default function EmailLoginScreen() {
  const navigate = useNavigate();
  const login = useSessionStore((s) => s.login);
  const [showPass, setShowPass] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: authApi.staffLogin,
    onSuccess: (data) => {
      login(data.access_token, data.user);
      navigate({ to: "/pos" });
    },
    onError: (err) => {
      const { message } = parseApiError(err);
      setApiError(message);
    },
  });

  const onSubmit = (data: FormData) => {
    setApiError(null);
    mutation.mutate(data);
  };

  return (
    <div style={{
      minHeight: "100dvh",
      background: "var(--color-brand)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: 24,
    }}>
      <div className="animate-fade-in" style={{ width: "100%", maxWidth: 380 }}>

        {/* Back link */}
        <Link to="/auth/pin" style={{
          display: "inline-flex", alignItems: "center", gap: 6,
          color: "var(--color-muted)",
          fontFamily: "var(--font-mono)", fontSize: 12,
          textDecoration: "none", marginBottom: 32,
          letterSpacing: "0.05em",
        }}>
          <ArrowLeft size={13} /> Back to PIN
        </Link>

        {/* Heading */}
        <h1 style={{
          fontFamily: "var(--font-display)",
          fontSize: 24, fontWeight: 700,
          color: "var(--color-text)",
          margin: "0 0 6px",
          letterSpacing: "-0.5px",
        }}>
          Staff Login
        </h1>
        <p style={{
          fontFamily: "var(--font-mono)",
          fontSize: 12, color: "var(--color-muted)",
          margin: "0 0 28px",
        }}>
          Admin & manager email access
        </p>

        <form onSubmit={handleSubmit(onSubmit)}>
          {/* Email */}
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>Email</label>
            <input
              type="email"
              autoComplete="email"
              {...register("email")}
              style={{
                ...inputStyle,
                borderColor: errors.email ? "var(--color-danger)" : "var(--color-border)",
              }}
              placeholder="you@venue.com"
            />
            {errors.email && (
              <p style={fieldErrorStyle}>{errors.email.message}</p>
            )}
          </div>

          {/* Password */}
          <div style={{ marginBottom: 24, position: "relative" }}>
            <label style={labelStyle}>Password</label>
            <div style={{ position: "relative" }}>
              <input
                type={showPass ? "text" : "password"}
                autoComplete="current-password"
                {...register("password")}
                style={{
                  ...inputStyle,
                  paddingRight: 44,
                  borderColor: errors.password
                    ? "var(--color-danger)"
                    : "var(--color-border)",
                }}
              />
              <button
                type="button"
                onClick={() => setShowPass((s) => !s)}
                style={{
                  position: "absolute", right: 12, top: "50%",
                  transform: "translateY(-50%)",
                  background: "none", border: "none",
                  color: "var(--color-muted)", cursor: "pointer",
                  padding: 4,
                }}
              >
                {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {errors.password && (
              <p style={fieldErrorStyle}>{errors.password.message}</p>
            )}
          </div>

          {/* API error */}
          {apiError && (
            <div style={{
              padding: "10px 14px",
              background: "rgba(239,68,68,0.1)",
              border: "1px solid rgba(239,68,68,0.3)",
              borderRadius: "var(--radius-md)",
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              color: "var(--color-danger)",
              marginBottom: 16,
            }}>
              {apiError}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting || mutation.isPending}
            style={{
              width: "100%",
              height: 50,
              background: "var(--color-accent)",
              border: "none",
              borderRadius: "var(--radius-md)",
              color: "#fff",
              fontFamily: "var(--font-display)",
              fontSize: 16, fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              opacity: (isSubmitting || mutation.isPending) ? 0.7 : 1,
              transition: "opacity 0.15s",
            }}
          >
            {(isSubmitting || mutation.isPending)
              ? "Logging in..."
              : <><LogIn size={16} /> Log in</>
            }
          </button>
        </form>
      </div>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: "block",
  fontFamily: "var(--font-mono)",
  fontSize: 11,
  color: "var(--color-muted)",
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  marginBottom: 8,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "12px 14px",
  background: "var(--color-brand-2)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-md)",
  color: "var(--color-text)",
  fontFamily: "var(--font-body)",
  fontSize: 15,
  outline: "none",
  transition: "border-color 0.15s",
};

const fieldErrorStyle: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: 11,
  color: "var(--color-danger)",
  margin: "6px 0 0",
};