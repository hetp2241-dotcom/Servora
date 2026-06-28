import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import SiteLayout from "@/components/site-layout";
import DashboardLayout from "@/components/dashboard-layout";
import { Loading } from "@/components/states";

const Home = lazy(() => import("@/pages/home"));
const Services = lazy(() => import("@/pages/services"));
const ServiceDetail = lazy(() => import("@/pages/service-detail"));
const Providers = lazy(() => import("@/pages/providers"));
const ProviderDetail = lazy(() => import("@/pages/provider-detail"));
const Login = lazy(() => import("@/pages/login"));
const Register = lazy(() => import("@/pages/register"));
const Dashboard = lazy(() => import("@/pages/dashboard"));
const Bookings = lazy(() => import("@/pages/bookings"));
const Payments = lazy(() => import("@/pages/payments"));
const Messages = lazy(() => import("@/pages/messages"));
const Notifications = lazy(() => import("@/pages/notifications"));
const Reviews = lazy(() => import("@/pages/reviews"));
const Profile = lazy(() => import("@/pages/profile"));
const NotFound = lazy(() => import("@/pages/not-found"));

function Protected() {
  const { isLoading, authenticated } = useAuth();
  const location = useLocation();
  if (isLoading) return <Loading label="Checking your session…" />;
  if (!authenticated) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />;
  return <DashboardLayout />;
}

export default function App() {
  return <Suspense fallback={<Loading />}><Routes><Route element={<SiteLayout />}><Route index element={<Home />} /><Route path="services" element={<Services />} /><Route path="services/:id" element={<ServiceDetail />} /><Route path="providers" element={<Providers />} /><Route path="providers/:id" element={<ProviderDetail />} /><Route path="login" element={<Login />} /><Route path="register" element={<Register />} /></Route><Route element={<Protected />}><Route path="dashboard" element={<Dashboard />} /><Route path="bookings" element={<Bookings />} /><Route path="payments" element={<Payments />} /><Route path="messages" element={<Messages />} /><Route path="notifications" element={<Notifications />} /><Route path="reviews" element={<Reviews />} /><Route path="profile" element={<Profile />} /></Route><Route path="*" element={<NotFound />} /></Routes></Suspense>;
}
