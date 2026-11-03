type Props = {
  message?: string | null;
  variant?: "info" | "success" | "warning" | "danger";
};

export function OperatorFeedback({ message, variant = "info" }: Props) {
  if (!message) return null;

  const styles =
    variant === "success"
      ? "border-semantic-success-border bg-semantic-success-bg text-semantic-success"
      : variant === "warning"
        ? "border-semantic-warning-border bg-semantic-warning-bg text-semantic-warning"
        : variant === "danger"
          ? "border-semantic-danger-border bg-semantic-danger-bg text-semantic-danger"
          : "border-white/20 bg-white/10 text-white";

  return (
    <div
      role={variant === "danger" ? "alert" : "status"}
      className={`rounded-xl border px-4 py-3 text-sm font-medium ${styles}`}
    >
      {message}
    </div>
  );
}
