import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
export function Logo({ className }: { className?: string }) {
  return <Link to="/" className={cn("flex items-center gap-2 font-display text-xl font-extrabold", className)}><span className="grid size-9 place-items-center rounded-xl bg-gradient-brand text-white shadow-glow"><Sparkles className="size-4" /></span>Servora</Link>;
}
