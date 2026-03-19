import { useMutation } from "@tanstack/react-query";
import type { AnalysisResponse } from "../types/api";

/**
 * Generic hook for analysis API calls.
 * Wraps react-query useMutation for loading/error state.
 */
export function useAnalysis<TReq, TData = Record<string, unknown>>(
  fn: (req: TReq) => Promise<AnalysisResponse<TData>>
) {
  const mutation = useMutation({
    mutationFn: fn,
  });

  return {
    run: mutation.mutate,
    runAsync: mutation.mutateAsync,
    data: mutation.data?.data ?? null,
    error: mutation.data?.error || mutation.error?.message || null,
    isLoading: mutation.isPending,
    isSuccess: mutation.data?.success ?? false,
    reset: mutation.reset,
  };
}
