// ============================================================
// 数据模型 — 匹配后端 build_user_response() 与各序列化器
// 组长 feature/backend-web-admin-v3 最新格式，扁平化 user 对象
// ============================================================

// ---- 用户（登录/注册/me 返回的扁平 user） ----
export interface UserInfo {
  id: number
  username: string
  email: string
  role: string
  role_display: string
  phone: string
  community: string
  address: string
  skills: string
  current_latitude: number | null
  current_longitude: number | null
  location_updated_at: string | null
  is_available: boolean
}

// ---- 登录 / 注册 响应 ----
export interface LoginResponse {
  message: string
  token: string
  user: UserInfo
}

export interface RegisterResponse {
  message: string
  token: string
  user: UserInfo
}

// ---- /auth/me/ 响应（嵌套了一层 user） ----
export interface MeResponse {
  user: UserInfo
}

// ---- 灾害预警 ----
export interface WarningItem {
  id: number
  title: string
  warning_type: string
  warning_type_display: string
  level: string
  level_display: string
  content: string
  community: string
  publisher_name: string
  is_active: boolean
  created_at: string
  updated_at: string
}

// ---- 居民求助（含后端自动生成的 ai_summary） ----
export interface HelpRequestItem {
  id: number
  resident: number
  resident_name: string
  request_type: string
  request_type_display: string
  urgency: string
  urgency_display: string
  description: string
  ai_summary: string
  address: string
  latitude: number | null
  longitude: number | null
  status: string
  status_display: string
  created_at: string
  updated_at: string
  completed_at: string | null
}

// ---- 志愿者任务 ----
export interface TaskItem {
  id: number
  help_request: number
  volunteer: number | null
  volunteer_name: string
  status: string
  status_display: string
  feedback: string
  help_request_description: string
  help_request_type: string
  help_request_address: string
  help_request_latitude: string | null
  help_request_longitude: string | null
  assigned_at: string
  accepted_at: string | null
  completed_at: string | null
}

// ---- 站内消息 ----
export interface NotificationItem {
  id: number
  recipient: number
  recipient_name: string
  title: string
  content: string
  category: string
  category_display: string
  is_read: boolean
  related_type: string
  related_id: number
  created_at: string
}

// ---- 附近避难所（GET /shelters/ 或 /shelters/nearby/ 返回项） ----
export interface ShelterItem {
  id: number
  name: string
  address: string
  capacity: number
  contact_phone: string
  latitude?: string
  longitude?: string
  is_available: boolean
  created_at: string
  distance_km?: number
}

// ---- 应急物资 ----
export interface MaterialItem {
  id: number
  name: string
  category: string
  category_display: string
  quantity: number
  unit: string
  storage_location: string
  warning_quantity: number
  is_low_stock: boolean
  lifecycle_status: string
  lifecycle_status_display: string
  expire_date: string | null
  expiry_warning_days: number
}

// ============================================================
// 请求载荷（Payload）
// ============================================================

export interface EmptyPayload {
}

export interface LoginPayload {
  username: string
  password: string
}

// 注册载荷 — 匹配 UserRegisterSerializer
export interface RegisterPayload {
  username: string
  password: string
  email?: string
  role: string            // 'resident' | 'volunteer'
  phone?: string
  community?: string
  address?: string
  skills?: string         // 志愿者必填，空格分隔关键词
  current_latitude?: number
  current_longitude?: number
}

export interface SubmitHelpPayload {
  request_type: string
  urgency: string
  description: string
  address: string
  latitude?: string
  longitude?: string
}

export interface CompleteTaskPayload {
  feedback: string
}

// 设备推送令牌上报载荷（Push Kit）
export interface DeviceTokenPayload {
  push_token: string
  platform: string
}

// 位置上报载荷
export interface UpdateLocationPayload {
  current_latitude: number
  current_longitude: number
}

// 位置上报响应
export interface UpdateLocationResponse {
  message: string
  current_latitude: number
  current_longitude: number
  location_updated_at: string
}

// ---- 定位结果（Location Kit） ----
export interface LocationResult {
  latitude: number
  longitude: number
}

// ============================================================
// 后端 DRF 分页统一格式
// ============================================================
export interface PaginatedList<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}