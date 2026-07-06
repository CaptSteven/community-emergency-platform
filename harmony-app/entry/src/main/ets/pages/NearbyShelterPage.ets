import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { BusinessError, AsyncCallback } from '@ohos.base'
import { common, Want } from '@kit.AbilityKit'
import { Api } from '../common/Api'
import { LocationService } from '../common/LocationService'
import { ShelterItem, LocationResult } from '../model/Models'
import { Theme } from '../common/Theme'
// Map Kit 需在 AppGallery Connect 配置后生效，未配置时自动降级为列表。
// 该导入在未配置的纯净构建中可能无法解析，属预期情况。
import { map, MapComponent, mapCommon } from '@kit.MapKit'

// 从志愿者端跳转时携带的目标点参数（居民求助位置）
interface ShelterRouteParams {
  focusLat: number
  focusLng: number
  focusTitle: string
  focusAddress: string
}

// 判断路由参数中是否携带有效经纬度
function hasValidCoords(p: ShelterRouteParams): boolean {
  return p !== undefined && p.focusLat !== undefined && p.focusLng !== undefined
    && p.focusLat !== 0 && p.focusLng !== 0
}

@Entry
@Component
struct NearbyShelterPage {
  @State shelters: ShelterItem[] = []
  @State loading: boolean = false
  @State locatedText: string = ''
  @State hasFocus: boolean = false
  @State showFocusHeader: boolean = false
  @State focusTitle: string = ''
  @State focusAddress: string = ''
  // Map Kit 是否可用；默认 false，仅在成功初始化地图后置 true，否则始终使用列表降级
  @State mapReady: boolean = false

  private centerLat: number = 39.9042
  private centerLng: number = 116.4074
  private mapController?: map.MapComponentController
  // 地图参数与回调给出默认值（非可选），避免 @Builder 中的可选成员窄化问题
  private mapOptions: mapCommon.MapOptions = {
    position: {
      target: { latitude: 39.9042, longitude: 116.4074 },
      zoom: 14
    }
  }
  private mapCallback: AsyncCallback<map.MapComponentController> =
    (err: BusinessError, controller: map.MapComponentController) => {
      if (err) {
        this.mapReady = false
        return
      }
      this.mapController = controller
      this.addMapMarkers()
    }

  aboutToAppear() {
    this.parseParams()
    this.setupMap()
    this.init()
  }

  parseParams(): void {
    let params = router.getParams() as ShelterRouteParams
    if (!params) {
      return
    }
    if (params.focusTitle || params.focusAddress) {
      this.showFocusHeader = true
      this.focusTitle = params.focusTitle ? params.focusTitle : '求助位置'
      this.focusAddress = params.focusAddress ? params.focusAddress : ''
    }
    // 仅当携带有效坐标时才以该坐标作为查询中心；否则回退到用户当前定位
    if (hasValidCoords(params)) {
      this.hasFocus = true
      this.centerLat = params.focusLat
      this.centerLng = params.focusLng
    }
  }

  // 尝试初始化 Map Kit；任何异常都降级为列表。
  setupMap(): void {
    try {
      let target: mapCommon.LatLng = {
        latitude: this.centerLat,
        longitude: this.centerLng
      }
      let cameraPosition: mapCommon.CameraPosition = {
        target: target,
        zoom: 14
      }
      this.mapOptions = {
        position: cameraPosition
      }
      // 说明：此处仅表示已构造地图参数；若无 AGC 配置，MapComponent 在真机上会渲染为空，
      // 下方列表始终作为功能性降级方案存在。
      this.mapReady = true
    } catch (e) {
      this.mapReady = false
    }
  }

  addMapMarkers(): void {
    try {
      if (!this.mapController) {
        return
      }
      // 中心点（用户/求助位置）标记
      let centerMarker: mapCommon.MarkerOptions = {
        position: { latitude: this.centerLat, longitude: this.centerLng },
        title: this.hasFocus ? this.focusTitle : '我的位置'
      }
      this.mapController.addMarker(centerMarker)
      // 各避难所标记
      this.shelters.forEach((s: ShelterItem) => {
        let markerOptions: mapCommon.MarkerOptions = {
          position: { latitude: Number(s.latitude), longitude: Number(s.longitude) },
          title: s.name
        }
        if (this.mapController) {
          this.mapController.addMarker(markerOptions)
        }
      })
    } catch (e) {
      // 标记失败不影响列表展示
    }
  }

  async init() {
    this.loading = true
    try {
      // 未携带目标点时，使用用户当前定位作为查询中心
      if (!this.hasFocus) {
        let loc: LocationResult = await LocationService.getCurrentLocation()
        this.centerLat = loc.latitude
        this.centerLng = loc.longitude
      }
      this.locatedText = `中心点：${this.centerLat.toFixed(4)}, ${this.centerLng.toFixed(4)}`

      let path = `/shelters/nearby/?lat=${this.centerLat}&lng=${this.centerLng}&limit=10`
      this.shelters = await Api.get(path) as ShelterItem[]
      this.addMapMarkers()
    } catch (err) {
      let e = err as BusinessError
      promptAction.showToast({ message: e.message ? e.message : '加载附近避难所失败' })
    } finally {
      this.loading = false
    }
  }

  // “导航”：优先拉起手机地图应用（花瓣地图）进行路线导航；
  // 无可用地图应用（如模拟器）时降级为坐标弹窗。
  openNavigation(item: ShelterItem): void {
    let context = getContext(this) as common.UIAbilityContext
    let want: Want = {
      action: 'ohos.want.action.viewData',
      entities: ['entity.system.browsable'],
      uri: `petalmaps://navigation?daddr=${item.latitude},${item.longitude}&type=drive`
    }
    context.startAbility(want).catch((err: BusinessError) => {
      AlertDialog.show({
        title: `导航到 ${item.name}`,
        message: `地址：${item.address}\n坐标：${item.latitude}, ${item.longitude}\n\n未检测到可用的地图应用，请在系统地图中按坐标前往。`,
        confirm: {
          value: '知道了',
          action: () => {
          }
        }
      })
    })
  }

  @Builder
  MapArea() {
    // Map Kit 可用时渲染地图，否则不渲染（下方列表始终可用）
    if (this.mapReady) {
      MapComponent({ mapOptions: this.mapOptions, mapCallback: this.mapCallback })
        .width('100%')
        .height(220)
    }
  }

  // 单条信息行：图标 + 文案，统一排版
  @Builder
  InfoRow(icon: string, label: string, value: string) {
    Row() {
      Text(icon)
        .fontSize(13)
        .margin({ right: 6 })
      Text(label)
        .fontSize(13)
        .fontColor(Theme.TEXT_MUTED)
      Text(value)
        .fontSize(13)
        .fontColor(Theme.TEXT_BODY)
        .layoutWeight(1)
    }
    .width('100%')
    .alignItems(VerticalAlign.Center)
    .margin({ top: 8 })
  }

  build() {
    Column() {
      // 顶部渐变头部
      Column() {
        Row() {
          Text(this.showFocusHeader ? '导航到求助位置' : '附近避难所')
            .fontSize(22)
            .fontWeight(FontWeight.Bold)
            .fontColor(Color.White)
            .layoutWeight(1)

          Button('返回')
            .height(36)
            .fontSize(14)
            .fontColor(Color.White)
            .backgroundColor('#33FFFFFF')
            .borderRadius(Theme.RADIUS_SM)
            .onClick(() => {
              router.back()
            })
        }
        .width('100%')

        Row() {
          Text('🏠')
            .fontSize(14)
            .margin({ right: 6 })
          Text('就近查找应急避难场所')
            .fontSize(13)
            .fontColor('#DBEAFE')
        }
        .width('100%')
        .margin({ top: 8 })
        .alignItems(VerticalAlign.Center)
      }
      .width('100%')
      .padding({ left: 18, right: 18, top: 20, bottom: 20 })
      .linearGradient({
        angle: 145,
        colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY, 0.55], [Theme.PRIMARY_DARK, 1.0]]
      })
      .borderRadius({ bottomLeft: 28, bottomRight: 28 })

      Scroll() {
        Column() {
          this.MapArea()

          // 目标点卡片（从志愿者端跳转携带）
          if (this.showFocusHeader) {
            Column() {
              Row() {
                Text('📍')
                  .fontSize(15)
                  .margin({ right: 6 })
                Text('目标位置')
                  .fontSize(12)
                  .fontColor(Color.White)
                  .padding({ left: 10, right: 10, top: 4, bottom: 4 })
                  .backgroundColor(Theme.PRIMARY)
                  .borderRadius(12)
              }
              .width('100%')
              .alignItems(VerticalAlign.Center)

              Text(this.focusTitle)
                .fontSize(16)
                .fontWeight(FontWeight.Bold)
                .fontColor(Theme.TEXT)
                .margin({ top: 10 })

              if (this.focusAddress) {
                Text(`地址：${this.focusAddress}`)
                  .fontSize(13)
                  .fontColor(Theme.TEXT_BODY)
                  .margin({ top: 6 })
              }
            }
            .width('100%')
            .alignItems(HorizontalAlign.Start)
            .padding(14)
            .backgroundColor(Theme.CARD)
            .borderRadius(Theme.RADIUS)
            .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })
            .margin({ bottom: 12 })
          }

          // 定位信息 + 刷新
          Row() {
            Column() {
              Text('查询中心')
                .fontSize(12)
                .fontColor(Theme.TEXT_MUTED)
              Text(this.locatedText ? this.locatedText : '定位中…')
                .fontSize(13)
                .fontColor(Theme.TEXT_BODY)
                .margin({ top: 4 })
            }
            .alignItems(HorizontalAlign.Start)
            .layoutWeight(1)

            Button(this.loading ? '加载中...' : '刷新')
              .height(36)
              .fontSize(14)
              .borderRadius(Theme.RADIUS_SM)
              .backgroundColor(Theme.PRIMARY)
              .enabled(!this.loading)
              .onClick(() => {
                this.init()
              })
          }
          .width('100%')
          .padding(14)
          .backgroundColor(Theme.CARD)
          .borderRadius(Theme.RADIUS)
          .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })
          .margin({ bottom: 12 })
          .alignItems(VerticalAlign.Center)

          // 加载态
          if (this.loading && this.shelters.length === 0) {
            Column() {
              LoadingProgress()
                .width(44)
                .height(44)
                .color(Theme.PRIMARY)
              Text('正在查找附近避难所…')
                .fontSize(14)
                .fontColor(Theme.TEXT_MUTED)
                .margin({ top: 12 })
            }
            .width('100%')
            .padding({ top: 60, bottom: 60 })
            .justifyContent(FlexAlign.Center)
          } else if (this.shelters.length === 0) {
            // 空态
            Column() {
              Text('🏕️')
                .fontSize(52)
              Text('附近暂无避难所')
                .fontSize(16)
                .fontWeight(FontWeight.Bold)
                .fontColor(Theme.TEXT_BODY)
                .margin({ top: 12 })
              Text('可稍后下拉刷新，或扩大查询范围')
                .fontSize(13)
                .fontColor(Theme.TEXT_MUTED)
                .margin({ top: 6 })
            }
            .width('100%')
            .padding({ top: 60, bottom: 60 })
            .justifyContent(FlexAlign.Center)
          } else {
            // 避难所卡片列表
            ForEach(this.shelters, (item: ShelterItem) => {
              Column() {
                Row() {
                  Text(item.name)
                    .fontSize(17)
                    .fontWeight(FontWeight.Bold)
                    .fontColor(Theme.TEXT)
                    .layoutWeight(1)

                  if (item.distance_km !== undefined) {
                    Text(`${item.distance_km.toFixed(1)} km`)
                      .fontSize(12)
                      .fontColor(Color.White)
                      .padding({ left: 10, right: 10, top: 4, bottom: 4 })
                      .backgroundColor(Theme.TEAL)
                      .borderRadius(12)
                  }
                }
                .width('100%')
                .alignItems(VerticalAlign.Center)

                this.InfoRow('📍', '地址　', item.address)
                this.InfoRow('👥', '容纳　', `${item.capacity} 人`)
                this.InfoRow('☎️', '电话　', item.contact_phone)

                Button('导 航')
                  .height(40)
                  .width('100%')
                  .fontSize(15)
                  .fontWeight(FontWeight.Medium)
                  .borderRadius(Theme.RADIUS_SM)
                  .linearGradient({
                    angle: 90,
                    colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY_DARK, 1.0]]
                  })
                  .margin({ top: 14 })
                  .onClick(() => {
                    this.openNavigation(item)
                  })
              }
              .width('100%')
              .padding(16)
              .backgroundColor(Theme.CARD)
              .borderRadius(Theme.RADIUS)
              .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })
              .margin({ bottom: 12 })
            }, (item: ShelterItem) => item.id.toString())
          }
        }
        .width('90%')
        .margin({ top: 14, bottom: 14 })
      }
      .layoutWeight(1)
      .width('100%')
      .align(Alignment.Top)
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG)
  }
}
