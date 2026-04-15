import { QueryClient } from "@tanstack/react-query";
import { parseApiError } from "@restaurantos/api";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 2,      // 2 min default
      gcTime:    1000 * 60 * 10,     // 10 min gc
      retry: (failureCount, error) => {
        const { status } = parseApiError(error);
        // Never retry auth errors
        if (status === 401 || status === 403) return false;
        return failureCount < 2;
      },
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
});