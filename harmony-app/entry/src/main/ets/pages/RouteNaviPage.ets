import { webview } from '@kit.ArkWeb'
import router from '@ohos.router'

// 路线导航参数：起点(志愿者当前定位) → 终点(坐标或地址)
interface RouteNaviParams {
  oLat: number
  oLng: number
  dLat: number
  dLng: number
  destName: string
  destAddress?: string   // 无坐标时用地址，交给百度地理编码自动规划
  region?: string        // 地址所在城市
}

// 应用内百度地图路线页：调用百度「路线规划 URI API」，在 WebView 中展示驾车路线。
// 优点：无需本机安装百度地图 App（模拟器可用），复用 Web 端已申请的能力，直接“显示路线”。
@Entry
@Component
struct RouteNaviPage {
  private controller: webview.WebviewController = new webview.WebviewController()
  @State title: string = '路线导航'
  @State naviUrl: string = ''

  aboutToAppear() {
    let p = router.getParams() as RouteNaviParams
    if (p === undefined) {
      return
    }
    this.title = p.destName ? p.destName : '路线导航'
    let origin: string = '?origin=latlng:' + p.oLat + ',' + p.oLng + '|name:我的位置'
    let destPart: string = ''
    let hasCoord: boolean = p.dLat !== undefined && p.dLng !== undefined && (p.dLat !== 0 || p.dLng !== 0)
    if (hasCoord) {
      let dest: string = encodeURIComponent(p.destName ? p.destName : '目的地')
      destPart = '&destination=latlng:' + p.dLat + ',' + p.dLng + '|name:' + dest
    } else if (p.destAddress !== undefined && p.destAddress !== '') {
      // 无坐标：直接用地址，百度自动地理编码规划路线
      destPart = '&destination=' + encodeURIComponent(p.destAddress)
      if (p.region !== undefined && p.region !== '') {
        destPart += '&region=' + encodeURIComponent(p.region)
      }
    }
    if (destPart !== '') {
      this.naviUrl = 'https://api.map.baidu.com/direction' + origin + destPart
        + '&mode=driving&coord_type=gcj02&output=html'
        + '&src=webapp.hmservice.volunteer'
    }
  }

  build() {
    Column() {
      // 顶部栏
      Row() {
        Text('‹ 返回')
          .fontSize(16)
          .fontColor(Color.White)
          .onClick(() => {
            router.back()
          })
        Text(this.title)
          .fontSize(17)
          .fontWeight(FontWeight.Bold)
          .fontColor(Color.White)
          .layoutWeight(1)
          .textAlign(TextAlign.Center)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
        Text('  ')
          .width(44)
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 14, bottom: 14 })
      .backgroundColor('#2563EB')

      if (this.naviUrl !== '') {
        Web({ src: this.naviUrl, controller: this.controller })
          .width('100%')
          .layoutWeight(1)
          .domStorageAccess(true)
          .geolocationAccess(true)
          .mixedMode(MixedMode.All)
      } else {
        Column() {
          Text('⚠️')
            .fontSize(40)
          Text('缺少目的地坐标，无法规划路线')
            .fontSize(15)
            .fontColor('#64748B')
            .margin({ top: 12 })
        }
        .width('100%')
        .layoutWeight(1)
        .justifyContent(FlexAlign.Center)
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#FFFFFF')
  }
}
