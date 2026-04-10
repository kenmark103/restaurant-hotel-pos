import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { createBranch, CreateBranchPayload, getBranches } from '@/features/staff/api/branchApi'
import { BranchRecord } from '@/features/staff/api/branchApi'

export const branchQueryKeys = {
  all: ['branches'] as const,
}

export function useBranches() {
  return useQuery({
    queryKey: branchQueryKeys.all,
    queryFn: getBranches,
    staleTime: 30 * 60 * 1000,
  })
}

export function useCreateBranch() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateBranchPayload) => createBranch(payload),
    onSuccess: (createdBranch) => {
      queryClient.setQueryData<BranchRecord[]>(branchQueryKeys.all, (current = []) => [createdBranch, ...current])
    },
  })
}
