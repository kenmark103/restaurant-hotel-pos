export interface StaffMember {
  id: number
  email: string
  full_name: string
  role: string
  status: string
  branch_id: number | null
}

export type StaffRead = StaffMember
