import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { Api, Session } from '../common/Api'
import { WarningItem, HelpRequestItem } from '../model/Models'
import { Theme } from '../common/Theme'
import { RedAlertService } from '../common/RedAlertService'
import { common } from '@kit.AbilityKit'

@Entry
@Component
struct ResidentHomePage {
  @State warnings: WarningItem[] = []
  @State requests: HelpRequestItem[] = []
  @State loading: boolean = false
  private redAlertTimer: number = -1

  aboutToAppear() {
    this.startRedAlertPolling()
  }

  aboutToDisappear() {
    this.stopRedAlertPolling()
  }

  // 每次页面显示时刷新（含从提交求助/避难所等子页返回），保证列表实时
  onPageShow() {
    this.loadData()
    RedAlertService.checkOnce()
  }

  startRedAlertPolling() {
    if (this.redAlertTimer !== -1) {
      return
    }
    RedAlertService.checkOnce()
    this.redAlertTimer = setInterval(() => {
      RedAlertService.checkOnce()
    }, 5000)
  }

  stopRedAlertPolling() {
    if (this.redAlertTimer !== -1) {
      clearInterval(this.redAlertTimer)
      this.redAlertTimer = -1
    }
  }

  // 退出登录：清空会话（内存+本地持久化）并返回登录页
  async logout() {
    await Session.clear(getContext(this) as common.UIAbilityContext)
    router.replaceUrl({ url: 'pages/LoginPage' })
  }

  async loadData() {
    this.loading = true

    try {
      // getList 自动解包分页 results
      this.warnings = await Api.getList<WarningItem>('/warnings/?is_active=true')
      this.requests = await Api.getList<HelpRequestItem>('/help-requests/')
    } catch (err) {
      promptAction.showToast({ message: '加载失败，请检查后端服务' })
    } finally {
      this.loading = false
    }
  }

  async cancelRequest(id: number) {
    try {
      await Api.postEmpty(`/help-requests/${id}/cancel/`)
      promptAction.showToast({ message: '求助已取消' })
      this.loadData()
    } catch (err) {
      promptAction.showToast({ message: '取消失败' })
    }
  }

  // 快捷入口卡片按钮
  @Builder
  entryCard(icon: string, label: string, accent: string, tap: () => void) {
    Column() {
      Text(icon)
        .fontSize(26)
        .width(48)
        .height(48)
        .textAlign(TextAlign.Center)
        .backgroundColor('#1A' + accent.slice(1))
        .borderRadius(14)

      Text(label)
        .fontSize(13)
        .fontWeight(FontWeight.Medium)
        .fontColor(Theme.TEXT)
        .margin({ top: 10 })
    }
    .layoutWeight(1)
    .padding({ top: 16, bottom: 16 })
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
    .backgroundColor(Theme.CARD)
    .borderRadius(Theme.RADIUS)
    .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })
    .onClick(tap)
  }

  // 分区标题
  @Builder
  sectionHeader(title: string, count: number, accent: string) {
    Row() {
      Column()
        .width(4)
        .height(18)
        .backgroundColor(accent)
        .borderRadius(2)

      Text(title)
        .fontSize(18)
        .fontWeight(FontWeight.Bold)
        .fontColor(Theme.TEXT)
        .margin({ left: 10 })

      Text(`${count}`)
        .fontSize(12)
        .fontColor(Theme.TEXT_MUTED)
        .margin({ left: 8 })
    }
    .width('100%')
    .alignItems(VerticalAlign.Center)
  }

  build() {
    Column() {
      // 顶部渐变头部
      Row() {
        Column() {
          Row() {
            Text('🏠')
              .fontSize(22)
              .margin({ right: 8 })

            Text(`居民端 · ${Session.username}`)
              .fontSize(22)
              .fontWeight(FontWeight.Bold)
              .fontColor(Color.White)
          }
          .alignItems(VerticalAlign.Center)

          Text(`社区：${Session.community || '未填写'}`)
            .fontSize(13)
            .fontColor('#DBEAFE')
            .margin({ top: 8 })
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Start)

        Button('刷新')
          .height(38)
          .fontSize(14)
          .fontColor(Color.White)
          .backgroundColor('#33FFFFFF')
          .borderRadius(Theme.RADIUS_SM)
          .margin({ left: 8 })
          .onClick(() => {
            this.loadData()
          })

        Button('退出')
          .height(38)
          .fontSize(14)
          .fontColor(Color.White)
          .backgroundColor('#33FFFFFF')
          .borderRadius(Theme.RADIUS_SM)
          .margin({ left: 8 })
          .onClick(() => {
            this.logout()
          })
      }
      .width('100%')
      .padding({ left: 20, right: 20, top: 22, bottom: 26 })
      .alignItems(VerticalAlign.Center)
      .linearGradient({
        angle: 145,
        colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY, 0.55], [Theme.PRIMARY_DARK, 1.0]]
      })
      .borderRadius({ bottomLeft: 28, bottomRight: 28 })

      // 三个快捷入口卡片
      Row() {
        this.entryCard('🆘', '提交求助', Theme.DANGER, () => {
          router.pushUrl({ url: 'pages/SubmitHelpPage' })
        })

        Column()
          .width(12)

        this.entryCard('✉️', '站内消息', Theme.TEAL, () => {
          router.pushUrl({ url: 'pages/NotificationsPage' })
        })

        Column()
          .width(12)

        this.entryCard('🏥', '附近避难所', Theme.PURPLE, () => {
          router.pushUrl({ url: 'pages/NearbyShelterPage' })
        })
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 16 })

      // 预警 + 求助列表
      List({ space: 12 }) {
        ListItem() {
          Row() {
            Column().width(4).height(18).backgroundColor(Theme.WARN).borderRadius(2)
            Text('灾害预警').fontSize(18).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT).margin({ left: 10 })
            Text(`${this.warnings.length}`).fontSize(12).fontColor(Theme.TEXT_MUTED).margin({ left: 8 })
          }
          .width('100%').alignItems(VerticalAlign.Center)
        }
        .margin({ top: 8 })

        if (this.warnings.length === 0) {
          ListItem() {
            Column() {
              Text('🌤️')
                .fontSize(38)
              Text('暂无灾害预警')
                .fontSize(14)
                .fontColor(Theme.TEXT_MUTED)
                .margin({ top: 10 })
            }
            .width('100%')
            .padding({ top: 28, bottom: 28 })
            .justifyContent(FlexAlign.Center)
            .alignItems(HorizontalAlign.Center)
          }
        }

        ForEach(this.warnings, (item: WarningItem) => {
          ListItem() {
            Column() {
              Row() {
                Text(item.title)
                  .fontSize(17)
                  .fontWeight(FontWeight.Bold)
                  .fontColor(Theme.TEXT)
                  .layoutWeight(1)

                Text(item.level_display)
                  .fontSize(12)
                  .fontColor(Color.White)
                  .padding({ left: 10, right: 10, top: 4, bottom: 4 })
                  .backgroundColor(Theme.levelColor(item.level))
                  .borderRadius(12)
              }
              .width('100%')
              .alignItems(VerticalAlign.Center)

              Text(item.content)
                .fontSize(14)
                .fontColor(Theme.TEXT_BODY)
                .margin({ top: 10 })

              Text(`影响社区：${item.community || '全部社区'}`)
                .fontSize(12)
                .fontColor(Theme.TEXT_MUTED)
                .margin({ top: 8 })
            }
            .width('100%')
            .alignItems(HorizontalAlign.Start)
            .padding(16)
            .backgroundColor(Theme.CARD)
            .borderRadius(Theme.RADIUS)
            .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })
          }
        }, (item: WarningItem) => item.id.toString())

        ListItem() {
          Row() {
            Column().width(4).height(18).backgroundColor(Theme.PRIMARY).borderRadius(2)
            Text('我的求助').fontSize(18).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT).margin({ left: 10 })
            Text(`${this.requests.length}`).fontSize(12).fontColor(Theme.TEXT_MUTED).margin({ left: 8 })
          }
          .width('100%').alignItems(VerticalAlign.Center)
        }
        .margin({ top: 8 })

        if (this.requests.length === 0) {
          ListItem() {
            Column() {
              Text('📭')
                .fontSize(38)
              Text('还没有提交过求助')
                .fontSize(14)
                .fontColor(Theme.TEXT_MUTED)
                .margin({ top: 10 })
            }
            .width('100%')
            .padding({ top: 28, bottom: 28 })
            .justifyContent(FlexAlign.Center)
            .alignItems(HorizontalAlign.Center)
          }
        }

        ForEach(this.requests, (item: HelpRequestItem) => {
          ListItem() {
            Column() {
              Row() {
                Text(item.request_type_display)
                  .fontSize(17)
                  .fontWeight(FontWeight.Bold)
                  .fontColor(Theme.TEXT)
                  .layoutWeight(1)

                Text(item.status_display)
                  .fontSize(12)
                  .fontColor(Color.White)
                  .padding({ left: 10, right: 10, top: 4, bottom: 4 })
                  .backgroundColor(Theme.statusColor(item.status))
                  .borderRadius(12)
              }
              .width('100%')
              .alignItems(VerticalAlign.Center)

              // AI 智能摘要
              if (item.ai_summary) {
                Text(item.ai_summary)
                  .fontSize(13)
                  .fontColor(Theme.PRIMARY)
                  .padding({ left: 12, right: 12, top: 6, bottom: 6 })
                  .backgroundColor('#EBF5FF')
                  .borderRadius(10)
                  .margin({ top: 10 })
              }

              Text(item.description)
                .fontSize(14)
                .fontColor(Theme.TEXT_BODY)
                .margin({ top: 10 })

              Text(`地址：${item.address}`)
                .fontSize(12)
                .fontColor(Theme.TEXT_MUTED)
                .margin({ top: 8 })

              Row() {
                Text('紧急程度')
                  .fontSize(12)
                  .fontColor(Theme.TEXT_MUTED)

                Text(item.urgency_display)
                  .fontSize(12)
                  .fontColor(Color.White)
                  .padding({ left: 10, right: 10, top: 3, bottom: 3 })
                  .backgroundColor(Theme.urgencyColor(item.urgency))
                  .borderRadius(12)
                  .margin({ left: 8 })
              }
              .margin({ top: 8 })
              .alignItems(VerticalAlign.Center)

              if (item.status === 'pending' || item.status === 'assigned') {
                Button('取消求助')
                  .width('100%')
                  .height(40)
                  .fontSize(15)
                  .fontColor(Color.White)
                  .backgroundColor(Theme.DANGER)
                  .borderRadius(Theme.RADIUS_SM)
                  .margin({ top: 14 })
                  .onClick(() => {
                    this.cancelRequest(item.id)
                  })
              }
            }
            .width('100%')
            .alignItems(HorizontalAlign.Start)
            .padding(16)
            .backgroundColor(Theme.CARD)
            .borderRadius(Theme.RADIUS)
            .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })
          }
        }, (item: HelpRequestItem) => `${item.id}-${item.status}`)

        ListItem() {
          Column()
            .height(12)
        }
      }
      .layoutWeight(1)
      .width('100%')
      .padding({ left: 16, right: 16 })
      .scrollBar(BarState.Off)
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG)
  }
}