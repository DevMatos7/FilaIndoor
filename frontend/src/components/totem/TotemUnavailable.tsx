type Props = {
  title: string;
  description?: string;
};

/** Reusable commercial unavailable pattern (closed / maintenance / no token). */
export function TotemUnavailable({ title, description }: Props) {
  return (
    <div
      className="rounded-2xl bg-white/12 px-6 py-14 text-center text-white"
      role="status"
      aria-live="polite"
    >
      <p className="text-2xl font-semibold sm:text-3xl">{title}</p>
      {description && <p className="mt-4 text-lg text-brand-100">{description}</p>}
    </div>
  );
}
