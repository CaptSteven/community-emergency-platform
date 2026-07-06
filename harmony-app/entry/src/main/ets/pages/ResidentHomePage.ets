import router from '@ohos.router'
import { Session } from '../common/Api'
import { Theme } from '../common/Theme'
import { common } from '@kit.AbilityKit'

// 居民端主页：纯社区服务，无任何灾害预警 / 应急求助入口。
@Entry
@Component
struct ResidentHomePage {
  // 退出登录：清空会话（内存+本地持久化）并返回登录页
  async logout() {
    await Session.clear(getContext(this) as common.UIAbilityContext)
    router.replaceUrl({ url: 'pages/LoginPage' })
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

      // 社区长期服务主入口（居民端首要入口，突出的渐变卡片）
      Row() {
        Text('🛎️')
          .fontSize(30).width(54).height(54).textAlign(TextAlign.Center)
          .backgroundColor('#33FFFFFF').borderRadius(16)
        Column() {
          Text('我的社区服务')
            .fontSize(Theme.FS_SUBTITLE).fontWeight(FontWeight.Bold).fontColor(Color.White)
          Text('申请周期上门 · 长者关怀 · 健康记录')
            .fontSize(Theme.FS_SMALL).fontColor('#E0F2F1').margin({ top: 4 })
        }.layoutWeight(1).alignItems(HorizontalAlign.Start).margin({ left: 14 })
        Text('›').fontSize(30).fontColor(Color.White)
      }
      .width('90%').padding({ left: 16, right: 18, top: 14, bottom: 14 })
      .margin({ top: 16 }).alignItems(VerticalAlign.Center)
      .borderRadius(Theme.RADIUS)
      .linearGradient({ angle: 120, colors: [[Theme.SUCCESS, 0.0], [Theme.TEAL, 1.0]] })
      .shadow({ radius: 16, color: '#3316A34A', offsetX: 0, offsetY: 6 })
      .onClick(() => { router.pushUrl({ url: 'pages/ResidentServicePage' }) })

      // 站内消息入口
      Row() {
        Text('✉️')
          .fontSize(24).width(48).height(48).textAlign(TextAlign.Center)
          .backgroundColor(Theme.PRIMARY_LIGHT_BG).borderRadius(14)
        Column() {
          Text('站内消息')
            .fontSize(Theme.FS_SUBTITLE).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT)
          Text('查看社区通知与服务进度')
            .fontSize(Theme.FS_SMALL).fontColor(Theme.TEXT_MUTED).margin({ top: 4 })
        }.layoutWeight(1).alignItems(HorizontalAlign.Start).margin({ left: 14 })
        Text('›').fontSize(28).fontColor(Theme.TEXT_MUTED)
      }
      .width('90%').padding({ left: 16, right: 18, top: 14, bottom: 14 })
      .margin({ top: 14 }).alignItems(VerticalAlign.Center)
      .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
      .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })
      .onClick(() => { router.pushUrl({ url: 'pages/NotificationsPage' }) })

      // 欢迎 / 说明卡片
      Column() {
        Text('🤝')
          .fontSize(46).margin({ bottom: 12 })
        Text('欢迎使用社区服务')
          .fontSize(Theme.FS_SUBTITLE).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT)
        Text('在这里申请周期上门、长者关怀与健康记录服务，\n志愿者会按约定时间为您提供贴心帮助。')
          .fontSize(Theme.FS_SMALL).fontColor(Theme.TEXT_BODY).textAlign(TextAlign.Center)
          .lineHeight(20).margin({ top: 10 })
      }
      .width('90%').padding({ top: 28, bottom: 28, left: 16, right: 16 })
      .margin({ top: 16 })
      .justifyContent(FlexAlign.Center).alignItems(HorizontalAlign.Center)
      .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
      .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })

      Blank()
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG)
  }
}
