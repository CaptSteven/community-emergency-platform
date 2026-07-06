import { Api } from './Api'
import { NotificationItem } from '../model/Models'

export class RedAlertService {
  private static checking: boolean = false
  private static dialogShowing: boolean = false
  private static showingIds: string = ','

  static async checkOnce(): Promise<void> {
    if (RedAlertService.checking || RedAlertService.dialogShowing) {
      return
    }

    RedAlertService.checking = true

    try {
      let alerts: NotificationItem[] = await Api.getList<NotificationItem>('/notifications/red-alerts/')
      if (alerts.length === 0) {
        return
      }

      let alert = alerts[0]
      let key = `,${alert.id},`
      if (RedAlertService.showingIds.indexOf(key) >= 0) {
        return
      }

      RedAlertService.showingIds = `${RedAlertService.showingIds}${alert.id},`
      RedAlertService.dialogShowing = true

      AlertDialog.show({
        title: '🚨 红色预警',
        message: `${alert.title}\n\n${alert.content}`,
        autoCancel: false,
        alignment: DialogAlignment.Center,
        primaryButton: {
          value: '我已知晓',
          action: () => {
            RedAlertService.markRead(alert.id)
            RedAlertService.dialogShowing = false
          }
        }
      })
    } catch (err) {
      // 红色预警轮询不能影响首页正常使用，网络异常时静默等待下一轮。
    } finally {
      RedAlertService.checking = false
    }
  }

  private static async markRead(id: number): Promise<void> {
    try {
      await Api.postEmpty(`/notifications/${id}/mark_read/`)
    } catch (err) {
      // 标记失败时移除本地去重标记，下一轮轮询会再次提醒。
      RedAlertService.showingIds = RedAlertService.showingIds.replace(`,${id},`, ',')
    }
  }
}
