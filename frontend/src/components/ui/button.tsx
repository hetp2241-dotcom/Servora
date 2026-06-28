import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva("focus-ring inline-flex items-center justify-center gap-2 rounded-xl font-semibold disabled:pointer-events-none disabled:opacity-50", {
  variants: {
    variant: {
      default: "bg-gradient-brand text-primary-foreground shadow-glow hover:opacity-95",
      secondary: "bg-secondary text-foreground hover:bg-primary-soft",
      outline: "border bg-background text-foreground hover:bg-secondary",
      ghost: "text-muted-foreground hover:bg-secondary hover:text-foreground",
      destructive: "bg-destructive text-white hover:opacity-90"
    },
    size: { default: "h-10 px-4 text-sm", sm: "h-9 px-3 text-sm", lg: "h-12 px-6", icon: "size-10" }
  },
  defaultVariants: { variant: "default", size: "default" }
});

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> { asChild?: boolean }
export function Button({ className, variant, size, asChild, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
export { buttonVariants };
