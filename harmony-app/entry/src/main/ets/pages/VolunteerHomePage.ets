import router from '@ohos.router'
import { Api, Session } from '../common/Api'
import { LocationService } from '../common/LocationService'
import { common } from '@kit.AbilityKit'
import { UpdateLocationPayload, LocationResult } from '../model/Models'
import { Theme } from '../common/Theme'

// 志愿者端主页：纯社区服务，无任何应急任务 / 灾害预警。
// 仅保留后台定位上报（供社区上门服务派单参考），静默运行、不打扰用户。
@Entry
@Component
struct VolunteerHomePage {
  private reportTimer: number = -1

  aboutToAppear() {
    this.reportLocation()
    this.reportTimer = setInterval(() => {
      this.reportLocation()
    }, 60000)
  }

  aboutToDisappear() {
    if (this.reportTimer !== -1) {
      clearInterval(this.reportTimer)
      this.reportTimer = -1
    }
  }

  async logout() {
    await Session.clear(getContext(this) as common.UIAbilityContext)
    router.replaceUrl({ url: 'pages/LoginPage' })
  }

  // 后台静默上报当前定位，便于社区服务就近派单
  async reportLocation() {
    try {
      let loc: LocationResult = await LocationService.getCurrentLocation()
      let payload: UpdateLocationPayload = {
        current_latitude: loc.latitude,
        current_longitude: loc.longitude
      }
      await Api.post<UpdateLocationPayload>('/auth/update-location/', payload)
    } catch (err) {
      // 静默失败
    }
  }

  build() {
    Column() {
      // 顶部渐变头部
      Row() {
        Column() {
          Row() {
            Text('🦺').fontSize(22)
            Text(`志愿者端 · ${Session.username}`)
              .fontSize(21).fontWeight(FontWeight.Bold).fontColor(Color.White).margin({ left: 8 })
          }.alignItems(VerticalAlign.Center)
          Text(`技能：${Session.skills || '未填写'}`)
            .fontSize(13).fontColor('#DBEAFE').margin({ top: 8 })
        }.layoutWeight(1).alignItems(HorizontalAlign.Start)

        Button('退出')
          .height(38).fontSize(14).fontColor(Color.White).backgroundColor('#33FFFFFF')
          .borderRadius(Theme.RADIUS_SM)
          .onClick(() => { this.logout() })
      }
      .width('100%').padding({ left: 20, right: 20, top: 22, bottom: 26 }).alignItems(VerticalAlign.Center)
      .linearGradient({
        angle: 145,
        colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY, 0.55], [Theme.PRIMARY_DARK, 1.0]]
      }).borderRadius({ bottomLeft: 28, bottomRight: 28 })

      // 社区长期服务主入口（志愿者端首要入口，突出的渐变卡片，与头部叠层）
      Row() {
        Text('🩺')
          .fontSize(30).width(54).height(54).textAlign(TextAlign.Center)
          .backgroundColor('#33FFFFFF').borderRadius(16)
        Column() {
          Text('我的上门服务')
            .fontSize(Theme.FS_SUBTITLE).fontWeight(FontWeight.Bold).fontColor(Color.White)
          Text('社区长期服务 · 长者关怀 · 录入健康记录')
            .fontSize(Theme.FS_SMALL).fontColor('#E0F2F1').margin({ top: 4 })
        }.layoutWeight(1).alignItems(HorizontalAlign.Start).margin({ left: 14 })
        Text('›').fontSize(30).fontColor(Color.White)
      }
      .width('90%').padding({ left: 16, right: 18, top: 14, bottom: 14 })
      .margin({ top: -16 }).alignItems(VerticalAlign.Center)
      .borderRadius(Theme.RADIUS)
      .linearGradient({ angle: 120, colors: [[Theme.SUCCESS, 0.0], [Theme.TEAL, 1.0]] })
      .shadow({ radius: 16, color: '#3316A34A', offsetX: 0, offsetY: 6 })
      .onClick(() => { router.pushUrl({ url: 'pages/VolunteerServicePage' }) })

      // 站内消息入口
      Row() {
        Text('✉️')
          .fontSize(24).width(48).height(48).textAlign(TextAlign.Center)
          .backgroundColor(Theme.PRIMARY_LIGHT_BG).borderRadius(14)
        Column() {
          Text('站内消息')
            .fontSize(Theme.FS_SUBTITLE).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT)
          Text('查看服务通知与派单提醒')
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
        Text('💚')
          .fontSize(46).margin({ bottom: 12 })
        Text('感谢您的社区服务')
          .fontSize(Theme.FS_SUBTITLE).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT)
        Text('进入「我的上门服务」查看排班、\n完成长者关怀与健康记录录入。')
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
    .width('100%').height('100%').backgroundColor(Theme.BG)
  }
}
