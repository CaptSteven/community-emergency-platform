import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { Api, Session } from '../common/Api'
import { LocationService } from '../common/LocationService'
import { PushService } from '../common/PushService'
import { RegisterPayload, RegisterResponse, LocationResult } from '../model/Models'
import { BusinessError } from '@ohos.base'
import { common } from '@kit.AbilityKit'
import { Theme } from '../common/Theme'

@Entry
@Component
struct RegisterPage {
  @State username: string = ''
  @State password: string = ''
  @State email: string = ''
  @State role: string = 'resident'
  @State phone: string = ''
  @State community: string = ''
  @State address: string = ''
  @State skills: string = ''
  @State submitting: boolean = false
  @State locating: boolean = false
  @State located: boolean = false
  @State latitude: number = 0
  @State longitude: number = 0

  // 调用 Location Kit 获取当前定位
  async fetchLocation() {
    this.locating = true
    try {
      let result: LocationResult = await LocationService.getCurrentLocation()
      this.latitude = result.latitude
      this.longitude = result.longitude
      this.located = true
      promptAction.showToast({ message: '定位成功' })
    } catch (err) {
      let e = err as BusinessError
      promptAction.showToast({ message: e.message ? e.message : '定位失败' })
    } finally {
      this.locating = false
    }
  }

  async doRegister() {
    if (this.username.trim() === '' || this.password.trim() === '') {
      promptAction.showToast({ message: '请填写用户名和密码' })
      return
    }

    if (this.password.length < 6) {
      promptAction.showToast({ message: '密码至少 6 位' })
      return
    }

    if (this.role === 'volunteer' && this.skills.trim() === '') {
      promptAction.showToast({ message: '志愿者请填写技能标签，如：医疗 急救 老人' })
      return
    }

    this.submitting = true

    try {
      let payload: RegisterPayload = {
        username: this.username,
        password: this.password,
        email: this.email,
        role: this.role,
        phone: this.phone,
        community: this.community,
        address: this.address,
        skills: this.skills
      }

      // 如果已定位则携带经纬度
      if (this.located) {
        payload.current_latitude = this.latitude
        payload.current_longitude = this.longitude
      }

      let result = await Api.post<RegisterPayload>('/auth/register/', payload) as RegisterResponse

      // 注册成功，自动登录并持久化登录态
      Session.token = result.token
      Session.saveUser(result.user)
      await Session.persist(getContext(this) as common.UIAbilityContext)

      promptAction.showToast({ message: '注册成功' })

      // 上报设备推送 Token
      PushService.registerToken()

      if (Session.role === 'resident') {
        router.replaceUrl({ url: 'pages/ResidentHomePage' })
      } else if (Session.role === 'volunteer') {
        router.replaceUrl({ url: 'pages/VolunteerHomePage' })
      }
    } catch (err) {
      let e = err as BusinessError
      promptAction.showToast({ message: e.message ? e.message : '注册失败，请重试' })
    } finally {
      this.submitting = false
    }
  }

  // 角色切换药丸
  @Builder
  RolePill(label: string, desc: string, value: string) {
    Column() {
      Text(label)
        .fontSize(16)
        .fontWeight(this.role === value ? FontWeight.Bold : FontWeight.Medium)
        .fontColor(this.role === value ? Color.White : Theme.TEXT_BODY)

      Text(desc)
        .fontSize(12)
        .fontColor(this.role === value ? '#DBEAFE' : Theme.TEXT_MUTED)
        .margin({ top: 4 })
    }
    .layoutWeight(1)
    .height(60)
    .justifyContent(FlexAlign.Center)
    .backgroundColor(this.role === value ? Theme.PRIMARY : '#F1F5F9')
    .borderRadius(Theme.RADIUS_SM)
    .border({
      width: 1,
      color: this.role === value ? Theme.PRIMARY : Theme.BORDER
    })
    .onClick(() => {
      // 志愿者需线上申请+审核，不能直接注册
      if (value === 'volunteer') {
        router.pushUrl({ url: 'pages/VolunteerApplyPage' })
        return
      }
      this.role = value
    })
  }

  @Builder
  SectionTitle(title: string) {
    Text(title)
      .fontSize(16)
      .fontWeight(FontWeight.Bold)
      .fontColor(Theme.TEXT)
      .width('100%')
      .margin({ bottom: 12 })
  }

  build() {
    Column() {
      // 顶部
      Column() {
        Row() {
          Text('← 返回')
            .fontSize(15)
            .fontColor(Color.White)
            .padding({ left: 12, right: 12, top: 6, bottom: 6 })
            .backgroundColor('#33FFFFFF')
            .borderRadius(Theme.RADIUS_SM)
            .onClick(() => {
              router.back()
            })
          Blank()
        }
        .width('100%')

        Row() {
          Text('📝')
            .fontSize(34)
            .margin({ right: 10 })
          Column() {
            Text('注册新账号')
              .fontSize(24)
              .fontWeight(FontWeight.Bold)
              .fontColor(Color.White)
            Text('居民求助或志愿者响应')
              .fontSize(13)
              .fontColor('#DBEAFE')
              .margin({ top: 4 })
          }
          .alignItems(HorizontalAlign.Start)
          .layoutWeight(1)
        }
        .width('100%')
        .margin({ top: 14 })
      }
      .width('100%')
      .padding({ left: 20, right: 20, top: 20, bottom: 24 })
      .linearGradient({
        angle: 145,
        colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY, 0.55], [Theme.PRIMARY_DARK, 1.0]]
      })
      .borderRadius({ bottomLeft: 28, bottomRight: 28 })

      Scroll() {
        Column() {
          // 角色选择
          Column() {
            this.SectionTitle('选择角色')
            Row() {
              this.RolePill('🏠 居民', '提交求助', 'resident')
              Blank().width(12)
              this.RolePill('🦺 志愿者', '响应救助', 'volunteer')
            }
          }
          .width('100%')
          .padding(16)
          .backgroundColor(Theme.CARD)
          .borderRadius(Theme.RADIUS)
          .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })

          // 账号信息
          Column() {
            this.SectionTitle('账号信息')

            TextInput({ placeholder: '用户名（必填）', text: this.username })
              .height(48)
              .backgroundColor('#F8FAFC')
              .borderRadius(Theme.RADIUS_SM)
              .border({ width: 1, color: Theme.BORDER })
              .padding({ left: 12, right: 12 })
              .onChange((value: string) => {
                this.username = value
              })

            TextInput({ placeholder: '密码（至少 6 位）', text: this.password })
              .height(48)
              .type(InputType.Password)
              .backgroundColor('#F8FAFC')
              .borderRadius(Theme.RADIUS_SM)
              .border({ width: 1, color: Theme.BORDER })
              .padding({ left: 12, right: 12 })
              .margin({ top: 12 })
              .onChange((value: string) => {
                this.password = value
              })

            TextInput({ placeholder: '邮箱（选填）', text: this.email })
              .height(48)
              .type(InputType.Email)
              .backgroundColor('#F8FAFC')
              .borderRadius(Theme.RADIUS_SM)
              .border({ width: 1, color: Theme.BORDER })
              .padding({ left: 12, right: 12 })
              .margin({ top: 12 })
              .onChange((value: string) => {
                this.email = value
              })
          }
          .width('100%')
          .padding(16)
          .margin({ top: 12 })
          .backgroundColor(Theme.CARD)
          .borderRadius(Theme.RADIUS)
          .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })

          // 联系信息
          Column() {
            this.SectionTitle('联系信息')

            TextInput({ placeholder: '手机号', text: this.phone })
              .height(48)
              .type(InputType.PhoneNumber)
              .backgroundColor('#F8FAFC')
              .borderRadius(Theme.RADIUS_SM)
              .border({ width: 1, color: Theme.BORDER })
              .padding({ left: 12, right: 12 })
              .onChange((value: string) => {
                this.phone = value
              })

            TextInput({ placeholder: '所在社区（如：幸福社区）', text: this.community })
              .height(48)
              .backgroundColor('#F8FAFC')
              .borderRadius(Theme.RADIUS_SM)
              .border({ width: 1, color: Theme.BORDER })
              .padding({ left: 12, right: 12 })
              .margin({ top: 12 })
              .onChange((value: string) => {
                this.community = value
              })

            TextInput({ placeholder: '详细地址', text: this.address })
              .height(48)
              .backgroundColor('#F8FAFC')
              .borderRadius(Theme.RADIUS_SM)
              .border({ width: 1, color: Theme.BORDER })
              .padding({ left: 12, right: 12 })
              .margin({ top: 12 })
              .onChange((value: string) => {
                this.address = value
              })
          }
          .width('100%')
          .padding(16)
          .margin({ top: 12 })
          .backgroundColor(Theme.CARD)
          .borderRadius(Theme.RADIUS)
          .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })

          // 志愿者技能（仅志愿者角色显示）
          if (this.role === 'volunteer') {
            Column() {
              this.SectionTitle('技能标签（智能派单依据）')

              TextInput({ placeholder: '如：医疗 急救 老人 物资 分发', text: this.skills })
                .height(48)
                .backgroundColor('#F8FAFC')
                .borderRadius(Theme.RADIUS_SM)
                .border({ width: 1, color: Theme.BORDER })
                .padding({ left: 12, right: 12 })
                .onChange((value: string) => {
                  this.skills = value
                })

              Text('用空格分隔多个关键词，如：医疗 急救 老人\n这将帮助管理员精准派单')
                .fontSize(12)
                .fontColor(Theme.TEXT_MUTED)
                .margin({ top: 10 })
            }
            .width('100%')
            .padding(16)
            .margin({ top: 12 })
            .backgroundColor(Theme.CARD)
            .borderRadius(Theme.RADIUS)
            .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })
          }

          // 初始定位（选填）
          Column() {
            this.SectionTitle('初始定位（选填）')

            Button(this.locating ? '定位中...' : '获取当前定位')
              .width('100%')
              .height(46)
              .fontSize(16)
              .fontWeight(FontWeight.Medium)
              .borderRadius(Theme.RADIUS_SM)
              .backgroundColor(Theme.TEAL)
              .enabled(!this.locating)
              .onClick(() => {
                this.fetchLocation()
              })

            if (this.located) {
              Row() {
                Text('✅')
                  .fontSize(14)
                  .margin({ right: 6 })
                Text(`已定位：${this.latitude.toFixed(4)}, ${this.longitude.toFixed(4)}`)
                  .fontSize(13)
                  .fontColor(Theme.SUCCESS)
                  .layoutWeight(1)
              }
              .width('100%')
              .margin({ top: 12 })
              .padding(12)
              .backgroundColor('#ECFDF5')
              .borderRadius(Theme.RADIUS_SM)
            }
          }
          .width('100%')
          .padding(16)
          .margin({ top: 12 })
          .backgroundColor(Theme.CARD)
          .borderRadius(Theme.RADIUS)
          .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })

          // 提交按钮
          Button(this.submitting ? '注册中...' : '注 册')
            .width('100%')
            .height(50)
            .fontSize(17)
            .fontWeight(FontWeight.Medium)
            .borderRadius(Theme.RADIUS_SM)
            .enabled(!this.submitting)
            .linearGradient({
              angle: 90,
              colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY_DARK, 1.0]]
            })
            .shadow({ radius: 14, color: '#332563EB', offsetX: 0, offsetY: 4 })
            .margin({ top: 20, bottom: 24 })
            .onClick(() => {
              this.doRegister()
            })
        }
        .width('90%')
        .padding({ top: 16 })
      }
      .layoutWeight(1)
      .width('100%')
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG)
  }
}