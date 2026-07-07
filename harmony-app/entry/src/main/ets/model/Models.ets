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

// ---- 社区服务：服务类型目录 ----
export interface ServiceTypeItem {
  id: number
  name: string
  code: string
  category: string
  description: string
  required_skill: string
  default_frequency: string
  default_frequency_display: string
  duration_minutes: number
  needs_health_record: boolean
  icon: string
  is_active: boolean
}

// ---- 社区服务：服务计划/订阅 ----
export interface ServiceSubscriptionItem {
  id: number
  resident: number
  resident_name: string
  service_type: number
  service_type_name: string
  service_type_icon: string
  frequency: string
  frequency_display: string
  preferred_weekday: number
  preferred_weekday_display: string
  preferred_slot: number | null       // 标准整点时段槽（8..19），null=不限
  preferred_slot_display: string
  address: string
  note: string
  is_active: boolean
  start_date: string | null
  last_generated_date: string | null
  created_at: string
}

// ---- 社区服务：上门工单 ----
export interface ServiceVisitItem {
  id: number
  subscription: number | null
  service_type: number
  service_type_name: string
  service_type_icon: string
  needs_health_record: boolean
  resident: number
  resident_name: string
  volunteer: number | null
  volunteer_name: string
  scheduled_date: string
  scheduled_slot: number | null      // 预约整点时段槽（8..19），DDL=槽结束
  slot_display: string
  status: string
  status_display: string
  address: string
  latitude: number | null
  longitude: number | null
  note: string             // 需求说明（居民提交单次任务时填写）
  duration_minutes: number // 本次服务时长（分钟）
  feedback: string
  completion_photo: string | null
  confirm_photo: string | null     // 居民确认时上传的凭证照片
  checkin_photo: string | null     // 到场报到照片
  checkin_distance_m: number | null // 报到距服务地址的距离（米）
  checkin_remote: boolean          // 远程报到（距离异常）
  systolic: number | null
  diastolic: number | null
  heart_rate: number | null
  temperature: number | null
  health_note: string
  started_at: string | null
  completed_at: string | null
  confirmed_at: string | null      // 居民确认完成时间
  created_at: string
}

// ============================================================
// 请求载荷（Payload）
// ============================================================

export interface EmptyPayload {
}

// 完成上门服务载荷（志愿者录入健康记录/反馈）
export interface CompleteVisitPayload {
  feedback: string
  health_note: string
  systolic?: number
  diastolic?: number
  heart_rate?: number
  temperature?: number
}

// 取消上门服务载荷
export interface CancelVisitPayload {
  reason: string
  note: string
}

// 到场报到载荷（定位必须；照片报到成功后单独补传）
export interface CheckinPayload {
  latitude: number
  longitude: number
}

// 居民提交单次任务载荷（无订阅、待管理员派单）
export interface RequestOncePayload {
  service_type: number
  address: string
  note: string
  scheduled_date?: string   // 可选期望日期（YYYY-MM-DD，今天~未来14天）
  scheduled_slot?: number   // 可选期望时段槽（8..19）
}

// 志愿者本人服务统计（积分与时长）
export interface MyStats {
  points: number
  total_minutes: number
  week_minutes: number
  completed_count: number
}

// 站内消息未读数（GET /notifications/unread_count/）
export interface UnreadCount {
  unread_count: number
}

// 志愿积分排行榜条目
export interface LeaderboardItem {
  rank: number
  volunteer: string
  points: number
  total_minutes: number
  week_minutes: number
  completed_count: number
}

// 志愿者线上申请载荷
export interface VolunteerApplyPayload {
  username: string
  password: string
  phone: string
  community: string
  address: string
  skills: string
  note: string
}

// 居民申请周期服务载荷
export interface CreateSubscriptionPayload {
  service_type: number
  frequency: string
  preferred_weekday: number
  preferred_slot: number | null
  note: string
  address: string          // 上门服务地址（居民可指定）
  is_active?: boolean       // 编辑(PUT)时保留生效/暂停状态
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