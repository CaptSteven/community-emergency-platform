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

// 应用内百度地图路线页：用「百度地图 JSAPI(BMapGL) + DrivingRoute」在 WebView 里真正画出驾车路线。
// 比 direction?output=html 更可靠（后者在无百度App的WebView里会退化成通用地图落地页，画不出路线）。
// AK 为浏览器端 key，白名单含 localhost:5173，因此 loadData 的 baseUrl 设为该域以通过 Referer 校验。
const BAIDU_AK: string = 'mrz71REUvct4PN02kXDzraVnvIIZyhM0'
const BASE_REFERER: string = 'http://localhost:5173/'

@Entry
@Component
struct RouteNaviPage {
  private controller: webview.WebviewController = new webview.WebviewController()
  @State title: string = '路线导航'
  @State html: string = ''
  @State hasDest: boolean = false
  private loaded: boolean = false

  aboutToAppear() {
    let p = router.getParams() as RouteNaviParams
    if (p === undefined) {
      return
    }
    this.title = p.destName ? p.destName : '路线导航'
    let hasCoord: boolean = p.dLat !== undefined && p.dLng !== undefined && (p.dLat !== 0 || p.dLng !== 0)
    let addr: string = (p.destAddress !== undefined ? p.destAddress : '').replace(/'/g, ' ')
    let city: string = (p.region !== undefined ? p.region : '乌鲁木齐').replace(/'/g, ' ')
    let name: string = (p.destName !== undefined ? p.destName : '目的地').replace(/'/g, ' ')
    if (!hasCoord && addr === '') {
      this.hasDest = false
      return
    }
    this.hasDest = true
    this.html = this.buildHtml(p.oLng, p.oLat, hasCoord, p.dLng, p.dLat, addr, city, name)
  }

  buildHtml(oLng: number, oLat: number, hasCoord: boolean, dLng: number, dLat: number,
            addr: string, city: string, name: string): string {
    let destJs: string = hasCoord
      ? `drawTo(new BMap.Point(${dLng},${dLat}),'${name}');`
      : `var gc=new BMap.Geocoder();gc.getPoint('${addr}',function(pt){if(pt){drawTo(pt,'${addr}');}else{tip('该地址无法定位：${addr}');}}, '${city}');`
    // 用经典 2D 光栅 API(v3.0, BMap)：模拟器 WebView 不支持 WebGL，光栅瓦片才能显示。
    return `<!DOCTYPE html><html><head><meta charset="utf-8">`
      + `<meta name="viewport" content="initial-scale=1.0,user-scalable=no,width=device-width">`
      + `<style>html,body,#map{width:100%;height:100%;margin:0;padding:0}`
      + `#tip{position:absolute;top:10px;left:10px;right:10px;background:#fff;padding:9px 12px;`
      + `border-radius:10px;font:14px -apple-system,sans-serif;color:#334155;`
      + `box-shadow:0 2px 10px rgba(0,0,0,.15);z-index:99}</style></head><body>`
      + `<div id="tip">正在规划路线…</div><div id="map"></div><script>`
      + `function tip(t){document.getElementById('tip').innerHTML=t;}`
      + `function bmapReady(){try{`
      + `var map=new BMap.Map('map');var start=new BMap.Point(${oLng},${oLat});`
      + `map.centerAndZoom(start,13);map.enableScrollWheelZoom(true);map.addOverlay(new BMap.Marker(start));`
      + `function drawTo(dest,label){var dr=new BMap.DrivingRoute(map,{renderOptions:{map:map,autoViewport:true},`
      + `onSearchComplete:function(res){if(dr.getStatus()===0){tip('🚗 驾车路线 · '+label);}`
      + `else{tip('未找到驾车路线，已定位到 '+label);map.centerAndZoom(dest,15);map.addOverlay(new BMap.Marker(dest));}}});`
      + `dr.search(start,dest);}`
      + destJs
      + `}catch(e){tip('地图加载失败：'+e.message);}}`
      + `</script><script src="https://api.map.baidu.com/api?v=3.0&ak=${BAIDU_AK}&callback=bmapReady"></script>`
      + `</body></html>`
  }

  build() {
    Column() {
      // 顶部栏
      Row() {
        Text('‹ 返回')
          .fontSize(16).fontColor(Color.White)
          .onClick(() => { router.back() })
        Text(this.title)
          .fontSize(17).fontWeight(FontWeight.Bold).fontColor(Color.White)
          .layoutWeight(1).textAlign(TextAlign.Center).maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
        Text('  ').width(44)
      }
      .width('100%').padding({ left: 16, right: 16, top: 14, bottom: 14 })
      .backgroundColor('#2563EB')

      if (this.hasDest) {
        Web({ src: 'about:blank', controller: this.controller })
          .width('100%').layoutWeight(1)
          .javaScriptAccess(true)
          .domStorageAccess(true)
          .geolocationAccess(true)
          .mixedMode(MixedMode.All)
          .onPageEnd(() => {
            // 等初始 about:blank 加载结束后再注入真实 HTML，避免被清空；
            // baseUrl 设为白名单域，通过百度 AK 的 Referer 校验。loaded 防止重复加载。
            if (!this.loaded) {
              this.loaded = true
              this.controller.loadData(this.html, 'text/html', 'UTF-8', BASE_REFERER, BASE_REFERER)
            }
          })
      } else {
        Column() {
          Text('⚠️').fontSize(40)
          Text('该服务暂无地址或坐标，无法规划路线')
            .fontSize(15).fontColor('#64748B').margin({ top: 12 })
        }
        .width('100%').layoutWeight(1).justifyContent(FlexAlign.Center)
      }
    }
    .width('100%').height('100%').backgroundColor('#FFFFFF')
  }
}
