import { useQuery } from "@tanstack/react-query";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";

delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({ iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png", iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png", shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png" });
interface Location { profile_id: number; provider_name: string; latitude: number; longitude: number; city: string; average_rating: number; is_verified: boolean }
export default function ProviderMap() { const query = useQuery({ queryKey: ["provider-locations"], queryFn: async () => (await api.get<{ results: Location[] }>("/maps/providers/")).data.results }); const points = query.data || []; return <div className="overflow-hidden rounded-2xl border bg-background shadow-card"><div className="p-4"><h2 className="font-bold">Providers near you</h2><p className="mt-1 text-xs text-muted-foreground">Live location data from existing provider profiles</p></div><MapContainer center={[23.0225, 72.5714]} zoom={9} className="h-[430px] w-full"><TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />{points.map((point) => <Marker key={point.profile_id} position={[point.latitude, point.longitude]}><Popup><strong>{point.provider_name}</strong><br />{point.city} · ★ {point.average_rating.toFixed(1)}<br /><Link to={`/providers/${point.profile_id}`}>View profile</Link></Popup></Marker>)}</MapContainer></div>; }
