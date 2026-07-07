import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { Api, Session } from '../common/Api'
import { NotificationItem } from '../model/Models'
import { Theme } from '../common/Theme'

@Entry
@Component
struct NotificationsPage {
  @State notifications: NotificationItem[] = []
  @State loading: boolean = false

  // 每次页面显示时刷新，保证通知实时
  onPageShow() {
    this.loadData()
  }

  async loadData() {
    this.loading = true

    try {
      this.notifications = await Api.getList<NotificationItem>('/notifications/')
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

  async markAllRead() {
    try {
      await Api.postEmpty('/notifications/mark_all_read/')
      promptAction.showToast({ message: '全部已标记为已读' })
      this.loadData()
    } catch (err) {
      promptAction.showToast({ message: '操作失败' })
    }
  }

  // 点击条目：弹窗看全文，并把未读标为已读
  openDetail(item: NotificationItem) {
    promptAction.showDialog({
      title: item.title,
      message: item.content + '\n\n' + (item.created_at ? item.created_at.replace('T', ' ').slice(0, 19) : ''),
      buttons: [{ text: '知道了', color: '#2563EB' }]
    }).catch(() => {})
    if (!item.is_read) {
      this.markRead(item.id)
    }
  }

  categoryColor(category: string): string {
    if (category === 'service') return '#16A34A'
    if (category === 'system') return '#64748B'
    if (category === 'warning') return '#DC2626'
    if (category === 'help_request') return '#D97706'
    if (category === 'task') return '#2563EB'
    return '#64748B'
  }

  build() {
    Column() {
      // 顶部渐变头部
      Column() {
        Row() {
          Text('🔔')
            .fontSize(30)
            .margin({ right: 10 })

          Column() {
            Text('站内消息')
              .fontSize(24)
              .fontWeight(FontWeight.Bold)
              .fontColor(Color.White)

            Text(Session.username)
              .fontSize(13)
              .fontColor('#DBEAFE')
              .margin({ top: 4 })
          }
          .alignItems(HorizontalAlign.Start)
          .layoutWeight(1)

          Button('返回')
            .height(36)
            .fontSize(14)
            .fontColor(Theme.PRIMARY)
            .backgroundColor(Color.White)
            .borderRadius(Theme.RADIUS_SM)
            .padding({ left: 16, right: 16 })
            .onClick(() => {
              router.back()
            })
        }
        .width('100%')
        .alignItems(VerticalAlign.Center)
      }
      .width('100%')
      .padding({ left: 20, right: 20, top: 28, bottom: 24 })
      .linearGradient({
        angle: 145,
        colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY, 0.55], [Theme.PRIMARY_DARK, 1.0]]
      })
      .borderRadius({ bottomLeft: 28, bottomRight: 28 })

      // 刷新按钮 + 全部已读
      Row() {
        Button(this.loading ? '刷新中...' : '刷新消息')
          .layoutWeight(1)
          .height(46)
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
          .fontColor(Color.White)
          .borderRadius(Theme.RADIUS_SM)
          .enabled(!this.loading)
          .linearGradient({
            angle: 90,
            colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY_DARK, 1.0]]
          })
          .shadow({ radius: 12, color: '#332563EB', offsetX: 0, offsetY: 4 })
          .onClick(() => {
            this.loadData()
          })

        Button('全部已读')
          .layoutWeight(1)
          .height(46)
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
          .fontColor(Theme.PRIMARY)
          .backgroundColor('#EBF5FF')
          .borderRadius(Theme.RADIUS_SM)
          .margin({ left: 10 })
          .onClick(() => {
            this.markAllRead()
          })
      }
      .width('90%')
      .margin({ top: 16, bottom: 6 })

      if (this.notifications.length === 0) {
        // 空状态
        Column() {
          Text('📭')
            .fontSize(56)
            .margin({ bottom: 14 })

          Text('暂无站内消息')
            .fontSize(16)
            .fontWeight(FontWeight.Medium)
            .fontColor(Theme.TEXT_BODY)

          Text('社区服务与系统通知会显示在这里')
            .fontSize(13)
            .fontColor(Theme.TEXT_MUTED)
            .margin({ top: 8 })
        }
        .width('100%')
        .layoutWeight(1)
        .justifyContent(FlexAlign.Center)
        .alignItems(HorizontalAlign.Center)
      } else {
        // 条栏式：每条消息一行紧凑条目，点击查看全文并标记已读
        List({ space: 8 }) {
          ForEach(this.notifications, (item: NotificationItem) => {
            ListItem() {
              Row() {
                // 分类色点
                Column()
                  .width(10).height(10).borderRadius(5)
                  .backgroundColor(this.categoryColor(item.category))
                  .margin({ right: 12 })

                Column() {
                  Row() {
                    Text(item.title)
                      .fontSize(15).fontWeight(FontWeight.Medium).fontColor(Theme.TEXT)
                      .layoutWeight(1).maxLines(1).textOverflow({ overflow: TextOverflow.Ellipsis })
                    Text(item.created_at ? item.created_at.slice(5, 16).replace('T', ' ') : '')
                      .fontSize(11).fontColor(Theme.TEXT_MUTED).margin({ left: 8 })
                  }.width('100%').alignItems(VerticalAlign.Center)

                  Text(item.content)
                    .fontSize(13).fontColor(Theme.TEXT_MUTED)
                    .maxLines(1).textOverflow({ overflow: TextOverflow.Ellipsis })
                    .margin({ top: 4 }).width('100%')
                }
                .layoutWeight(1).alignItems(HorizontalAlign.Start)

                // 未读红点
                if (!item.is_read) {
                  Column().width(8).height(8).borderRadius(4)
                    .backgroundColor(Theme.DANGER).margin({ left: 10 })
                }
              }
              .width('100%')
              .padding({ left: 14, right: 14, top: 12, bottom: 12 })
              .backgroundColor(Theme.CARD)
              .borderRadius(12)
              .onClick(() => { this.openDetail(item) })
            }
          }, (item: NotificationItem) => item.id.toString())
        }
        .layoutWeight(1)
        .width('100%')
        .padding({ left: 16, right: 16, top: 10, bottom: 6 })
        .scrollBar(BarState.Off)
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG)
  }
}