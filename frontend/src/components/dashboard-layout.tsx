import { Bell, BriefcaseBusiness, CalendarDays, CreditCard, LayoutDashboard, LogOut, MapPinned, Menu, MessageCircle, Search, Star, UserRound, Wrench, X } from "lucide-react";
import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { Logo } from "./brand";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

export default function DashboardLayout() {
  const [open, setOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const nav = [
    ["/dashboard", "Overview", LayoutDashboard], ["/bookings", "Bookings", CalendarDays], ["/messages", "Messages", MessageCircle],
    ["/payments", "Payments", CreditCard], ["/reviews", "Reviews", Star], ["/notifications", "Notifications", Bell],
    ["/services", user?.role === "PROVIDER" ? "My services" : "Discover", Wrench], ["/providers", "Provider map", MapPinned], ["/profile", "Profile", UserRound]
  ] as const;
  const sidebar = <><Logo className="px-2" /><nav className="mt-8 flex flex-1 flex-col gap-1">{nav.map(([to, label, Icon]) => <NavLink key={to} to={to} onClick={() => setOpen(false)} end={to === "/dashboard"} className={({ isActive }) => cn("flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold", isActive ? "bg-primary-soft text-primary" : "text-muted-foreground hover:bg-secondary hover:text-foreground")}><Icon className="size-4" />{label}</NavLink>)}</nav><div className="rounded-2xl border bg-gradient-subtle p-4"><div className="flex items-center gap-2"><BriefcaseBusiness className="size-4 text-primary" /><p className="text-xs font-bold uppercase tracking-wider text-primary">{user?.role || "Servora"}</p></div><p className="mt-2 text-sm font-semibold">{user?.full_name}</p><button onClick={async () => { await logout(); navigate("/"); }} className="mt-3 flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-destructive"><LogOut className="size-3.5" />Sign out</button></div></>;
  return <div className="min-h-screen bg-secondary/40"><div className="mx-auto flex max-w-[1440px]"><aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r bg-background px-4 py-6 lg:flex">{sidebar}</aside>{open && <div className="fixed inset-0 z-50 lg:hidden"><button className="absolute inset-0 bg-foreground/30" onClick={() => setOpen(false)} /><aside className="relative flex h-full w-72 flex-col bg-background px-4 py-6 shadow-xl">{sidebar}<button className="absolute right-4 top-5" onClick={() => setOpen(false)}><X /></button></aside></div>}<main className="min-w-0 flex-1"><header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b bg-background/85 px-4 backdrop-blur-xl sm:px-8"><button className="grid size-9 place-items-center rounded-lg border lg:hidden" onClick={() => setOpen(true)}><Menu className="size-4" /></button><div className="hidden h-9 max-w-md flex-1 items-center gap-2 rounded-lg border bg-secondary/60 px-3 text-sm text-muted-foreground md:flex"><Search className="size-4" />Search bookings, pros, services…</div><div className="flex-1 md:hidden" /><Link to="/notifications" className="relative grid size-9 place-items-center rounded-lg border bg-background hover:bg-secondary"><Bell className="size-4" /><span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-destructive ring-2 ring-background" /></Link><div className="grid size-9 place-items-center rounded-full bg-gradient-brand text-sm font-bold text-white">{user?.full_name?.charAt(0)}</div></header><div className="px-4 py-8 sm:px-8"><Outlet /></div></main></div></div>;
}
