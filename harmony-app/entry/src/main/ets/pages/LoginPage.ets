import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { Api, Session } from '../common/Api'
import { PushService } from '../common/PushService'
import { LoginPayload, LoginResponse } from '../model/Models'
import { LocationService } from '../common/LocationService'
import { LocationResult } from '../model/Models'
import { BusinessError } from '@ohos.base'
import { Theme } from '../common/Theme'
import { common } from '@kit.AbilityKit'

@Entry
@Component
struct LoginPage {
  @State username: string = 'resident1'
  @State password: string = '123456'
  @State loading: boolean = false
  @State sosSending: boolean = false

  // 启动时尝试自动登录：若本地有已保存且仍有效的登录态，直接进入对应主页
  async aboutToAppear() {
    let context = getContext(this) as common.UIAbilityContext
    let hasSession = await Session.restore(context)
    if (!hasSession) {
      return
    }
    try {
      await Api.get('/auth/me/')
    } catch (err) {
      await Session.clear(context)
      return
    }
    if (Session.role === 'resident') {
      router.replaceUrl({ url: 'pages/ResidentHomePage' })
    } else if (Session.role === 'volunteer') {
      router.replaceUrl({ url: 'pages/VolunteerHomePage' })
    }
  }

  async login() {
    let username = this.username.trim()
    let password = this.password.trim()

    if (username === '' || password === '') {
      promptAction.showToast({ message: '请输入用户名和密码' })
      return
    }

    this.loading = true

    try {
      let payload: LoginPayload = {
        username: username,
        password: password
      }

      let result = await Api.post<LoginPayload>('/auth/login/', payload) as LoginResponse

      // 保存 token + 全部用户字段（phone / community / address / skills）
      Session.token = result.token
      Session.saveUser(result.user)

      // 持久化登录态以支持下次自动登录
      await Session.persist(getContext(this) as common.UIAbilityContext)

      promptAction.showToast({ message: '登录成功' })

      // 登录成功后异步上报设备推送 Token（fire-and-forget，不阻塞导航）
      PushService.registerToken()

      if (Session.role === 'resident') {
        router.replaceUrl({ url: 'pages/ResidentHomePage' })
      } else if (Session.role === 'volunteer') {
        router.replaceUrl({ url: 'pages/VolunteerHomePage' })
      } else if (Session.role === 'admin') {
        promptAction.showToast({ message: '管理员请使用 Web 后台登录' })
      } else {
        promptAction.showToast({ message: '未知用户角色' })
      }
    } catch (err) {
      let e = err as Error
      promptAction.showToast({ message: e.message ? e.message : '登录失败，请检查账号、密码或后端服务' })
    } finally {
      this.loading = false
    }
  }

  // 一键紧急求助：获取位置后直接发送 SOS，无需登录
  async sosHelp() {
    this.sosSending = true
    try {
      let loc: LocationResult = await LocationService.getCurrentLocation()
      let payload: Record<string, number> = {
        'latitude': loc.latitude,
        'longitude': loc.longitude
      }
      await Api.post<Record<string, number>>('/auth/emergency/', payload)
      promptAction.showToast({ message: '紧急求助已发送！救援人员将尽快响应' })
    } catch (err) {
      let e = err as BusinessError
      promptAction.showToast({ message: e.message ? e.message : '发送失败，请确认已开启定位' })
    } finally {
      this.sosSending = false
    }
  }

  build() {
    Column() {
      // 顶部渐变头部
      Column() {
        Text('🤝')
          .fontSize(52)
          .margin({ bottom: 10 })

        Text('社区应急互助平台')
          .fontSize(27)
          .fontWeight(FontWeight.Bold)
          .fontColor(Color.White)

        Text('居民求助 · 志愿者响应 · 灾害预警')
          .fontSize(14)
          .fontColor('#DBEAFE')
          .margin({ top: 10 })
      }
      .width('100%')
      .height(280)
      .justifyContent(FlexAlign.Center)
      .alignItems(HorizontalAlign.Center)
      .linearGradient({
        angle: 145,
        colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY, 0.55], [Theme.PRIMARY_DARK, 1.0]]
      })
      .borderRadius({ bottomLeft: 32, bottomRight: 32 })

      // 浮起的登录卡片（负边距叠压头部）
      Column() {
        Text('账号登录')
          .fontSize(22)
          .fontWeight(FontWeight.Bold)
          .fontColor(Theme.TEXT)
          .margin({ bottom: 22 })

        TextInput({ placeholder: '用户名', text: this.username })
          .height(50)
          .backgroundColor('#F8FAFC')
          .borderRadius(Theme.RADIUS_SM)
          .border({ width: 1, color: Theme.BORDER })
          .padding({ left: 14, right: 14 })
          .onChange((value: string) => {
            this.username = value
          })

        TextInput({ placeholder: '密码', text: this.password })
          .height(50)
          .type(InputType.Password)
          .backgroundColor('#F8FAFC')
          .borderRadius(Theme.RADIUS_SM)
          .border({ width: 1, color: Theme.BORDER })
          .padding({ left: 14, right: 14 })
          .margin({ top: 14 })
          .onChange((value: string) => {
            this.password = value
          })

        Button(this.loading ? '登录中...' : '登 录')
          .width('100%')
          .height(50)
          .fontSize(17)
          .fontWeight(FontWeight.Medium)
          .borderRadius(Theme.RADIUS_SM)
          .enabled(!this.loading)
          .linearGradient({
            angle: 90,
            colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY_DARK, 1.0]]
          })
          .margin({ top: 22 })
          .onClick(() => {
            this.login()
          })

        // 注册入口
        Button('注册新账号')
          .width('100%')
          .height(46)
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
          .fontColor(Theme.PRIMARY)
          .backgroundColor('#EBF5FF')
          .borderRadius(Theme.RADIUS_SM)
          .margin({ top: 14 })
          .onClick(() => {
            router.pushUrl({ url: 'pages/RegisterPage' })
          })

        // 一键紧急求助（无需登录，仅需定位）
        Button(this.sosSending ? '发送中...' : '🆘 一键紧急求助')
          .width('100%')
          .height(52)
          .fontSize(17)
          .fontWeight(FontWeight.Bold)
          .fontColor(Color.White)
          .backgroundColor(Theme.DANGER)
          .borderRadius(Theme.RADIUS_SM)
          .enabled(!this.sosSending)
          .shadow({ radius: 16, color: '#66EF4444', offsetX: 0, offsetY: 4 })
          .margin({ top: 14 })
          .onClick(() => {
            this.sosHelp()
          })

        Text('无需登录 · 自动定位 · 一键发送求救信号')
          .fontSize(12)
          .fontColor(Theme.DANGER)
          .margin({ top: 8 })
          .width('100%')
          .textAlign(TextAlign.Center)

        // 演示账号提示区
        Column() {
          Text('演示账号')
            .fontSize(12)
            .fontColor(Theme.TEXT_MUTED)
            .margin({ bottom: 6 })
          Text('居民　resident1 / 123456')
            .fontSize(13)
            .fontColor(Theme.TEXT_BODY)
          Text('志愿者　volunteer1 / 123456')
            .fontSize(13)
            .fontColor(Theme.TEXT_BODY)
            .margin({ top: 4 })
        }
        .width('100%')
        .alignItems(HorizontalAlign.Start)
        .padding(14)
        .margin({ top: 20 })
        .backgroundColor('#F1F5F9')
        .borderRadius(Theme.RADIUS_SM)
      }
      .width('90%')
      .padding(24)
      .margin({ top: -40 })
      .alignItems(HorizontalAlign.Start)
      .backgroundColor(Theme.CARD)
      .borderRadius(Theme.RADIUS)
      .shadow({ radius: 24, color: '#1A1E293B', offsetX: 0, offsetY: 8 })
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG)
  }
}