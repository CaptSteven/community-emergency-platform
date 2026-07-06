import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { Api, Session } from '../common/Api'
import { LocationService } from '../common/LocationService'
import { common } from '@kit.AbilityKit'
import {
  CompleteTaskPayload,
  TaskItem,
  HelpRequestItem,
  UpdateLocationPayload,
  LocationResult
} from '../model/Models'
import { Theme } from '../common/Theme'
import { RedAlertService } from '../common/RedAlertService'

interface ShelterNavParams {
  focusTitle: string
  focusAddress: string
  focusLat?: number
  focusLng?: number
}

@Entry
@Component
struct VolunteerHomePage {
  @State tasks: TaskItem[] = []
  @State availableRequests: HelpRequestItem[] = []
  @State loading: boolean = false
  @State feedback: string = '已完成现场协助处理'
  @State currentTab: number = 0
  private reportTimer: number = -1
  private redAlertTimer: number = -1

  onPageShow() {
    this.loadAll()
    RedAlertService.checkOnce()
  }

  aboutToAppear() {
    this.loadAll()
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

  async loadAll() {
    this.loading = true
    try {
      this.tasks = await Api.getList<TaskItem>('/tasks/')
      this.availableRequests = await Api.getList<HelpRequestItem>('/help-requests/?status=pending')
    } catch (err) {
      promptAction.showToast({ message: '加载失败，请检查后端服务' })
    } finally {
      this.loading = false
    }
  }

  async claimRequest(id: number) {
    try {
      await Api.postEmpty(`/help-requests/${id}/claim/`)
      promptAction.showToast({ message: '认领成功，请尽快处理' })
      this.reportLocation()
      this.loadAll()
    } catch (err) {
      promptAction.showToast({ message: '认领失败：' + (err as Error).message })
    }
  }

  async acceptTask(id: number) {
    try {
      await Api.postEmpty(`/tasks/${id}/accept/`)
      promptAction.showToast({ message: '接单成功' })
      this.loadAll()
    } catch (err) {
      promptAction.showToast({ message: '接单失败' })
    }
  }

  async completeTask(id: number) {
    try {
      let payload: CompleteTaskPayload = { feedback: this.feedback }
      await Api.post<CompleteTaskPayload>(`/tasks/${id}/complete/`, payload)
      promptAction.showToast({ message: '任务已完成' })
      this.loadAll()
    } catch (err) {
      promptAction.showToast({ message: '完成任务失败' })
    }
  }

  viewLocation(item: TaskItem) {
    let navParams: ShelterNavParams = {
      focusTitle: item.help_request_type ? item.help_request_type : `任务 #${item.id}`,
      focusAddress: item.help_request_address
    }

    // 后端任务列表已补充求助经纬度；有坐标时按求助点查附近避难所，没有坐标再回退到当前位置。
    if (item.help_request_latitude && item.help_request_longitude) {
      navParams.focusLat = Number(item.help_request_latitude)
      navParams.focusLng = Number(item.help_request_longitude)
    }

    router.pushUrl({ url: 'pages/NearbyShelterPage', params: navParams })
  }

  @Builder
  ClaimCard(item: HelpRequestItem) {
    Column() {
      Row() {
        Text(item.request_type_display)
          .fontSize(17).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT).layoutWeight(1)
        Text(item.urgency_display)
          .fontSize(12).fontColor(Color.White)
          .padding({ left: 10, right: 10, top: 4, bottom: 4 })
          .backgroundColor(Theme.urgencyColor(item.urgency)).borderRadius(12)
      }.width('100%')

      Text(item.description)
        .fontSize(14).fontColor(Theme.TEXT_BODY).lineHeight(21).margin({ top: 10 })

      Row() {
        Text('📍').fontSize(12)
        Text(item.address || '-').fontSize(12).fontColor(Theme.TEXT_MUTED).layoutWeight(1).margin({ left: 4 })
      }.width('100%').alignItems(VerticalAlign.Center).margin({ top: 10 })

      Text(`提交人：${item.resident_name}`)
        .fontSize(12).fontColor(Theme.TEXT_MUTED).margin({ top: 8 })

      Button('认 领')
        .width('100%').height(42).fontSize(15).fontWeight(FontWeight.Medium)
        .fontColor(Color.White).backgroundColor(Theme.DANGER).borderRadius(Theme.RADIUS_SM)
        .margin({ top: 14 })
        .onClick(() => { this.claimRequest(item.id) })
    }
    .width('100%').padding(16).alignItems(HorizontalAlign.Start)
    .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
    .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })
    .margin({ bottom: 12 })
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

      if (item.help_request_address) {
        Button('查看位置 / 导航')
          .width('100%').height(38).fontSize(14).fontColor(Color.White)
          .backgroundColor(Theme.PURPLE).borderRadius(Theme.RADIUS_SM).margin({ top: 12 })
          .onClick(() => { this.viewLocation(item) })
      }

      if (item.feedback) {
        Row() {
          Text('✅').fontSize(12)
          Text(`反馈：${item.feedback}`).fontSize(12).fontColor(Theme.SUCCESS).layoutWeight(1).margin({ left: 4 })
        }.width('100%').alignItems(VerticalAlign.Top).padding(10).margin({ top: 12 })
        .backgroundColor('#F0FDF4').borderRadius(Theme.RADIUS_SM)
      }

      Row() {
        if (item.status === 'assigned') {
          Button('接 单')
            .layoutWeight(1).height(42).fontSize(15).fontWeight(FontWeight.Medium)
            .fontColor(Color.White).backgroundColor(Theme.PRIMARY).borderRadius(Theme.RADIUS_SM)
            .onClick(() => { this.acceptTask(item.id) })
        }
        if (item.status === 'processing') {
          Button('完成任务')
            .layoutWeight(1).height(42).fontSize(15).fontWeight(FontWeight.Medium)
            .fontColor(Color.White).backgroundColor(Theme.SUCCESS).borderRadius(Theme.RADIUS_SM)
            .onClick(() => { this.completeTask(item.id) })
        }
        if (item.status === 'completed') {
          Row() {
            Text('🎉').fontSize(14)
            Text('该任务已完成').fontSize(14).fontWeight(FontWeight.Medium).fontColor(Theme.SUCCESS).margin({ left: 6 })
          }.width('100%').justifyContent(FlexAlign.Center).padding({ top: 8, bottom: 8 })
          .backgroundColor('#F0FDF4').borderRadius(Theme.RADIUS_SM)
        }
      }.width('100%').margin({ top: 14 })
    }
    .width('100%').padding(16).alignItems(HorizontalAlign.Start)
    .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
    .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })
    .margin({ bottom: 12 })
  }

  build() {
    Column() {
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
      .width('100%').padding({ left: 20, right: 20, top: 22, bottom: 26 })
      .alignItems(VerticalAlign.Center)
      .linearGradient({
        angle: 145,
        colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY, 0.55], [Theme.PRIMARY_DARK, 1.0]]
      }).borderRadius({ bottomLeft: 28, bottomRight: 28 })

      Column() {
        Text('完成反馈').fontSize(13).fontColor(Theme.TEXT_MUTED).margin({ bottom: 8 })
        TextInput({ placeholder: '完成任务时的反馈内容', text: this.feedback })
          .height(46).fontSize(14).backgroundColor('#F8FAFC').borderRadius(Theme.RADIUS_SM)
          .border({ width: 1, color: Theme.BORDER }).padding({ left: 12, right: 12 })
          .onChange((value: string) => { this.feedback = value })
        Button(this.loading ? '刷新中...' : '刷新')
          .width('100%').height(44).fontSize(15).fontWeight(FontWeight.Medium)
          .fontColor(Color.White).borderRadius(Theme.RADIUS_SM)
          .linearGradient({ angle: 90, colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY_DARK, 1.0]] })
          .margin({ top: 12 })
          .onClick(() => { this.loadAll() })
      }
      .width('90%').padding(16).margin({ top: -16 }).alignItems(HorizontalAlign.Start)
      .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
      .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })

      Row() {
        Text(`可认领求助 (${this.availableRequests.length})`)
          .fontSize(15).fontWeight(this.currentTab === 0 ? FontWeight.Bold : FontWeight.Medium)
          .fontColor(this.currentTab === 0 ? Color.White : Theme.TEXT_BODY)
          .layoutWeight(1).height(38).textAlign(TextAlign.Center)
          .backgroundColor(this.currentTab === 0 ? Theme.DANGER : '#F1F5F9').borderRadius(Theme.RADIUS_SM)
          .onClick(() => { this.currentTab = 0 })
        Blank().width(8)
        Text(`我的任务 (${this.tasks.length})`)
          .fontSize(15).fontWeight(this.currentTab === 1 ? FontWeight.Bold : FontWeight.Medium)
          .fontColor(this.currentTab === 1 ? Color.White : Theme.TEXT_BODY)
          .layoutWeight(1).height(38).textAlign(TextAlign.Center)
          .backgroundColor(this.currentTab === 1 ? Theme.PRIMARY : '#F1F5F9').borderRadius(Theme.RADIUS_SM)
          .onClick(() => { this.currentTab = 1 })
      }.width('90%').margin({ top: 14 })

      if (this.currentTab === 0) {
        if (this.availableRequests.length === 0) {
          Column() {
            Text('📭').fontSize(52).margin({ bottom: 12 })
            Text('暂无可认领的求助').fontSize(15).fontColor(Theme.TEXT_BODY)
            Text('居民提交新求助后会出现在这里').fontSize(13).fontColor(Theme.TEXT_MUTED).margin({ top: 6 })
          }.width('100%').layoutWeight(1).justifyContent(FlexAlign.Center).alignItems(HorizontalAlign.Center)
        } else {
          List() {
            ForEach(this.availableRequests, (item: HelpRequestItem) => {
              ListItem() { this.ClaimCard(item) }
            }, (item: HelpRequestItem) => `claim-${item.id}`)
          }.layoutWeight(1).width('100%').padding({ left: 16, right: 16, top: 12 }).scrollBar(BarState.Off)
        }
      } else {
        if (this.tasks.length === 0) {
          Column() {
            Text('📭').fontSize(52).margin({ bottom: 12 })
            Text('暂无任务').fontSize(15).fontColor(Theme.TEXT_BODY)
            Text('认领求助或等待管理员分配').fontSize(13).fontColor(Theme.TEXT_MUTED).margin({ top: 6 })
          }.width('100%').layoutWeight(1).justifyContent(FlexAlign.Center).alignItems(HorizontalAlign.Center)
        } else {
          List() {
            ForEach(this.tasks, (item: TaskItem) => {
              ListItem() { this.TaskCard(item) }
            }, (item: TaskItem) => `${item.id}-${item.status}`)
          }.layoutWeight(1).width('100%').padding({ left: 16, right: 16, top: 12 }).scrollBar(BarState.Off)
        }
      }
    }
    .width('100%').height('100%').backgroundColor(Theme.BG)
  }
}