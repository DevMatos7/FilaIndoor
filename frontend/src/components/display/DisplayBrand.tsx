type Props = {
  size?: "sm" | "md" | "lg";
  className?: string;
};

export function DisplayBrand({ size = "md", className = "" }: Props) {
  const sizeClass =
    size === "lg" ? "text-[clamp(2.5rem,6vw,5rem)]" : size === "sm" ? "text-2xl" : "text-[clamp(2rem,4vw,3.5rem)]";
  return (
    <p className={`font-bold tracking-tight text-white ${sizeClass} ${className}`} aria-label="REAL">
      REAL
    </p>
  );
}
