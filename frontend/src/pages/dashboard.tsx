import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, CalendarCheck, CircleDollarSign, Clock3, Sparkles, Star, Wrench } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { money, shortDate } from "@/lib/utils";
import type { Booking, Role } from "@/types/api";
import { PageIntro, Loading, Empty } from "@/components/states";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface Dashboard { role: Role; stats: Record<string, string | number>; recent_bookings?: Booking[] }

type IconComponent = React.ComponentType<{ className?: string }>;

type CardDef = [IconComponent, string | number, string];

export default function DashboardPage() {
  const query = useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => (await api.get<Dashboard>("/dashboard/")).data,
  });

  if (!query.data) return <Loading label="Preparing your dashboard…" />;

  const { role, stats, recent_bookings = [] } = query.data;

  const cards: CardDef[] =
    role === "CUSTOMER"
      ? [
          [CalendarCheck as unknown as IconComponent, stats.total_bookings, "Total bookings"],
          [Clock3 as unknown as IconComponent, stats.upcoming, "Upcoming"],
          [Sparkles as unknown as IconComponent, stats.completed, "Completed"],
          [CircleDollarSign as unknown as IconComponent, money(stats.total_spent || 0), "Total spent"],
        ]
      : role === "PROVIDER"
        ? [
            [Wrench as unknown as IconComponent, stats.active_services, "Active services"],
            [CalendarCheck as unknown as IconComponent, stats.total_bookings, "Bookings"],
            [Star as unknown as IconComponent, stats.average_rating, "Average rating"],
            [CircleDollarSign as unknown as IconComponent, money(stats.earnings || 0), "Earnings"],
          ]
        : [
            [Wrench as unknown as IconComponent, stats.providers, "Providers"],
            [CalendarCheck as unknown as IconComponent, stats.bookings, "Bookings"],
            [Sparkles as unknown as IconComponent, stats.completed, "Completed"],
            [Star as unknown as IconComponent, stats.average_rating, "Platform rating"],
          ];

  return (
    <>
      <PageIntro
        eyebrow={`${role.toLowerCase()} space`}
        title="Good to see you"
        description={
          role === "PROVIDER"
            ? "Stay on top of incoming work, reputation, and earnings."
            : "Everything you need for your next local service, in one calm place."
        }
        actions={
          <Button asChild>
            <Link to={role === "PROVIDER" ? "/profile" : "/services"}>
              {role === "PROVIDER" ? "Manage profile" : "Book a service"}
              <ArrowUpRight className="size-4" />
            </Link>
          </Button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(([IconComp, value, label]) => (
          <Card key={String(label)} className="p-5">
            <div className="flex items-center justify-between">
              <span className="grid size-10 place-items-center rounded-xl bg-primary-soft text-primary">
                <span aria-hidden="true" className="grid size-5 place-items-center">
                  <IconComp />
                </span>
              </span>
              <ArrowUpRight className="size-4 text-muted-foreground" />
            </div>
            <p className="mt-5 font-display text-2xl font-extrabold">{String(value ?? 0)}</p>
            <p className="mt-1 text-xs font-semibold text-muted-foreground">{String(label)}</p>
          </Card>
        ))}
      </div>

      <section className="mt-8">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-extrabold">Recent bookings</h2>
          <Link className="text-sm font-bold text-primary" to="/bookings">
            View all
          </Link>
        </div>

        {recent_bookings.length ? (
          <div className="overflow-hidden rounded-2xl border bg-background shadow-card">
            <div className="divide-y">
              {recent_bookings.map((booking) => (
                <Link
                  to="/bookings"
                  key={booking.id}
                  className="flex flex-col gap-3 p-5 hover:bg-secondary/50 sm:flex-row sm:items-center"
                >
                  <div className="grid size-11 place-items-center rounded-xl bg-primary-soft text-primary">
                    <CalendarCheck className="size-5" />
                  </div>

                  <div className="min-w-0 flex-1">
                    <p className="truncate font-bold">{booking.service.name}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {role === "PROVIDER" ? booking.customer.full_name : booking.provider.full_name} · {shortDate(booking.booking_date)}
                    </p>
                  </div>

                  <Badge>{booking.status_label}</Badge>
                  <p className="font-bold">{money(booking.service.price)}</p>
                </Link>
              ))}
            </div>
          </div>
        ) : (
          <Empty title="No bookings yet" body="Your recent work will appear here." />
        )}
      </section>
    </>
  );
}

