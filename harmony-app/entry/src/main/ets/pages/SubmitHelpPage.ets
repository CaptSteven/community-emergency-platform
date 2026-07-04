import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { Api } from '../common/Api'
import { SubmitHelpPayload } from '../model/Models'

@Entry
@Component
struct SubmitHelpPage {
  @State requestType: string = 'medical'
  @State urgency: string = 'medium'
  @State description: string = ''
  @State address: string = ''
  @State submitting: boolean = false

  async submitHelp() {
    if (this.description.trim() === '' || this.address.trim() === '') {
      promptAction.showToast({ message: '请填写求助描述和地址' })
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

      await Api.post<SubmitHelpPayload>('/help-requests/', payload)

      promptAction.showToast({ message: '求助提交成功' })
      router.back()
    } catch (err) {
      promptAction.showToast({ message: '提交失败，请检查后端服务' })
    } finally {
      this.submitting = false
    }
  }

  typeButton(text: string, value: string): void {
  }

  build() {
    Column() {
      Row() {
        Text('提交居民求助')
          .fontSize(22)
          .fontWeight(FontWeight.Bold)
          .fontColor(Color.White)
          .layoutWeight(1)

        Button('返回')
          .height(34)
          .backgroundColor('#1D4ED8')
          .onClick(() => {
            router.back()
          })
      }
      .width('100%')
      .padding(18)
      .backgroundColor('#2563EB')

      Scroll() {
        Column() {
          Text('求助类型')
            .fontSize(16)
            .fontWeight(FontWeight.Bold)
            .margin({ bottom: 10 })

          Row() {
            Button('医疗')
              .layoutWeight(1)
              .height(40)
              .backgroundColor(this.requestType === 'medical' ? '#2563EB' : '#CBD5E1')
              .onClick(() => {
                this.requestType = 'medical'
              })

            Button('物资')
              .layoutWeight(1)
              .height(40)
              .backgroundColor(this.requestType === 'material' ? '#2563EB' : '#CBD5E1')
              .margin({ left: 8 })
              .onClick(() => {
                this.requestType = 'material'
              })

            Button('转移')
              .layoutWeight(1)
              .height(40)
              .backgroundColor(this.requestType === 'transfer' ? '#2563EB' : '#CBD5E1')
              .margin({ left: 8 })
              .onClick(() => {
                this.requestType = 'transfer'
              })
          }

          Row() {
            Button('老人')
              .layoutWeight(1)
              .height(40)
              .backgroundColor(this.requestType === 'elderly' ? '#2563EB' : '#CBD5E1')
              .onClick(() => {
                this.requestType = 'elderly'
              })

            Button('被困')
              .layoutWeight(1)
              .height(40)
              .backgroundColor(this.requestType === 'trapped' ? '#2563EB' : '#CBD5E1')
              .margin({ left: 8 })
              .onClick(() => {
                this.requestType = 'trapped'
              })

            Button('其他')
              .layoutWeight(1)
              .height(40)
              .backgroundColor(this.requestType === 'other' ? '#2563EB' : '#CBD5E1')
              .margin({ left: 8 })
              .onClick(() => {
                this.requestType = 'other'
              })
          }
          .margin({ top: 8 })

          Text('紧急程度')
            .fontSize(16)
            .fontWeight(FontWeight.Bold)
            .margin({ top: 24, bottom: 10 })

          Row() {
            Button('低')
              .layoutWeight(1)
              .height(40)
              .backgroundColor(this.urgency === 'low' ? '#64748B' : '#CBD5E1')
              .onClick(() => {
                this.urgency = 'low'
              })

            Button('中')
              .layoutWeight(1)
              .height(40)
              .backgroundColor(this.urgency === 'medium' ? '#2563EB' : '#CBD5E1')
              .margin({ left: 8 })
              .onClick(() => {
                this.urgency = 'medium'
              })

            Button('高')
              .layoutWeight(1)
              .height(40)
              .backgroundColor(this.urgency === 'high' ? '#D97706' : '#CBD5E1')
              .margin({ left: 8 })
              .onClick(() => {
                this.urgency = 'high'
              })

            Button('紧急')
              .layoutWeight(1)
              .height(40)
              .backgroundColor(this.urgency === 'critical' ? '#DC2626' : '#CBD5E1')
              .margin({ left: 8 })
              .onClick(() => {
                this.urgency = 'critical'
              })
          }

          Text('求助描述')
            .fontSize(16)
            .fontWeight(FontWeight.Bold)
            .margin({ top: 24, bottom: 10 })

          TextArea({ placeholder: '请描述遇到的问题，例如老人突发不适、需要饮用水、地下车库积水等', text: this.description })
            .height(130)
            .backgroundColor(Color.White)
            .borderRadius(12)
            .padding(12)
            .onChange((value: string) => {
              this.description = value
            })

          Text('详细地址')
            .fontSize(16)
            .fontWeight(FontWeight.Bold)
            .margin({ top: 24, bottom: 10 })

          TextInput({ placeholder: '例如：阳光社区 3 号楼 2 单元 501', text: this.address })
            .height(48)
            .backgroundColor(Color.White)
            .borderRadius(12)
            .padding({ left: 12, right: 12 })
            .onChange((value: string) => {
              this.address = value
            })

          Button(this.submitting ? '提交中...' : '提交求助')
            .width('100%')
            .height(48)
            .fontSize(17)
            .backgroundColor('#EF4444')
            .margin({ top: 28 })
            .onClick(() => {
              this.submitHelp()
            })
        }
        .width('100%')
        .padding(18)
      }
      .layoutWeight(1)
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F1F5F9')
  }
}