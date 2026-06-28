import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ensureCsrf } from "@/lib/api";
import type { Session } from "@/types/api";

export function useAuth() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["session"], queryFn: async () => (await api.get<Session>("/auth/session/")).data, staleTime: 60_000 });
  return {
    ...query,
    user: query.data?.user ?? null,
    authenticated: query.data?.authenticated ?? false,
    login: async (email: string, password: string, remember = false) => {
      await ensureCsrf();
      await api.post("/auth/login/", new URLSearchParams({ username: email, password, remember_me: remember ? "on" : "" }));

      await client.invalidateQueries({ queryKey: ["session"] });
    },
    logout: async () => {
      await ensureCsrf();
      await api.post("/auth/logout/");
      client.clear();
      await client.invalidateQueries({ queryKey: ["session"] });
    }
  };
}
