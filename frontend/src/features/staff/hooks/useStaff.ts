import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { disableStaffMember, getStaffMembers, inviteStaffMember, activateStaffAccount } from '@/features/staff/api/staffApi'
import type { InviteStaffPayload, ActivateStaffPayload } from '@/features/staff/api/staffApi'
import { StaffMember } from '@/features/staff/types'

export const staffQueryKeys = {
  all: ['staff-members'] as const,
}

export function useStaffMembers() {
  return useQuery({
    queryKey: staffQueryKeys.all,
    queryFn: getStaffMembers,
    staleTime: 2 * 60 * 1000,
  })
}

// Backward-compatible alias used by TeamPage.
export function useStaffList() {
  return useStaffMembers()
}

export function useInviteStaff() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: InviteStaffPayload) => inviteStaffMember(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: staffQueryKeys.all })
    },
  })
}

export function useDisableStaff() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (staffId: number) => disableStaffMember(staffId),
    onSuccess: (_response, staffId) => {
      queryClient.setQueryData<StaffMember[]>(staffQueryKeys.all, (current = []) =>
        current.map((member) =>
          member.id === staffId ? { ...member, status: 'disabled' } : member
        ),
      )
    },
  })
}

// New — used by StaffActivatePage (public route, no auth)
export function useActivateStaff() {
  return useMutation({
    mutationFn: (payload: ActivateStaffPayload) => activateStaffAccount(payload),
  })
}
