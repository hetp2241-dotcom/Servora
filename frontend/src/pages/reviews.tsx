import { useQuery } from "@tanstack/react-query";
import { Star } from "lucide-react";
import { api } from "@/lib/api";
import { shortDate } from "@/lib/utils";
import type { ListResponse, Review } from "@/types/api";
import { Empty, Loading, PageIntro } from "@/components/states";
export default function ReviewsPage() { const query = useQuery({ queryKey: ["reviews"], queryFn: async () => (await api.get<ListResponse<Review>>("/reviews/?page_size=50")).data }); return <><PageIntro eyebrow="Trust & reputation" title="Reviews" description="Every review is tied to a completed booking and contributes to provider-wide rating statistics." />{query.isLoading ? <Loading /> : query.data?.results.length ? <div className="grid gap-4 md:grid-cols-2">{query.data.results.map((review) => <article key={review.id} className="rounded-2xl border bg-background p-5 shadow-card"><div className="flex items-center justify-between"><div><p className="font-bold">{review.service.name}</p><p className="mt-1 text-xs text-muted-foreground">{review.customer.full_name} → {review.provider.full_name}</p></div><span className="flex items-center gap-1 rounded-full bg-warning/10 px-2.5 py-1 text-sm font-bold"><Star className="size-4 fill-warning text-warning" />{review.rating}</span></div><p className="mt-4 text-sm leading-6 text-muted-foreground">{review.comment}</p><p className="mt-3 text-xs text-muted-foreground">{shortDate(review.created_at)}</p></article>)}</div> : <Empty title="No reviews yet" body="Reviews become available after completed bookings." />}</>;
}
