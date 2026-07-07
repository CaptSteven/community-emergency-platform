import router from '@ohos.router'
import { Api, Session } from '../common/Api'
import { LocationService } from '../common/LocationService'
import { common } from '@kit.AbilityKit'
import { UpdateLocationPayload, LocationResult } from '../model/Models'
import { Theme } from '../common/Theme'

// 志愿者端主页：纯社区服务，无任何应急任务 / 灾害预警。
// 仅保留后台定位上报（供社区上门服务派单参考），静默运行、不打扰用户。
// 首页视觉重做：品牌问候渐变头 + 醒目大卡入口 + 圆角功能宫格 + 温暖引导卡。
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

  // 头像首字：取用户名首字，无则用 emoji 兜底
  private avatarChar(): string {
    return Session.username.length > 0 ? Session.username.substring(0, 1) : '🦺'
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
    Scroll() {
      Column() {
        // ===== 顶部品牌问候渐变头 =====
        Column() {
          Row() {
            // 头像圆（姓名首字）
            Text(this.avatarChar())
              .fontSize(24).fontWeight(FontWeight.Bold).fontColor(Color.White)
              .width(56).height(56).textAlign(TextAlign.Center)
              .backgroundColor('#33FFFFFF').borderRadius(28)
              .borderWidth(1.5).borderColor('#66FFFFFF')

            // 问候语 + 技能
            Column() {
              Text(`你好，${Session.username} 👋`)
                .fontSize(20).fontWeight(FontWeight.Bold).fontColor(Color.White)
                .maxLines(1).textOverflow({ overflow: TextOverflow.Ellipsis })
              Text(`技能：${Session.skills || '未填写'}`)
                .fontSize(13).fontColor('#DBEAFE').margin({ top: 6 })
                .maxLines(1).textOverflow({ overflow: TextOverflow.Ellipsis })
            }
            .layoutWeight(1).alignItems(HorizontalAlign.Start).margin({ left: 14 })

            // 消息小图标
            Text('✉️')
              .fontSize(18).width(40).height(40).textAlign(TextAlign.Center)
              .backgroundColor('#33FFFFFF').borderRadius(20)
              .onClick(() => { router.pushUrl({ url: 'pages/NotificationsPage' }) })
            // 退出小图标
            Text('⏻')
              .fontSize(18).fontColor(Color.White).width(40).height(40).textAlign(TextAlign.Center)
              .backgroundColor('#33FFFFFF').borderRadius(20).margin({ left: 10 })
              .onClick(() => { this.logout() })
          }
          .width('100%').alignItems(VerticalAlign.Center)
        }
        .width('100%')
        .padding({ left: 20, right: 20, top: 24, bottom: 40 })
        .linearGradient({
          angle: 145,
          colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY, 0.55], [Theme.PRIMARY_DARK, 1.0]]
        })
        .borderRadius({ bottomLeft: 30, bottomRight: 30 })

        // ===== 主入口大卡：我的上门服务（绿→青渐变，与头部叠层）=====
        Row() {
          Text('🩺')
            .fontSize(32).width(58).height(58).textAlign(TextAlign.Center)
            .backgroundColor('#33FFFFFF').borderRadius(18)
          Column() {
            Text('我的上门服务')
              .fontSize(Theme.FS_TITLE).fontWeight(FontWeight.Bold).fontColor(Color.White)
            Text('社区长期服务 · 长者关怀 · 录入健康记录')
              .fontSize(Theme.FS_SMALL).fontColor('#E0F2F1').margin({ top: 6 })
          }.layoutWeight(1).alignItems(HorizontalAlign.Start).margin({ left: 14 })
          Text('›').fontSize(32).fontColor(Color.White)
        }
        .width('90%').padding({ left: 18, right: 18, top: 18, bottom: 18 })
        .margin({ top: -20 }).alignItems(VerticalAlign.Center)
        .borderRadius(Theme.RADIUS_LG)
        .linearGradient({ angle: 120, colors: [[Theme.SUCCESS, 0.0], [Theme.TEAL, 1.0]] })
        .shadow({ radius: 18, color: '#3316A34A', offsetX: 0, offsetY: 8 })
        .onClick(() => { router.pushUrl({ url: 'pages/VolunteerServicePage' }) })

        // ===== 常用功能 区块标题 =====
        Row() {
          Text('常用功能')
            .fontSize(Theme.FS_BODY).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT)
        }
        .width('90%').margin({ top: 22, bottom: 12 }).justifyContent(FlexAlign.Start)

        // ===== 功能宫格：3 个圆角小卡 =====
        Row() {
          // 站内消息
          Column() {
            Text('✉️')
              .fontSize(26).width(50).height(50).textAlign(TextAlign.Center)
              .backgroundColor(Theme.PRIMARY_LIGHT_BG).borderRadius(15)
            Text('站内消息')
              .fontSize(13).fontWeight(FontWeight.Medium).fontColor(Theme.TEXT).margin({ top: 10 })
          }
          .layoutWeight(1).padding({ top: 16, bottom: 16 }).alignItems(HorizontalAlign.Center)
          .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
          .shadow({ radius: 14, color: '#14000000', offsetX: 0, offsetY: 4 })
          .onClick(() => { router.pushUrl({ url: 'pages/NotificationsPage' }) })

          // 我的排班
          Column() {
            Text('🗓️')
              .fontSize(26).width(50).height(50).textAlign(TextAlign.Center)
              .backgroundColor(Theme.SUCCESS_LIGHT).borderRadius(15)
            Text('我的排班')
              .fontSize(13).fontWeight(FontWeight.Medium).fontColor(Theme.TEXT).margin({ top: 10 })
          }
          .layoutWeight(1).margin({ left: 10, right: 10 }).padding({ top: 16, bottom: 16 })
          .alignItems(HorizontalAlign.Center)
          .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
          .shadow({ radius: 14, color: '#14000000', offsetX: 0, offsetY: 4 })
          .onClick(() => { router.pushUrl({ url: 'pages/VolunteerServicePage' }) })

          // 我的积分 → 积分与排行榜页
          Column() {
            Text('⭐')
              .fontSize(26).width(50).height(50).textAlign(TextAlign.Center)
              .backgroundColor(Theme.WARN_LIGHT).borderRadius(15)
            Text('我的积分')
              .fontSize(13).fontWeight(FontWeight.Medium).fontColor(Theme.TEXT).margin({ top: 10 })
          }
          .layoutWeight(1).padding({ top: 16, bottom: 16 }).alignItems(HorizontalAlign.Center)
          .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
          .shadow({ radius: 14, color: '#14000000', offsetX: 0, offsetY: 4 })
          .onClick(() => { router.pushUrl({ url: 'pages/VolunteerPointsPage' }) })
        }
        .width('90%')

        // ===== 底部温暖引导卡 =====
        Column() {
          Text('💚')
            .fontSize(46).margin({ bottom: 12 })
          Text('感谢您的社区服务')
            .fontSize(Theme.FS_SUBTITLE).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT)
          Text('进入「我的上门服务」查看排班、\n完成长者关怀与健康记录录入。')
            .fontSize(Theme.FS_SMALL).fontColor(Theme.TEXT_BODY).textAlign(TextAlign.Center)
            .lineHeight(21).margin({ top: 10 })
        }
        .width('90%').padding({ top: 26, bottom: 26, left: 16, right: 16 })
        .margin({ top: 18, bottom: 24 })
        .justifyContent(FlexAlign.Center).alignItems(HorizontalAlign.Center)
        .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
        .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })
      }
      .width('100%').constraintSize({ minHeight: '100%' })
    }
    .width('100%').height('100%')
    .backgroundColor(Theme.BG)
    .scrollBar(BarState.Off)
    .edgeEffect(EdgeEffect.Spring)
    .align(Alignment.Top)
  }
}
