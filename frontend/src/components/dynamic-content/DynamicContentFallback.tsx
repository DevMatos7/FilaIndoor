/** Invisible commercial fallback — never show technical errors on TV. */
export function DynamicContentFallback() {
  return <div className="absolute inset-0 bg-brand-950" data-testid="dynamic-fallback" aria-hidden />;
}
