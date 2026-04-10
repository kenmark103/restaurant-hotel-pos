export interface TableRecord {
  id: number
  branch_id: number
  table_number: string
  capacity: number
  status: 'available' | 'occupied' | 'reserved' | 'cleaning'
  qr_code_token: string
}
