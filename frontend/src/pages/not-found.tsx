import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
export default function NotFoundPage() { return <main className="grid min-h-[60vh] place-items-center px-4 text-center"><div><p className="font-display text-7xl font-extrabold text-primary">404</p><h1 className="mt-3 text-2xl font-bold">This page wandered off</h1><p className="mt-2 text-sm text-muted-foreground">Let’s get you back to the marketplace.</p><Button asChild className="mt-6"><Link to="/">Go home</Link></Button></div></main>; }
