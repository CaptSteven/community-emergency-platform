import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { Api, Session } from '../common/Api'
import { ServiceTypeItem, ServiceSubscriptionItem, ServiceVisitItem, CreateSubscriptionPayload } from '../model/Models'
import { Theme } from '../common/Theme'

@Entry
@Component
struct ResidentServicePage {
  @State subscriptions: ServiceSubscriptionItem[] = []
  @State visits: ServiceVisitItem[] = []
  @State types: ServiceTypeItem[] = []
  @State loading: boolean = false
  // 申请周期服务表单
  @State showSubscribe: boolean = false
  @State selectedTypeId: number = 0
  @State frequency: string = 'weekly'
  @State weekday: number = 0
  @State preferredTime: string = ''
  @State note: string = ''

  private weekdayLabels: string[] = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
  private freqKeys: string[] = ['weekly', 'biweekly', 'monthly']
  private freqLabels: string[] = ['每周', '每两周', '每月']

  onPageShow() {
    this.loadAll()
  }

  aboutToAppear() {
    this.loadAll()
    this.loadTypes()
  }

  async loadAll() {
    this.loading = true
    try {
      this.subscriptions = await Api.getList<ServiceSubscriptionItem>('/service-subscriptions/')
      this.visits = await Api.getList<ServiceVisitItem>('/service-visits/')
    } catch (err) {
      promptAction.showToast({ message: '加载失败，请检查后端服务' })
    } finally {
      this.loading = false
    }
  }

  async loadTypes() {
    try {
      this.types = await Api.getList<ServiceTypeItem>('/service-types/')
      if (this.types.length > 0) {
        this.selectedTypeId = this.types[0].id
      }
    } catch (err) {
      // 静默
    }
  }

  openSubscribe() {
    this.frequency = 'weekly'
    this.weekday = 0
    this.preferredTime = ''
    this.note = ''
    if (this.types.length > 0) {
      this.selectedTypeId = this.types[0].id
    }
    this.showSubscribe = true
  }

  async submitSubscribe() {
    if (this.selectedTypeId === 0) {
      promptAction.showToast({ message: '请选择服务类型' })
      return
    }
    let payload: CreateSubscriptionPayload = {
      service_type: this.selectedTypeId,
      frequency: this.frequency,
      preferred_weekday: this.weekday,
      preferred_time: this.preferredTime,
      note: this.note
    }
    try {
      await Api.post<CreateSubscriptionPayload>('/service-subscriptions/', payload)
      promptAction.showToast({ message: '已提交服务申请' })
      this.showSubscribe = false
      this.loadAll()
    } catch (err) {
      promptAction.showToast({ message: '提交失败：' + (err as Error).message })
    }
  }

  @Builder
  SubscriptionCard(item: ServiceSubscriptionItem) {
    Column() {
      Row() {
        Text(`${item.service_type_icon} ${item.service_type_name}`)
          .fontSize(16).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT).layoutWeight(1)
        Text(item.is_active ? '生效中' : '已暂停')
          .fontSize(12).fontColor(Color.White)
          .padding({ left: 10, right: 10, top: 3, bottom: 3 })
          .backgroundColor(item.is_active ? Theme.SUCCESS : '#9CA3AF').borderRadius(12)
      }.width('100%')
      Text(`${item.frequency_display} · ${item.preferred_weekday_display}${item.preferred_time !== '' ? ' ' + item.preferred_time : ''}`)
        .fontSize(13).fontColor(Theme.TEXT_BODY).margin({ top: 8 })
    }
    .width('100%').padding(14).alignItems(HorizontalAlign.Start)
    .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
    .shadow({ radius: 12, color: '#12000000', offsetX: 0, offsetY: 3 })
    .margin({ bottom: 10 })
  }

  @Builder
  VisitCard(item: ServiceVisitItem) {
    Column() {
      Row() {
        Text(`${item.service_type_icon} ${item.service_type_name}`)
          .fontSize(15).fontWeight(FontWeight.Medium).fontColor(Theme.TEXT).layoutWeight(1)
        Text(item.status_display)
          .fontSize(12).fontColor(Color.White)
          .padding({ left: 10, right: 10, top: 3, bottom: 3 })
          .backgroundColor(Theme.statusColor(item.status)).borderRadius(12)
      }.width('100%')
      Row() {
        Text('📅').fontSize(12)
        Text(item.scheduled_date).fontSize(12).fontColor(Theme.TEXT_MUTED).margin({ left: 4 }).layoutWeight(1)
        if (item.volunteer_name !== '') {
          Text(`志愿者：${item.volunteer_name}`).fontSize(12).fontColor(Theme.TEXT_MUTED)
        }
      }.width('100%').margin({ top: 8 })
      if (item.status === 'completed' && item.needs_health_record) {
        Text(`血压 ${item.systolic ?? '—'}/${item.diastolic ?? '—'} · 心率 ${item.heart_rate ?? '—'} · 体温 ${item.temperature ?? '—'}℃`)
          .fontSize(12).fontColor(Theme.SUCCESS).margin({ top: 8 })
        if (item.health_note !== '') {
          Text(item.health_note).fontSize(12).fontColor(Theme.TEXT_MUTED).margin({ top: 4 })
        }
      }
    }
    .width('100%').padding(14).alignItems(HorizontalAlign.Start)
    .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
    .shadow({ radius: 12, color: '#12000000', offsetX: 0, offsetY: 3 })
    .margin({ bottom: 10 })
  }

  @Builder
  SubscribeForm() {
    Column() {
      Text('申请周期服务').fontSize(18).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT).margin({ bottom: 14 })

      Text('服务类型').fontSize(14).fontWeight(FontWeight.Medium).fontColor(Theme.PRIMARY).margin({ bottom: 8 })
      Flex({ wrap: FlexWrap.Wrap }) {
        ForEach(this.types, (t: ServiceTypeItem) => {
          Text(`${t.icon} ${t.name}`)
            .fontSize(13).fontColor(this.selectedTypeId === t.id ? Color.White : Theme.TEXT_BODY)
            .padding({ left: 12, right: 12, top: 7, bottom: 7 }).margin({ right: 8, bottom: 8 })
            .backgroundColor(this.selectedTypeId === t.id ? Theme.PRIMARY : '#EEF2FF').borderRadius(16)
            .onClick(() => { this.selectedTypeId = t.id })
        }, (t: ServiceTypeItem) => `${t.id}`)
      }.width('100%').margin({ bottom: 6 })

      Text('服务周期').fontSize(14).fontWeight(FontWeight.Medium).fontColor(Theme.PRIMARY).margin({ top: 8, bottom: 8 })
      Row() {
        ForEach(this.freqKeys, (k: string, i: number) => {
          Text(this.freqLabels[i])
            .fontSize(13).fontColor(this.frequency === k ? Color.White : Theme.TEXT_BODY)
            .padding({ left: 14, right: 14, top: 7, bottom: 7 }).margin({ right: 8 })
            .backgroundColor(this.frequency === k ? Theme.PRIMARY : '#EEF2FF').borderRadius(16)
            .onClick(() => { this.frequency = k })
        }, (k: string) => k)
      }.width('100%')

      Text('首选星期').fontSize(14).fontWeight(FontWeight.Medium).fontColor(Theme.PRIMARY).margin({ top: 14, bottom: 8 })
      Flex({ wrap: FlexWrap.Wrap }) {
        ForEach(this.weekdayLabels, (w: string, i: number) => {
          Text(w)
            .fontSize(13).fontColor(this.weekday === i ? Color.White : Theme.TEXT_BODY)
            .padding({ left: 12, right: 12, top: 6, bottom: 6 }).margin({ right: 8, bottom: 8 })
            .backgroundColor(this.weekday === i ? Theme.PRIMARY : '#EEF2FF').borderRadius(16)
            .onClick(() => { this.weekday = i })
        }, (w: string) => w)
      }.width('100%')

      Text('首选时段').fontSize(14).fontWeight(FontWeight.Medium).fontColor(Theme.PRIMARY).margin({ top: 8, bottom: 8 })
      TextInput({ placeholder: '如 09:00' }).width('100%').margin({ bottom: 12 })
        .onChange((v: string) => { this.preferredTime = v })

      Text('备注').fontSize(14).fontWeight(FontWeight.Medium).fontColor(Theme.TEXT).margin({ bottom: 8 })
      TextArea({ placeholder: '补充说明，如老人情况、门禁信息等' })
        .height(70).width('100%').margin({ bottom: 16 })
        .onChange((v: string) => { this.note = v })

      Row() {
        Button('取消')
          .layoutWeight(1).height(44).fontSize(15).fontColor(Theme.TEXT_BODY)
          .backgroundColor('#E5E7EB').borderRadius(Theme.RADIUS_SM)
          .onClick(() => { this.showSubscribe = false })
        Button('提交申请')
          .layoutWeight(1).height(44).fontSize(15).fontColor(Color.White)
          .backgroundColor(Theme.PRIMARY).borderRadius(Theme.RADIUS_SM).margin({ left: 12 })
          .onClick(() => { this.submitSubscribe() })
      }.width('100%')
    }
    .width('90%').padding(18).margin({ top: 16, bottom: 16 }).alignItems(HorizontalAlign.Start)
    .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
    .shadow({ radius: 16, color: '#14000000', offsetX: 0, offsetY: 4 })
  }

  build() {
    Column() {
      Row() {
        Button('‹ 返回')
          .height(36).fontSize(14).fontColor(Color.White).backgroundColor('#ffffff33')
          .borderRadius(Theme.RADIUS_SM)
          .onClick(() => { router.back() })
        Column() {
          Text('我的社区服务').fontSize(20).fontWeight(FontWeight.Bold).fontColor(Color.White)
          Text(`${Session.username} · ${Session.community || '社区居民'}`).fontSize(12).fontColor('#DBEAFE').margin({ top: 4 })
        }.layoutWeight(1).alignItems(HorizontalAlign.Start).margin({ left: 12 })

        Button('申请服务')
          .height(36).fontSize(13).fontColor(Theme.PRIMARY).backgroundColor(Color.White)
          .borderRadius(Theme.RADIUS_SM)
          .onClick(() => { this.openSubscribe() })
      }
      .width('100%').padding({ left: 16, right: 16, top: 22, bottom: 24 }).alignItems(VerticalAlign.Center)
      .linearGradient({
        angle: 145,
        colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY, 0.55], [Theme.PRIMARY_DARK, 1.0]]
      }).borderRadius({ bottomLeft: 28, bottomRight: 28 })

      if (this.showSubscribe) {
        Scroll() {
          this.SubscribeForm()
        }.layoutWeight(1).width('100%')
      } else {
        Scroll() {
          Column() {
            Text('我的服务计划').fontSize(16).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT)
              .width('100%').margin({ top: 4, bottom: 10 })
            if (this.subscriptions.length === 0) {
              Text('还没有服务计划，点击右上角「申请服务」').fontSize(13).fontColor(Theme.TEXT_MUTED)
                .width('100%').margin({ bottom: 12 })
            } else {
              ForEach(this.subscriptions, (item: ServiceSubscriptionItem) => {
                this.SubscriptionCard(item)
              }, (item: ServiceSubscriptionItem) => `s-${item.id}`)
            }

            Text('上门记录').fontSize(16).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT)
              .width('100%').margin({ top: 12, bottom: 10 })
            if (this.visits.length === 0) {
              Text('暂无上门记录').fontSize(13).fontColor(Theme.TEXT_MUTED).width('100%')
            } else {
              ForEach(this.visits, (item: ServiceVisitItem) => {
                this.VisitCard(item)
              }, (item: ServiceVisitItem) => `v-${item.id}-${item.status}`)
            }
          }
          .width('90%').margin({ top: 16, bottom: 20 }).alignItems(HorizontalAlign.Start)
        }.layoutWeight(1).width('100%')
      }
    }
    .width('100%').height('100%').backgroundColor(Theme.BG)
  }
}
