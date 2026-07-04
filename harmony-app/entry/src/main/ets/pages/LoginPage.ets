import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { Api, Session } from '../common/Api'
import { LoginPayload, LoginResponse } from '../model/Models'

@Entry
@Component
struct LoginPage {
  @State username: string = 'resident02'
  @State password: string = '123456'
  @State loading: boolean = false

  async login() {
    if (this.username.trim() === '' || this.password.trim() === '') {
      promptAction.showToast({ message: '请输入用户名和密码' })
      return
    }

    this.loading = true

    try {
      let payload: LoginPayload = {
        username: this.username,
        password: this.password
      }

      let result = await Api.post<LoginPayload>('/auth/login/', payload) as LoginResponse

      Session.token = result.token
      Session.userId = result.user.id
      Session.username = result.user.username
      Session.role = result.user.role

      promptAction.showToast({ message: '登录成功' })

      if (Session.role === 'resident') {
        router.pushUrl({ url: 'pages/ResidentHomePage' })
      } else if (Session.role === 'volunteer') {
        router.pushUrl({ url: 'pages/VolunteerHomePage' })
      } else if (Session.role === 'admin') {
        promptAction.showToast({ message: '管理员请使用 Web 后台登录' })
      } else {
        promptAction.showToast({ message: '未知用户角色' })
      }
    } catch (err) {
      promptAction.showToast({ message: '登录失败，请检查账号、密码或后端服务' })
    } finally {
      this.loading = false
    }
  }

  build() {
    Column() {
      Column() {
        Text('社区应急互助平台')
          .fontSize(28)
          .fontWeight(FontWeight.Bold)
          .fontColor(Color.White)

        Text('居民求助 · 志愿者响应 · 灾害预警')
          .fontSize(14)
          .fontColor('#E0F2FE')
          .margin({ top: 10 })
      }
      .width('100%')
      .height(180)
      .justifyContent(FlexAlign.Center)
      .alignItems(HorizontalAlign.Center)
      .backgroundColor('#2563EB')

      Column() {
        Text('账号登录')
          .fontSize(24)
          .fontWeight(FontWeight.Bold)
          .margin({ bottom: 24 })

        TextInput({ placeholder: '用户名', text: this.username })
          .height(48)
          .backgroundColor('#F1F5F9')
          .borderRadius(10)
          .padding({ left: 12, right: 12 })
          .onChange((value: string) => {
            this.username = value
          })

        TextInput({ placeholder: '密码', text: this.password })
          .height(48)
          .type(InputType.Password)
          .backgroundColor('#F1F5F9')
          .borderRadius(10)
          .padding({ left: 12, right: 12 })
          .margin({ top: 16 })
          .onChange((value: string) => {
            this.password = value
          })

        Button(this.loading ? '登录中...' : '登录')
          .width('100%')
          .height(48)
          .fontSize(17)
          .backgroundColor('#2563EB')
          .margin({ top: 24 })
          .onClick(() => {
            this.login()
          })

        Text('测试账号：resident02 / 123456')
          .fontSize(13)
          .fontColor('#64748B')
          .margin({ top: 18 })

        Text('志愿者账号：volunteer02 / 123456')
          .fontSize(13)
          .fontColor('#64748B')
          .margin({ top: 6 })
      }
      .width('100%')
      .padding(24)
      .alignItems(HorizontalAlign.Start)
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F8FAFC')
  }
}