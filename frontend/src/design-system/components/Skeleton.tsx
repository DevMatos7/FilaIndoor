import { HTMLAttributes } from "react";
import { cn } from "../utils/cn";

function Base({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-ds bg-brand-100/80", className)}
      aria-hidden
      {...props}
    />
  );
}

export function SkeletonText({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <Base className={cn("h-4 w-full", className)} {...props} />;
}

export function SkeletonLine({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <Base className={cn("h-3 w-3/4", className)} {...props} />;
}

export function SkeletonCard({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("space-y-3 rounded-ds border border-brand-100 bg-surface p-4", className)}
      {...props}
    >
      <SkeletonText className="w-1/3" />
      <SkeletonLine />
      <SkeletonLine className="w-1/2" />
    </div>
  );
}

export function SkeletonMetric({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("rounded-ds border border-brand-100 bg-surface p-4", className)} {...props}>
      <SkeletonText className="h-3 w-20" />
      <Base className="mt-3 h-8 w-24" />
    </div>
  );
}

export const Skeleton = {
  Text: SkeletonText,
  Line: SkeletonLine,
  Card: SkeletonCard,
  Metric: SkeletonMetric,
};
