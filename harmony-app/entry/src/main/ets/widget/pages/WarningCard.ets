// 服务卡片 UI（Form Kit / ArkTS 卡片）。数据由 EntryFormAbility 通过
// formBindingData 注入到卡片的 LocalStorage 中。
let storage = new LocalStorage()

@Entry(storage)
@Component
struct WarningCard {
  @LocalStorageProp('title') title: string = '社区应急预警'
  @LocalStorageProp('subtitle') subtitle: string = '打开应用查看最新预警'

  build() {
    Column() {
      Row() {
        Text(this.title)
          .fontSize(16)
          .fontWeight(FontWeight.Bold)
          .fontColor(Color.White)
          .layoutWeight(1)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
      }
      .width('100%')

      Text(this.subtitle)
        .fontSize(13)
        .fontColor('#E0F2FE')
        .margin({ top: 10 })
        .maxLines(3)
        .textOverflow({ overflow: TextOverflow.Ellipsis })
        .layoutWeight(1)

      Button('刷新')
        .fontSize(13)
        .height(30)
        .backgroundColor('#1D4ED8')
        .onClick(() => {
          // 通过 postCardAction 触发 FormExtensionAbility.onFormEvent 刷新卡片
          postCardAction(this, {
            action: 'message',
            params: {
              action: 'refresh'
            }
          })
        })
    }
    .width('100%')
    .height('100%')
    .padding(14)
    .alignItems(HorizontalAlign.Start)
    .backgroundColor('#2563EB')
  }
}
