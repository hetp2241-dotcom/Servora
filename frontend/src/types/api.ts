export type Role = "CUSTOMER" | "PROVIDER" | "ADMIN";
export interface User { id: number; email: string; full_name: string; phone_number: string; role: Role; is_active: boolean; date_joined: string }
export interface Session { authenticated: boolean; user: User | null }
export interface Pagination { page: number; page_size: number; count: number; pages: number; has_next: boolean; has_previous: boolean }
export interface ListResponse<T> { results: T[]; pagination: Pagination }
export interface Rating { average_rating: number; review_count: number; distribution?: Record<string, number> }
export interface Service extends Rating { id: number; name: string; description: string; price: string; duration_hours: number; image_url: string; is_available: boolean; created_at: string; category: { id: number; name: string } | null; provider: { id: number; profile_id: number | null; full_name: string; city: string; is_verified: boolean; profile_picture_url: string }; reviews?: Review[]; related_services?: Service[] }
export interface Provider extends Rating { id: number; user_id: number; full_name: string; phone_number: string; address: string; city: string; latitude: number; longitude: number; experience_years: number; description: string; is_verified: boolean; profile_picture_url: string; completion_percentage: number; member_since: string; jobs_completed: number; services?: Service[]; latest_reviews?: Review[] }
export interface Payment { id: number; booking_id: number; amount: string; payment_status: string; stripe_session_id: string; created_at: string; service_name: string }
export interface Booking { id: number; booking_date: string; notes: string; status: string; status_label: string; created_at: string; service: { id: number; name: string; price: string }; customer: { id: number; full_name: string }; provider: { id: number; full_name: string }; payment: Payment | null; has_review: boolean; review_id: number | null }
export interface Review { id: number; booking_id: number; service: { id: number; name: string }; customer: { id: number; full_name: string }; provider: { id: number; full_name: string }; rating: number; comment: string; created_at: string; updated_at: string }
export interface Notification { id: number; type: string; title: string; message: string; link: string; created_at: string; read_at: string | null; actor?: { id: number; full_name: string } | null }
export interface ChatMessage { id: number; sender_id: number; receiver_id: number; message: string; timestamp: string }
