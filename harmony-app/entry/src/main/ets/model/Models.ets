export interface UserInfo {
  id: number
  username: string
  email: string
  role: string
  role_display: string
  phone: string
  community: string
  address: string
}

export interface LoginResponse {
  message: string
  token: string
  user: UserInfo
}

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

export interface HelpRequestItem {
  id: number
  resident: number
  resident_name: string
  request_type: string
  request_type_display: string
  urgency: string
  urgency_display: string
  description: string
  address: string
  latitude: string
  longitude: string
  status: string
  status_display: string
  created_at: string
  updated_at: string
  completed_at: string
}

export interface TaskItem {
  id: number
  help_request: number
  volunteer: number
  volunteer_name: string
  status: string
  status_display: string
  feedback: string
  help_request_description: string
  help_request_type: string
  help_request_address: string
  assigned_at: string
  accepted_at: string
  completed_at: string
}

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

export interface EmptyPayload {
}

export interface LoginPayload {
  username: string
  password: string
}

export interface SubmitHelpPayload {
  request_type: string
  urgency: string
  description: string
  address: string
}

export interface CompleteTaskPayload {
  feedback: string
}