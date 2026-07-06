import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { Api } from '../common/Api'
import { LocationService } from '../common/LocationService'
import { SubmitHelpPayload, LocationResult } from '../model/Models'
import { BusinessError } from '@ohos.base'
import { Theme } from '../common/Theme'

@Entry
@Component
struct SubmitHelpPage {
  @State requestType: string = 'medical'
  @State urgency: string = 'medium'
  @State description: string = ''
  @State address: string = ''
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

  async submitHelp() {
    if (this.description.trim().length < 6) {
      promptAction.showToast({ message: '求助描述至少 6 个字，请写清具体情况' })
      return
    }

    if (this.address.trim() === '') {
      promptAction.showToast({ message: '请填写详细地址' })
      return
    }

    this.submitting = true

    try {
      let payload: SubmitHelpPayload = {
        request_type: this.requestType,
        urgency: this.urgency,
        description: this.description,
        address: this.address
      }

      // 未定位时不要提交空字符串，否则 DRF DecimalField 会将其视为非法数字。
      if (this.located) {
        payload.latitude = this.latitude.toString()
        payload.longitude = this.longitude.toString()
      }

      await Api.post<SubmitHelpPayload>('/help-requests/', payload)

      promptAction.showToast({ message: '求助提交成功' })
      router.back()
    } catch (err) {
      promptAction.showToast({ message: '提交失败，请确认描述至少6个字且后端服务正常' })
    } finally {
      this.submitting = false
    }
  }

  // 求助类型药丸按钮：选中态高亮
  @Builder
  TypePill(icon: string, label: string, value: string) {
    Column() {
      Text(icon)
        .fontSize(22)
        .margin({ bottom: 4 })
      Text(label)
        .fontSize(14)
        .fontWeight(this.requestType === value ? FontWeight.Bold : FontWeight.Medium)
        .fontColor(this.requestType === value ? Color.White : Theme.TEXT_BODY)
    }
    .layoutWeight(1)
    .height(66)
    .justifyContent(FlexAlign.Center)
    .backgroundColor(this.requestType === value ? Theme.PRIMARY : '#F1F5F9')
    .borderRadius(Theme.RADIUS_SM)
    .border({
      width: 1,
      color: this.requestType === value ? Theme.PRIMARY : Theme.BORDER
    })
    .shadow(this.requestType === value
      ? { radius: 10, color: '#332563EB', offsetX: 0, offsetY: 3 }
      : { radius: 0, color: '#00000000', offsetX: 0, offsetY: 0 })
    .onClick(() => {
      this.requestType = value
    })
  }

  // 紧急程度药丸按钮
  @Builder
  UrgencyPill(label: string, value: string, activeColor: string) {
    Text(label)
      .layoutWeight(1)
      .height(46)
      .textAlign(TextAlign.Center)
      .fontSize(15)
      .fontWeight(this.urgency === value ? FontWeight.Bold : FontWeight.Medium)
      .fontColor(this.urgency === value ? Color.White : Theme.TEXT_BODY)
      .backgroundColor(this.urgency === value ? activeColor : '#F1F5F9')
      .borderRadius(Theme.RADIUS_SM)
      .border({
        width: 1,
        color: this.urgency === value ? activeColor : Theme.BORDER
      })
      .onClick(() => {
        this.urgency = value
      })
  }

  @Builder
  SectionTitle(icon: string, title: string) {
    Row() {
      Text(icon)
        .fontSize(16)
        .margin({ right: 6 })
      Text(title)
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .fontColor(Theme.TEXT)
    }
    .width('100%')
    .margin({ bottom: 12 })
  }

  build() {
    Column() {
      // 顶部渐变头部
      Column() {
        Row() {
          Text('返回')
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
          Text('🆘')
            .fontSize(34)
            .margin({ right: 10 })
          Column() {
            Text('提交居民求助')
              .fontSize(24)
              .fontWeight(FontWeight.Bold)
              .fontColor(Color.White)
            Text('填写信息，志愿者将尽快响应')
              .fontSize(13)
              .fontColor('#DBEAFE')
              .margin({ top: 4 })
          }
          .alignItems(HorizontalAlign.Start)
          .layoutWeight(1)
        }
        .width('100%')
        .margin({ top: 16 })
      }
      .width('100%')
      .padding({ left: 20, right: 20, top: 20, bottom: 26 })
      .linearGradient({
        angle: 145,
        colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY, 0.55], [Theme.PRIMARY_DARK, 1.0]]
      })
      .borderRadius({ bottomLeft: 28, bottomRight: 28 })

      Scroll() {
        Column() {
          // 求助类型卡片
          Column() {
            this.SectionTitle('🏷️', '求助类型')

            Row() {
              this.TypePill('🩺', '医疗', 'medical')
              this.TypePill('📦', '物资', 'material')
              this.TypePill('🚐', '转移', 'transfer')
            }

            Row() {
              this.TypePill('👵', '老人', 'elderly')
              this.TypePill('🆘', '被困', 'trapped')
              this.TypePill('➕', '其他', 'other')
            }
            .margin({ top: 10 })

            Row() {
              this.TypePill('🧒', '儿童', 'child')
              this.TypePill('🔥', '火灾', 'fire')
              this.TypePill('💧', '积水', 'flood')
            }
            .margin({ top: 10 })
          }
          .width('100%')
          .padding(16)
          .backgroundColor(Theme.CARD)
          .borderRadius(Theme.RADIUS)
          .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })

          // 紧急程度卡片
          Column() {
            this.SectionTitle('⚡', '紧急程度')

            Row() {
              this.UrgencyPill('低', 'low', Theme.SUCCESS)
              Blank().width(8)
              this.UrgencyPill('中', 'medium', Theme.PRIMARY)
              Blank().width(8)
              this.UrgencyPill('高', 'high', Theme.WARN)
              Blank().width(8)
              this.UrgencyPill('紧急', 'critical', Theme.DANGER)
            }
          }
          .width('100%')
          .padding(16)
          .margin({ top: 12 })
          .backgroundColor(Theme.CARD)
          .borderRadius(Theme.RADIUS)
          .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })

          // 求助描述卡片
          Column() {
            this.SectionTitle('📝', '求助描述')

            TextArea({ placeholder: '请描述遇到的问题，例如老人突发不适、需要饮用水、地下车库积水等', text: this.description })
              .width('100%')
              .height(130)
              .backgroundColor('#F8FAFC')
              .borderRadius(Theme.RADIUS_SM)
              .border({ width: 1, color: Theme.BORDER })
              .padding(12)
              .onChange((value: string) => {
                this.description = value
              })
          }
          .width('100%')
          .padding(16)
          .margin({ top: 12 })
          .backgroundColor(Theme.CARD)
          .borderRadius(Theme.RADIUS)
          .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })

          // 详细地址卡片
          Column() {
            this.SectionTitle('📍', '详细地址')

            TextInput({ placeholder: '例如：阳光社区 3 号楼 2 单元 501', text: this.address })
              .width('100%')
              .height(48)
              .backgroundColor('#F8FAFC')
              .borderRadius(Theme.RADIUS_SM)
              .border({ width: 1, color: Theme.BORDER })
              .padding({ left: 12, right: 12 })
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

          // 位置定位卡片
          Column() {
            this.SectionTitle('🛰️', '位置定位')

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
              .padding({ left: 12, right: 12, top: 8, bottom: 8 })
              .backgroundColor('#ECFDF5')
              .borderRadius(Theme.RADIUS_SM)
            } else {
              Text('尚未定位。附上位置可帮助志愿者更快找到您（可选）')
                .width('100%')
                .fontSize(13)
                .fontColor(Theme.TEXT_MUTED)
                .margin({ top: 12 })
            }
          }
          .width('100%')
          .padding(16)
          .margin({ top: 12 })
          .backgroundColor(Theme.CARD)
          .borderRadius(Theme.RADIUS)
          .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })

          // 提交按钮
          Button(this.submitting ? '提交中...' : '提交求助')
            .width('100%')
            .height(50)
            .fontSize(17)
            .fontWeight(FontWeight.Medium)
            .borderRadius(Theme.RADIUS_SM)
            .enabled(!this.submitting)
            .linearGradient({
              angle: 90,
              colors: [['#F87171', 0.0], [Theme.DANGER, 1.0]]
            })
            .shadow({ radius: 14, color: '#33EF4444', offsetX: 0, offsetY: 4 })
            .margin({ top: 20, bottom: 8 })
            .onClick(() => {
              this.submitHelp()
            })
        }
        .width('90%')
        .padding({ top: 16, bottom: 24 })
      }
      .layoutWeight(1)
      .width('100%')
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG)
  }
}
