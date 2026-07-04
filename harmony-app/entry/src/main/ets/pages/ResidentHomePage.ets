import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { Api, Session } from '../common/Api'
import { WarningItem, HelpRequestItem } from '../model/Models'

@Entry
@Component
struct ResidentHomePage {
  @State warnings: WarningItem[] = []
  @State requests: HelpRequestItem[] = []
  @State loading: boolean = false

  aboutToAppear() {
    this.loadData()
  }

  async loadData() {
    this.loading = true

    try {
      this.warnings = await Api.get('/warnings/') as WarningItem[]
      this.requests = await Api.get('/help-requests/') as HelpRequestItem[]
    } catch (err) {
      promptAction.showToast({ message: '加载失败，请检查后端服务' })
    } finally {
      this.loading = false
    }
  }

  levelColor(level: string): string {
    if (level === 'red') return '#DC2626'
    if (level === 'orange') return '#EA580C'
    if (level === 'yellow') return '#D97706'
    return '#2563EB'
  }

  statusColor(status: string): string {
    if (status === 'completed') return '#16A34A'
    if (status === 'pending') return '#D97706'
    if (status === 'assigned' || status === 'processing') return '#2563EB'
    return '#64748B'
  }

  build() {
    Column() {
      Row() {
        Column() {
          Text(`居民端 · ${Session.username}`)
            .fontSize(22)
            .fontWeight(FontWeight.Bold)
            .fontColor(Color.White)

          Text('查看预警、提交求助、跟踪处理进度')
            .fontSize(13)
            .fontColor('#DBEAFE')
            .margin({ top: 6 })
        }
        .layoutWeight(1)

        Button('刷新')
          .height(36)
          .backgroundColor('#1D4ED8')
          .onClick(() => {
            this.loadData()
          })
      }
      .width('100%')
      .padding(18)
      .backgroundColor('#2563EB')

      Row() {
        Button('提交求助')
          .layoutWeight(1)
          .height(44)
          .backgroundColor('#EF4444')
          .onClick(() => {
            router.pushUrl({ url: 'pages/SubmitHelpPage' })
          })

        Button('站内消息')
          .layoutWeight(1)
          .height(44)
          .backgroundColor('#0F766E')
          .margin({ left: 12 })
          .onClick(() => {
            router.pushUrl({ url: 'pages/NotificationsPage' })
          })
      }
      .width('100%')
      .padding(16)

      List() {
        ListItem() {
          Text('灾害预警')
            .fontSize(20)
            .fontWeight(FontWeight.Bold)
            .margin({ left: 16, top: 8, bottom: 8 })
        }

        ForEach(this.warnings, (item: WarningItem) => {
          ListItem() {
            Column() {
              Row() {
                Text(item.title)
                  .fontSize(17)
                  .fontWeight(FontWeight.Bold)
                  .layoutWeight(1)

                Text(item.level_display)
                  .fontSize(12)
                  .fontColor(Color.White)
                  .padding({ left: 8, right: 8, top: 4, bottom: 4 })
                  .backgroundColor(this.levelColor(item.level))
                  .borderRadius(12)
              }

              Text(item.content)
                .fontSize(14)
                .fontColor('#475569')
                .margin({ top: 10 })

              Text(`影响社区：${item.community || '全部社区'}`)
                .fontSize(12)
                .fontColor('#64748B')
                .margin({ top: 8 })
            }
            .width('100%')
            .padding(14)
            .backgroundColor(Color.White)
            .borderRadius(14)
            .margin({ left: 16, right: 16, bottom: 12 })
          }
        }, (item: WarningItem) => item.id.toString())

        ListItem() {
          Text('我的求助')
            .fontSize(20)
            .fontWeight(FontWeight.Bold)
            .margin({ left: 16, top: 12, bottom: 8 })
        }

        ForEach(this.requests, (item: HelpRequestItem) => {
          ListItem() {
            Column() {
              Row() {
                Text(item.request_type_display)
                  .fontSize(17)
                  .fontWeight(FontWeight.Bold)
                  .layoutWeight(1)

                Text(item.status_display)
                  .fontSize(12)
                  .fontColor(Color.White)
                  .padding({ left: 8, right: 8, top: 4, bottom: 4 })
                  .backgroundColor(this.statusColor(item.status))
                  .borderRadius(12)
              }

              Text(item.description)
                .fontSize(14)
                .fontColor('#475569')
                .margin({ top: 10 })

              Text(`地址：${item.address}`)
                .fontSize(12)
                .fontColor('#64748B')
                .margin({ top: 8 })

              Text(`紧急程度：${item.urgency_display}`)
                .fontSize(12)
                .fontColor('#64748B')
                .margin({ top: 4 })
            }
            .width('100%')
            .padding(14)
            .backgroundColor(Color.White)
            .borderRadius(14)
            .margin({ left: 16, right: 16, bottom: 12 })
          }
        }, (item: HelpRequestItem) => item.id.toString())
      }
      .layoutWeight(1)
      .width('100%')
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F1F5F9')
  }
}