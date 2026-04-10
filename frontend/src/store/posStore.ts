import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

type PosState = {
  activeBranchId: number | null
  setActiveBranchId: (branchId: number | null) => void
}

export const usePosStore = create<PosState>()(
  persist(
    (set) => ({
      activeBranchId: null,
      setActiveBranchId: (activeBranchId) => set({ activeBranchId }),
    }),
    {
      name: 'pos-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ activeBranchId: state.activeBranchId }),
    },
  ),
)
