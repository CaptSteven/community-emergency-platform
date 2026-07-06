// 统一设计系统：品牌配色、圆角、间距，以及预警等级 / 求助状态 / 紧急程度的语义色。
// 所有页面共用，避免颜色散落硬编码，保证整体视觉一致、美观。

export class Theme {
  // 品牌主色（用于渐变头部、主按钮）
  static readonly PRIMARY: string = '#2563EB'
  static readonly PRIMARY_DARK: string = '#1D4ED8'
  static readonly PRIMARY_LIGHT: string = '#3B82F6'

  // 背景 / 卡片
  static readonly BG: string = '#EEF2F7'
  static readonly CARD: string = '#FFFFFF'

  // 文字层级
  static readonly TEXT: string = '#0F172A'
  static readonly TEXT_BODY: string = '#475569'
  static readonly TEXT_MUTED: string = '#94A3B8'
  static readonly ON_PRIMARY: string = '#FFFFFF'
  static readonly BORDER: string = '#E2E8F0'

  // 功能强调色
  static readonly DANGER: string = '#EF4444'
  static readonly SUCCESS: string = '#16A34A'
  static readonly WARN: string = '#EA580C'
  static readonly TEAL: string = '#0D9488'
  static readonly PURPLE: string = '#7C3AED'

  // 圆角 / 间距
  static readonly RADIUS: number = 18
  static readonly RADIUS_SM: number = 12
  static readonly GAP: number = 12
  static readonly PAD: number = 16

  // 预警等级色（red/orange/yellow/blue）
  static levelColor(level: string): string {
    if (level === 'red') return '#DC2626'
    if (level === 'orange') return '#EA580C'
    if (level === 'yellow') return '#D97706'
    if (level === 'blue') return '#2563EB'
    return '#64748B'
  }

  // 求助 / 任务状态色
  static statusColor(status: string): string {
    if (status === 'completed') return '#16A34A'
    if (status === 'pending') return '#D97706'
    if (status === 'assigned') return '#2563EB'
    if (status === 'processing') return '#7C3AED'
    if (status === 'cancelled') return '#94A3B8'
    return '#64748B'
  }

  // 紧急程度色（high/medium/low）
  static urgencyColor(urgency: string): string {
    if (urgency === 'high') return '#DC2626'
    if (urgency === 'medium') return '#EA580C'
    if (urgency === 'low') return '#16A34A'
    return '#64748B'
  }
}
