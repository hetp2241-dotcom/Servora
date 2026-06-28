import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import type { ListResponse, Provider } from "@/types/api";
import { ProviderCard } from "@/components/cards";
import { Empty, Loading, PageIntro } from "@/components/states";
import { Input } from "@/components/ui/input";
import ProviderMap from "@/components/provider-map";
export default function ProvidersPage() { const [params, setParams] = useSearchParams(); const qs = params.toString(); const query = useQuery({ queryKey: ["providers", qs], queryFn: async () => (await api.get<ListResponse<Provider>>(`/providers/?${qs}`)).data }); return <main className="container-page py-12"><PageIntro eyebrow="Local talent" title="Meet trusted professionals" description="Provider-wide ratings, completed jobs, and verification signals help you choose with confidence." /><div className="grid gap-8 lg:grid-cols-[1fr_360px]"><div><label className="relative mb-6 block"><Search className="absolute left-3 top-3.5 size-4 text-muted-foreground" /><Input className="pl-9" placeholder="Search providers or skills" value={params.get("search") || ""} onChange={(e) => { const next = new URLSearchParams(params); e.target.value ? next.set("search", e.target.value) : next.delete("search"); setParams(next); }} /></label>{query.isLoading ? <Loading /> : query.data?.results.length ? <div className="grid gap-5 sm:grid-cols-2">{query.data.results.map((provider) => <ProviderCard key={provider.id} provider={provider} />)}</div> : <Empty title="No providers found" />}</div><aside className="lg:sticky lg:top-24 lg:h-fit"><ProviderMap /></aside></div></main>; }
