import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { Api, Session } from '../common/Api'
import { NotificationItem } from '../model/Models'

@Entry
@Component
struct NotificationsPage {
  @State notifications: NotificationItem[] = []
  @State loading: boolean = false

  aboutToAppear() {
    this.loadData()
  }

  async loadData() {
    this.loading = true

    try {
      this.notifications = await Api.get('/notifications/') as NotificationItem[]
    } catch (err) {
      promptAction.showToast({ message: '消息加载失败' })
    } finally {
      this.loading = false
    }
  }

  async markRead(id: number) {
    try {
      await Api.postEmpty(`/notifications/${id}/mark_read/`)
      promptAction.showToast({ message: '已标记为已读' })
      this.loadData()
    } catch (err) {
      promptAction.showToast({ message: '操作失败' })
    }
  }

  categoryColor(category: string): string {
    if (category === 'warning') return '#DC2626'
    if (category === 'help_request') return '#D97706'
    if (category === 'task') return '#2563EB'
    return '#64748B'
  }

  build() {
    Column() {
      Row() {
        Text(`站内消息 · ${Session.username}`)
          .fontSize(22)
          .fontWeight(FontWeight.Bold)
          .fontColor(Color.White)
          .layoutWeight(1)

        Button('返回')
          .height(34)
          .backgroundColor('#1D4ED8')
          .onClick(() => {
            router.back()
          })
      }
      .width('100%')
      .padding(18)
      .backgroundColor('#2563EB')

      Button('刷新消息')
        .width('90%')
        .height(42)
        .backgroundColor('#2563EB')
        .margin({ top: 14, bottom: 10 })
        .onClick(() => {
          this.loadData()
        })

      List() {
        ForEach(this.notifications, (item: NotificationItem) => {
          ListItem() {
            Column() {
              Row() {
                Text(item.title)
                  .fontSize(17)
                  .fontWeight(FontWeight.Bold)
                  .layoutWeight(1)

                Text(item.is_read ? '已读' : '未读')
                  .fontSize(12)
                  .fontColor(Color.White)
                  .padding({ left: 8, right: 8, top: 4, bottom: 4 })
                  .backgroundColor(item.is_read ? '#64748B' : '#DC2626')
                  .borderRadius(12)
              }

              Text(item.category_display)
                .fontSize(12)
                .fontColor(Color.White)
                .padding({ left: 8, right: 8, top: 4, bottom: 4 })
                .backgroundColor(this.categoryColor(item.category))
                .borderRadius(12)
                .margin({ top: 8 })

              Text(item.content)
                .fontSize(14)
                .fontColor('#475569')
                .margin({ top: 10 })

              Text(item.created_at ? item.created_at.replace('T', ' ').slice(0, 19) : '')
                .fontSize(12)
                .fontColor('#94A3B8')
                .margin({ top: 8 })

              if (!item.is_read) {
                Button('标记已读')
                  .height(36)
                  .backgroundColor('#2563EB')
                  .margin({ top: 12 })
                  .onClick(() => {
                    this.markRead(item.id)
                  })
              }
            }
            .width('100%')
            .padding(14)
            .backgroundColor(Color.White)
            .borderRadius(14)
            .margin({ left: 16, right: 16, bottom: 12 })
          }
        }, (item: NotificationItem) => item.id.toString())
      }
      .layoutWeight(1)
      .width('100%')
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F1F5F9')
  }
}