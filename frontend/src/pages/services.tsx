import { useQuery } from "@tanstack/react-query";
import { Search, SlidersHorizontal } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import type { ListResponse, Service } from "@/types/api";
import { ServiceCard } from "@/components/cards";
import { Empty, Loading, PageIntro } from "@/components/states";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function ServicesPage() {
  const [params, setParams] = useSearchParams();
  const queryString = params.toString();
  const query = useQuery({ queryKey: ["services", queryString], queryFn: async () => (await api.get<ListResponse<Service> & { filters: { categories: { id: number; name: string }[]; cities: string[] } }>(`/services/?${queryString}`)).data });
  const update = (key: string, value: string) => { const next = new URLSearchParams(params); value ? next.set(key, value) : next.delete(key); next.delete("page"); setParams(next); };
  return <main className="container-page py-12"><PageIntro eyebrow="Marketplace" title="Find the right service" description="Explore verified local professionals, transparent pricing, and real provider-wide ratings." /><div className="mb-7 grid gap-3 rounded-2xl border bg-background p-3 shadow-card md:grid-cols-[1fr_200px_200px_auto]"><label className="relative"><Search className="absolute left-3 top-3.5 size-4 text-muted-foreground" /><Input value={params.get("search") || ""} onChange={(e) => update("search", e.target.value)} placeholder="Search services or providers" className="pl-9" /></label><select className="h-11 rounded-xl border bg-background px-3 text-sm" value={params.get("category") || ""} onChange={(e) => update("category", e.target.value)}><option value="">All categories</option>{query.data?.filters.categories.map((item) => <option key={item.id} value={item.name}>{item.name}</option>)}</select><select className="h-11 rounded-xl border bg-background px-3 text-sm" value={params.get("sort_by") || "newest_first"} onChange={(e) => update("sort_by", e.target.value)}><option value="newest_first">Newest first</option><option value="price_low">Price: low to high</option><option value="price_high">Price: high to low</option><option value="experience_high">Most experienced</option></select><Button variant="outline" onClick={() => setParams({})}><SlidersHorizontal className="size-4" />Reset</Button></div>{query.isLoading ? <Loading label="Finding trusted services…" /> : query.data?.results.length ? <><div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{query.data.results.map((service) => <ServiceCard key={service.id} service={service} />)}</div><div className="mt-8 flex justify-center gap-2"><Button variant="outline" disabled={!query.data.pagination.has_previous} onClick={() => update("page", String(query.data!.pagination.page - 1))}>Previous</Button><span className="grid h-10 place-items-center px-3 text-sm text-muted-foreground">Page {query.data.pagination.page} of {query.data.pagination.pages}</span><Button variant="outline" disabled={!query.data.pagination.has_next} onClick={() => update("page", String(query.data!.pagination.page + 1))}>Next</Button></div></> : <Empty title="No matching services" />}</main>;
}
