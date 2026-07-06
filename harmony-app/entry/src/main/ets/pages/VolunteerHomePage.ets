import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { Api, Session } from '../common/Api'
import { LocationService } from '../common/LocationService'
import { common } from '@kit.AbilityKit'
import { TaskItem, UpdateLocationPayload, LocationResult } from '../model/Models'
import { Theme } from '../common/Theme'
import { RedAlertService } from '../common/RedAlertService'

// 跳转附近避难所页携带的目标点参数
interface ShelterNavParams {
  focusTitle: string
  focusAddress: string
  focusLat?: number
  focusLng?: number
}

// 百度路线导航参数：起点(当前定位) → 终点(求助点坐标)
interface RouteNaviParams {
  oLat: number
  oLng: number
  dLat: number
  dLng: number
  destName: string
}

// 取消任务请求体
interface CancelTaskPayload {
  reason: string
  note: string
}

@Entry
@Component
struct VolunteerHomePage {
  @State tasks: TaskItem[] = []
  @State loading: boolean = false
  private reportTimer: number = -1
  private redAlertTimer: number = -1

  onPageShow() {
    this.loadTasks()
    RedAlertService.checkOnce()
  }

  aboutToAppear() {
    this.loadTasks()
    this.reportLocation()
    this.startRedAlertPolling()
    this.reportTimer = setInterval(() => {
      this.reportLocation()
    }, 60000)
  }

  aboutToDisappear() {
    if (this.reportTimer !== -1) {
      clearInterval(this.reportTimer)
      this.reportTimer = -1
    }
    this.stopRedAlertPolling()
  }

  startRedAlertPolling() {
    if (this.redAlertTimer !== -1) {
      return
    }
    RedAlertService.checkOnce()
    this.redAlertTimer = setInterval(() => {
      RedAlertService.checkOnce()
    }, 5000)
  }

  stopRedAlertPolling() {
    if (this.redAlertTimer !== -1) {
      clearInterval(this.redAlertTimer)
      this.redAlertTimer = -1
    }
  }

  async logout() {
    await Session.clear(getContext(this) as common.UIAbilityContext)
    router.replaceUrl({ url: 'pages/LoginPage' })
  }

  async reportLocation() {
    try {
      let loc: LocationResult = await LocationService.getCurrentLocation()
      let payload: UpdateLocationPayload = {
        current_latitude: loc.latitude,
        current_longitude: loc.longitude
      }
      await Api.post<UpdateLocationPayload>('/auth/update-location/', payload)
    } catch (err) {
      // 静默失败
    }
  }

  async loadTasks() {
    this.loading = true
    try {
      // 志愿者只看管理员指派给自己的任务；强制分配后无需接单/抢单
      this.tasks = await Api.getList<TaskItem>('/tasks/')
    } catch (err) {
      promptAction.showToast({ message: '加载失败，请检查后端服务' })
    } finally {
      this.loading = false
    }
  }

  viewLocation(item: TaskItem) {
    let navParams: ShelterNavParams = {
      focusTitle: item.help_request_type ? item.help_request_type : `任务 #${item.id}`,
      focusAddress: item.help_request_address
    }
    if (item.help_request_latitude && item.help_request_longitude) {
      navParams.focusLat = Number(item.help_request_latitude)
      navParams.focusLng = Number(item.help_request_longitude)
    }
    router.pushUrl({ url: 'pages/NearbyShelterPage', params: navParams })
  }

  // 一键百度地图导航：起点=当前定位，终点=求助点坐标
  async openBaiduNav(item: TaskItem) {
    if (!item.help_request_latitude || !item.help_request_longitude) {
      promptAction.showToast({ message: '该求助暂无坐标，无法导航' })
      return
    }
    let oLat: number = 39.9042
    let oLng: number = 116.4074
    try {
      let loc: LocationResult = await LocationService.getCurrentLocation()
      oLat = loc.latitude
      oLng = loc.longitude
    } catch (err) {
      promptAction.showToast({ message: '定位失败，使用默认起点' })
    }
    let params: RouteNaviParams = {
      oLat: oLat,
      oLng: oLng,
      dLat: Number(item.help_request_latitude),
      dLng: Number(item.help_request_longitude),
      destName: item.help_request_type ? item.help_request_type : `求助 #${item.help_request}`
    }
    router.pushUrl({ url: 'pages/RouteNaviPage', params: params })
  }

  // 申请取消强制分配的任务：弹原因菜单 -> 上报后端；被撤销资格则登出
  async applyCancel(item: TaskItem) {
    let keys: string[] = ['family', 'illness', 'distance', 'work', 'emergency', 'other']
    let labels: string[] = ['家庭原因', '生病', '距离过远', '工作冲突', '突发状况', '其他']
    let idx: number = -1
    try {
      let res = await promptAction.showActionMenu({
        title: '选择取消原因',
        buttons: [
          { text: '家庭原因', color: '#182431' },
          { text: '生病', color: '#182431' },
          { text: '距离过远', color: '#182431' },
          { text: '工作冲突', color: '#182431' },
          { text: '突发状况', color: '#182431' },
          { text: '其他', color: '#182431' }
        ]
      })
      idx = res.index
    } catch (err) {
      return
    }
    if (idx < 0 || idx >= keys.length) {
      return
    }
    try {
      let payload: CancelTaskPayload = { reason: keys[idx], note: labels[idx] }
      let resp = await Api.post<CancelTaskPayload>(`/tasks/${item.id}/cancel/`, payload) as Record<string, Object>
      let msg: string = resp['message'] !== undefined ? resp['message'] as string : '已申请取消'
      promptAction.showToast({ message: msg, duration: 3000 })
      let revoked: boolean = resp['revoked'] as boolean
      if (revoked === true) {
        await Session.clear(getContext(this) as common.UIAbilityContext)
        router.replaceUrl({ url: 'pages/LoginPage' })
        return
      }
      this.loadTasks()
    } catch (err) {
      promptAction.showToast({ message: '取消失败：' + (err as Error).message })
    }
  }

  @Builder
  TaskCard(item: TaskItem) {
    Column() {
      Row() {
        Text(`任务 #${item.id}`)
          .fontSize(18).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT).layoutWeight(1)
        Text(item.status_display)
          .fontSize(12).fontColor(Color.White)
          .padding({ left: 10, right: 10, top: 4, bottom: 4 })
          .backgroundColor(Theme.statusColor(item.status)).borderRadius(12)
      }.width('100%')

      Text(item.help_request_type || '居民求助')
        .fontSize(15).fontWeight(FontWeight.Medium).fontColor(Theme.PRIMARY).margin({ top: 12 })

      Text(item.help_request_description)
        .fontSize(14).fontColor(Theme.TEXT_BODY).lineHeight(21).margin({ top: 8 })

      Row() {
        Text('📍').fontSize(12)
        Text(item.help_request_address || '-').fontSize(12).fontColor(Theme.TEXT_MUTED).layoutWeight(1).margin({ left: 4 })
      }.width('100%').alignItems(VerticalAlign.Center).margin({ top: 10 })

      if (item.help_request_latitude && item.help_request_longitude) {
        Button('🧭 百度地图导航')
          .width('100%').height(40).fontSize(14).fontColor(Color.White)
          .backgroundColor('#2563EB').borderRadius(Theme.RADIUS_SM).margin({ top: 12 })
          .onClick(() => { this.openBaiduNav(item) })
      }

      if (item.help_request_address) {
        Button('查看位置 / 附近避难所')
          .width('100%').height(38).fontSize(14).fontColor(Theme.PRIMARY)
          .backgroundColor('#EEF2FF').borderRadius(Theme.RADIUS_SM).margin({ top: 8 })
          .onClick(() => { this.viewLocation(item) })
      }

      if (item.status === 'processing' || item.status === 'assigned') {
        Row() {
          Text('⏳').fontSize(14)
          Text('处理中 · 完成后由求助者拍照确认')
            .fontSize(13).fontColor(Theme.PRIMARY).margin({ left: 6 })
        }
        .width('100%').justifyContent(FlexAlign.Center).padding({ top: 10, bottom: 10 }).margin({ top: 12 })
        .backgroundColor('#EFF6FF').borderRadius(Theme.RADIUS_SM)
      }

      if (item.status === 'processing' || item.status === 'assigned') {
        Button('申请取消任务')
          .width('100%').height(36).fontSize(13).fontColor('#EF4444')
          .backgroundColor('#FEF2F2').borderRadius(Theme.RADIUS_SM).margin({ top: 8 })
          .onClick(() => { this.applyCancel(item) })
      }

      if (item.status === 'completed') {
        Row() {
          Text('🎉').fontSize(14)
          Text('该任务已完成')
            .fontSize(14).fontWeight(FontWeight.Medium).fontColor(Theme.SUCCESS).margin({ left: 6 })
        }
        .width('100%').justifyContent(FlexAlign.Center).padding({ top: 8, bottom: 8 }).margin({ top: 12 })
        .backgroundColor('#F0FDF4').borderRadius(Theme.RADIUS_SM)
      }
    }
    .width('100%').padding(16).alignItems(HorizontalAlign.Start)
    .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
    .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })
    .margin({ bottom: 12 })
  }

  build() {
    Column() {
      // 顶部渐变头部
      Row() {
        Column() {
          Row() {
            Text('🦺').fontSize(22)
            Text(`志愿者端 · ${Session.username}`)
              .fontSize(21).fontWeight(FontWeight.Bold).fontColor(Color.White).margin({ left: 8 })
          }.alignItems(VerticalAlign.Center)
          Text(`技能：${Session.skills || '未填写'}`)
            .fontSize(13).fontColor('#DBEAFE').margin({ top: 8 })
        }.layoutWeight(1).alignItems(HorizontalAlign.Start)

        Button('退出')
          .height(38).fontSize(14).fontColor(Color.White).backgroundColor('#EF4444')
          .borderRadius(Theme.RADIUS_SM).margin({ right: 8 })
          .onClick(() => { this.logout() })

        Button('消息')
          .height(38).fontSize(14).fontColor(Color.White).backgroundColor('#0F766E')
          .borderRadius(Theme.RADIUS_SM)
          .onClick(() => { router.pushUrl({ url: 'pages/NotificationsPage' }) })
      }
      .width('100%').padding({ left: 20, right: 20, top: 22, bottom: 26 }).alignItems(VerticalAlign.Center)
      .linearGradient({
        angle: 145,
        colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY, 0.55], [Theme.PRIMARY_DARK, 1.0]]
      }).borderRadius({ bottomLeft: 28, bottomRight: 28 })

      // 说明 + 刷新卡片
      Column() {
        Row() {
          Text('📋').fontSize(16)
          Text('我的任务由管理员统一指派')
            .fontSize(14).fontWeight(FontWeight.Medium).fontColor(Theme.TEXT).layoutWeight(1).margin({ left: 8 })
          Text(`${this.tasks.length}`).fontSize(14).fontColor(Theme.TEXT_MUTED)
        }.width('100%').alignItems(VerticalAlign.Center)

        Button(this.loading ? '刷新中...' : '刷新任务')
          .width('100%').height(42).fontSize(15).fontWeight(FontWeight.Medium)
          .fontColor(Color.White).borderRadius(Theme.RADIUS_SM)
          .linearGradient({ angle: 90, colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY_DARK, 1.0]] })
          .margin({ top: 12 })
          .onClick(() => { this.loadTasks() })
      }
      .width('90%').padding(16).margin({ top: -16 }).alignItems(HorizontalAlign.Start)
      .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
      .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })

      // 任务列表
      if (this.tasks.length === 0) {
        Column() {
          Text('📭').fontSize(52).margin({ bottom: 12 })
          Text('暂无指派给你的任务').fontSize(15).fontColor(Theme.TEXT_BODY)
          Text('等待管理员分配任务').fontSize(13).fontColor(Theme.TEXT_MUTED).margin({ top: 6 })
        }
        .width('100%').layoutWeight(1).justifyContent(FlexAlign.Center).alignItems(HorizontalAlign.Center)
      } else {
        List() {
          ForEach(this.tasks, (item: TaskItem) => {
            ListItem() { this.TaskCard(item) }
          }, (item: TaskItem) => `${item.id}-${item.status}`)
        }.layoutWeight(1).width('100%').padding({ left: 16, right: 16, top: 16 }).scrollBar(BarState.Off)
      }
    }
    .width('100%').height('100%').backgroundColor(Theme.BG)
  }
}
