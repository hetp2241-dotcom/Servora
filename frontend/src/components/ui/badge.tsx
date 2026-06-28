import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";
export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) { return <span className={cn("inline-flex items-center rounded-full bg-primary-soft px-2.5 py-1 text-xs font-semibold text-primary", className)} {...props} />; }
