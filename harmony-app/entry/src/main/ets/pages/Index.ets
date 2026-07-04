import router from '@ohos.router'

@Entry
@Component
struct Index {
  aboutToAppear() {
    router.replaceUrl({
      url: 'pages/LoginPage'
    })
  }

  build() {
    Column() {
      Text('正在进入社区应急互助平台...')
        .fontSize(20)
        .fontColor('#2563EB')
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
    .backgroundColor('#F8FAFC')
  }
}