import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { Api, Session } from '../common/Api'
import { LocationService } from '../common/LocationService'
import { ServiceVisitItem, CompleteVisitPayload, CancelVisitPayload, LocationResult } from '../model/Models'
import { Theme } from '../common/Theme'

// 百度路线导航参数：起点(当前定位) → 终点(服务点坐标)
interface RouteNaviParams {
  oLat: number
  oLng: number
  dLat: number
  dLng: number
  destName: string
}

@Entry
@Component
struct VolunteerServicePage {
  @State visits: ServiceVisitItem[] = []
  @State loading: boolean = false
  // 完成表单
  @State showComplete: boolean = false
  @State activeVisit: ServiceVisitItem | null = null
  @State systolic: string = ''
  @State diastolic: string = ''
  @State heartRate: string = ''
  @State temperature: string = ''
  @State healthNote: string = ''
  @State feedback: string = ''

  onPageShow() {
    this.loadVisits()
  }

  aboutToAppear() {
    this.loadVisits()
  }

  async loadVisits() {
    this.loading = true
    try {
      this.visits = await Api.getList<ServiceVisitItem>('/service-visits/')
    } catch (err) {
      promptAction.showToast({ message: '加载失败，请检查后端服务' })
    } finally {
      this.loading = false
    }
  }

  async openBaiduNav(item: ServiceVisitItem) {
    if (item.latitude === null || item.longitude === null) {
      promptAction.showToast({ message: '该服务暂无坐标，无法导航' })
      return
    }
    let oLat: number = 43.8256
    let oLng: number = 87.6417
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
      dLat: item.latitude as number,
      dLng: item.longitude as number,
      destName: item.service_type_name
    }
    router.pushUrl({ url: 'pages/RouteNaviPage', params: params })
  }

  async startVisit(item: ServiceVisitItem) {
    try {
      await Api.postEmpty(`/service-visits/${item.id}/start/`)
      promptAction.showToast({ message: '已开始服务' })
      this.loadVisits()
    } catch (err) {
      promptAction.showToast({ message: '操作失败：' + (err as Error).message })
    }
  }

  openCompleteForm(item: ServiceVisitItem) {
    this.activeVisit = item
    this.systolic = ''
    this.diastolic = ''
    this.heartRate = ''
    this.temperature = ''
    this.healthNote = ''
    this.feedback = ''
    this.showComplete = true
  }

  async submitComplete() {
    if (this.activeVisit === null) {
      return
    }
    let payload: CompleteVisitPayload = {
      feedback: this.feedback,
      health_note: this.healthNote
    }
    if (this.systolic !== '') {
      payload.systolic = Number(this.systolic)
    }
    if (this.diastolic !== '') {
      payload.diastolic = Number(this.diastolic)
    }
    if (this.heartRate !== '') {
      payload.heart_rate = Number(this.heartRate)
    }
    if (this.temperature !== '') {
      payload.temperature = Number(this.temperature)
    }
    try {
      await Api.post<CompleteVisitPayload>(`/service-visits/${this.activeVisit.id}/complete/`, payload)
      promptAction.showToast({ message: '服务已完成' })
      this.showComplete = false
      this.activeVisit = null
      this.loadVisits()
    } catch (err) {
      promptAction.showToast({ message: '提交失败：' + (err as Error).message })
    }
  }

  async applyCancel(item: ServiceVisitItem) {
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
      let payload: CancelVisitPayload = { reason: keys[idx], note: labels[idx] }
      let resp = await Api.post<CancelVisitPayload>(`/service-visits/${item.id}/cancel/`, payload) as Record<string, Object>
      let msg: string = resp['message'] !== undefined ? resp['message'] as string : '已申请取消'
      promptAction.showToast({ message: msg, duration: 3000 })
      let revoked: boolean = resp['revoked'] as boolean
      if (revoked === true) {
        router.replaceUrl({ url: 'pages/LoginPage' })
        return
      }
      this.loadVisits()
    } catch (err) {
      promptAction.showToast({ message: '取消失败：' + (err as Error).message })
    }
  }

  // 单项健康小徽章：标签 + 数值，醒目分隔
  @Builder
  HealthBadge(label: string, value: string, unit: string) {
    Column() {
      Text(label).fontSize(12).fontColor(Theme.TEXT_MUTED)
      Row() {
        Text(value).fontSize(18).fontWeight(FontWeight.Bold).fontColor(Theme.SUCCESS)
        if (unit !== '') {
          Text(unit).fontSize(12).fontColor(Theme.TEXT_MUTED).margin({ left: 2, bottom: 2 })
        }
      }.alignItems(VerticalAlign.Bottom).margin({ top: 2 })
    }
    .layoutWeight(1).alignItems(HorizontalAlign.Center)
    .padding({ top: 8, bottom: 8 })
  }

  @Builder
  VisitCard(item: ServiceVisitItem) {
    Column() {
      Row() {
        Text(`${item.service_type_icon} ${item.service_type_name}`)
          .fontSize(17).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT).layoutWeight(1)
        Text(item.status_display)
          .fontSize(12).fontColor(Color.White)
          .padding({ left: 10, right: 10, top: 4, bottom: 4 })
          .backgroundColor(Theme.statusColor(item.status)).borderRadius(12)
      }.width('100%')

      Row() {
        Text('👴').fontSize(13)
        Text(`受助居民：${item.resident_name}`).fontSize(14).fontColor(Theme.TEXT_BODY).margin({ left: 6 })
      }.width('100%').margin({ top: 10 })

      Row() {
        Text('📅').fontSize(13)
        Text(`计划日期：${item.scheduled_date}`).fontSize(13).fontColor(Theme.TEXT_MUTED).margin({ left: 6 })
      }.width('100%').margin({ top: 6 })

      Row() {
        Text('📍').fontSize(12)
        Text(item.address || '-').fontSize(12).fontColor(Theme.TEXT_MUTED).layoutWeight(1).margin({ left: 4 })
      }.width('100%').alignItems(VerticalAlign.Center).margin({ top: 6 })

      if (item.status === 'completed' && item.needs_health_record) {
        Column() {
          Row() {
            Text('❤️').fontSize(14)
            Text('本次健康记录').fontSize(Theme.FS_SMALL).fontWeight(FontWeight.Medium).fontColor(Theme.SUCCESS).margin({ left: 6 })
          }.width('100%')
          Row() {
            this.HealthBadge('血压', `${item.systolic ?? '—'}/${item.diastolic ?? '—'}`, 'mmHg')
            Divider().vertical(true).height(28).color(Theme.BORDER)
            this.HealthBadge('心率', `${item.heart_rate ?? '—'}`, '次/分')
            Divider().vertical(true).height(28).color(Theme.BORDER)
            this.HealthBadge('体温', `${item.temperature ?? '—'}`, '℃')
          }.width('100%').margin({ top: 6 })
          if (item.health_note !== '') {
            Text(item.health_note).fontSize(Theme.FS_SMALL).fontColor(Theme.TEXT_BODY).margin({ top: 6 })
          }
        }
        .width('100%').alignItems(HorizontalAlign.Start).padding(12).margin({ top: 12 })
        .backgroundColor(Theme.SUCCESS_LIGHT).borderRadius(Theme.RADIUS_SM)
      }

      if (item.latitude !== null && item.longitude !== null) {
        Button('🧭 百度地图导航')
          .width('100%').height(40).fontSize(14).fontColor(Color.White)
          .backgroundColor('#2563EB').borderRadius(Theme.RADIUS_SM).margin({ top: 12 })
          .onClick(() => { this.openBaiduNav(item) })
      }

      if (item.status === 'assigned') {
        Button('开始服务')
          .width('100%').height(40).fontSize(14).fontColor(Color.White)
          .backgroundColor(Theme.PRIMARY).borderRadius(Theme.RADIUS_SM).margin({ top: 8 })
          .onClick(() => { this.startVisit(item) })
      }

      if (item.status === 'assigned' || item.status === 'processing') {
        Button('完成并录入记录')
          .width('100%').height(40).fontSize(14).fontColor(Color.White)
          .backgroundColor(Theme.SUCCESS).borderRadius(Theme.RADIUS_SM).margin({ top: 8 })
          .onClick(() => { this.openCompleteForm(item) })

        Button('申请取消服务')
          .width('100%').height(36).fontSize(13).fontColor('#EF4444')
          .backgroundColor('#FEF2F2').borderRadius(Theme.RADIUS_SM).margin({ top: 8 })
          .onClick(() => { this.applyCancel(item) })
      }
    }
    .width('100%').padding(16).alignItems(HorizontalAlign.Start)
    .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
    .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })
    .margin({ bottom: 12 })
  }

  @Builder
  CompleteForm() {
    Column() {
      Text(`完成服务 · ${this.activeVisit?.service_type_name ?? ''}`)
        .fontSize(18).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT).margin({ bottom: 4 })
      Text(`受助居民：${this.activeVisit?.resident_name ?? ''}`)
        .fontSize(13).fontColor(Theme.TEXT_MUTED).margin({ bottom: 14 })

      if (this.activeVisit?.needs_health_record === true) {
        Text('健康记录（选填）').fontSize(14).fontWeight(FontWeight.Medium).fontColor(Theme.PRIMARY).margin({ bottom: 8 })
        Row() {
          TextInput({ placeholder: '收缩压(高压)' }).type(InputType.Number).layoutWeight(1)
            .onChange((v: string) => { this.systolic = v })
          Text('/').fontSize(16).margin({ left: 6, right: 6 })
          TextInput({ placeholder: '舒张压(低压)' }).type(InputType.Number).layoutWeight(1)
            .onChange((v: string) => { this.diastolic = v })
        }.width('100%').margin({ bottom: 10 })
        Row() {
          TextInput({ placeholder: '心率(次/分)' }).type(InputType.Number).layoutWeight(1)
            .onChange((v: string) => { this.heartRate = v })
          Text(' ').fontSize(16).margin({ left: 6, right: 6 })
          TextInput({ placeholder: '体温(℃)' }).type(InputType.Number).layoutWeight(1)
            .onChange((v: string) => { this.temperature = v })
        }.width('100%').margin({ bottom: 10 })
        TextArea({ placeholder: '健康备注，如血压偏高建议清淡饮食' })
          .height(70).width('100%').margin({ bottom: 12 })
          .onChange((v: string) => { this.healthNote = v })
      }

      Text('服务反馈').fontSize(14).fontWeight(FontWeight.Medium).fontColor(Theme.TEXT).margin({ bottom: 8 })
      TextArea({ placeholder: '简述本次上门服务情况' })
        .height(80).width('100%').margin({ bottom: 16 })
        .onChange((v: string) => { this.feedback = v })

      Row() {
        Button('取消')
          .layoutWeight(1).height(44).fontSize(15).fontColor(Theme.TEXT_BODY)
          .backgroundColor('#E5E7EB').borderRadius(Theme.RADIUS_SM)
          .onClick(() => { this.showComplete = false })
        Button('提交完成')
          .layoutWeight(1).height(44).fontSize(15).fontColor(Color.White)
          .backgroundColor(Theme.SUCCESS).borderRadius(Theme.RADIUS_SM).margin({ left: 12 })
          .onClick(() => { this.submitComplete() })
      }.width('100%')
    }
    .width('90%').padding(18).margin({ top: 16 }).alignItems(HorizontalAlign.Start)
    .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
    .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })
  }

  build() {
    Column() {
      // 顶部头部
      Row() {
        Button('‹ 返回')
          .height(36).fontSize(14).fontColor(Color.White).backgroundColor('#ffffff33')
          .borderRadius(Theme.RADIUS_SM)
          .onClick(() => { router.back() })
        Column() {
          Text('我的上门服务').fontSize(20).fontWeight(FontWeight.Bold).fontColor(Color.White)
          Text(`志愿者 · ${Session.username}`).fontSize(12).fontColor('#DBEAFE').margin({ top: 4 })
        }.layoutWeight(1).alignItems(HorizontalAlign.Start).margin({ left: 12 })
      }
      .width('100%').padding({ left: 16, right: 16, top: 22, bottom: 24 }).alignItems(VerticalAlign.Center)
      .linearGradient({
        angle: 145,
        colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY, 0.55], [Theme.PRIMARY_DARK, 1.0]]
      }).borderRadius({ bottomLeft: 28, bottomRight: 28 })

      if (this.showComplete) {
        Scroll() {
          this.CompleteForm()
        }.layoutWeight(1).width('100%')
      } else if (this.visits.length === 0) {
        Column() {
          Text('🗓️').fontSize(52).margin({ bottom: 12 })
          Text('暂无上门服务任务').fontSize(15).fontColor(Theme.TEXT_BODY)
          Text('系统会按你的技能自动排班').fontSize(13).fontColor(Theme.TEXT_MUTED).margin({ top: 6 })
        }
        .width('100%').layoutWeight(1).justifyContent(FlexAlign.Center).alignItems(HorizontalAlign.Center)
      } else {
        List() {
          ForEach(this.visits, (item: ServiceVisitItem) => {
            ListItem() { this.VisitCard(item) }
          }, (item: ServiceVisitItem) => `${item.id}-${item.status}`)
        }.layoutWeight(1).width('100%').padding({ left: 16, right: 16, top: 16 }).scrollBar(BarState.Off)
      }
    }
    .width('100%').height('100%').backgroundColor(Theme.BG)
  }
}
