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
  @State serviceAddress: string = ''
  @State editingId: number = 0          // 0=新建申请，>0=编辑该服务计划
  @State editingActive: boolean = true

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
    this.editingId = 0
    this.editingActive = true
    this.frequency = 'weekly'
    this.weekday = 0
    this.preferredTime = ''
    this.note = ''
    this.serviceAddress = ''
    if (this.types.length > 0) {
      this.selectedTypeId = this.types[0].id
    }
    this.showSubscribe = true
  }

  // 修改已有服务计划：预填后进入表单
  openEdit(item: ServiceSubscriptionItem) {
    this.editingId = item.id
    this.editingActive = item.is_active
    this.selectedTypeId = item.service_type
    this.frequency = item.frequency
    this.weekday = item.preferred_weekday
    this.preferredTime = item.preferred_time
    this.note = item.note
    this.serviceAddress = item.address
    this.showSubscribe = true
  }

  // 暂停 / 恢复服务计划
  async toggleActive(item: ServiceSubscriptionItem) {
    try {
      await Api.postEmpty(`/service-subscriptions/${item.id}/toggle-active/`)
      promptAction.showToast({ message: item.is_active ? '已暂停该服务' : '已恢复该服务' })
      this.loadAll()
    } catch (err) {
      promptAction.showToast({ message: '操作失败：' + (err as Error).message })
    }
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
      note: this.note,
      address: this.serviceAddress
    }
    try {
      if (this.editingId > 0) {
        payload.is_active = this.editingActive   // 编辑用 PUT，保留生效/暂停状态
        await Api.put<CreateSubscriptionPayload>(`/service-subscriptions/${this.editingId}/`, payload)
        promptAction.showToast({ message: '已保存修改' })
      } else {
        await Api.post<CreateSubscriptionPayload>('/service-subscriptions/', payload)
        promptAction.showToast({ message: '已提交服务申请' })
      }
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
          .fontSize(Theme.FS_SUBTITLE).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT).layoutWeight(1)
        Text(item.is_active ? '生效中' : '已暂停')
          .fontSize(13).fontColor(Color.White)
          .padding({ left: 12, right: 12, top: 4, bottom: 4 })
          .backgroundColor(item.is_active ? Theme.SUCCESS : Theme.TEXT_MUTED).borderRadius(12)
      }.width('100%')
      Row() {
        Text('🗓️').fontSize(14)
        Text(`${item.frequency_display} · ${item.preferred_weekday_display}${item.preferred_time !== '' ? ' ' + item.preferred_time : ''}`)
          .fontSize(Theme.FS_BODY).fontColor(Theme.TEXT_BODY).margin({ left: 6 })
      }.width('100%').margin({ top: 10 })
      if (item.address !== '') {
        Row() {
          Text('📍').fontSize(14)
          Text(item.address).fontSize(Theme.FS_SMALL).fontColor(Theme.TEXT_MUTED).margin({ left: 6 }).layoutWeight(1)
        }.width('100%').margin({ top: 8 })
      }
      Row() {
        Button('修改服务')
          .layoutWeight(1).height(40).fontSize(14).fontColor(Theme.PRIMARY)
          .backgroundColor('#EEF2FF').borderRadius(Theme.RADIUS_SM)
          .onClick(() => { this.openEdit(item) })
        Button(item.is_active ? '暂停' : '恢复')
          .layoutWeight(1).height(40).fontSize(14)
          .fontColor(item.is_active ? Theme.WARN : Theme.SUCCESS)
          .backgroundColor(item.is_active ? '#FFF7ED' : '#F0FDF4').borderRadius(Theme.RADIUS_SM).margin({ left: 10 })
          .onClick(() => { this.toggleActive(item) })
      }.width('100%').margin({ top: 12 })
    }
    .width('100%').padding(16).alignItems(HorizontalAlign.Start)
    .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
    .shadow({ radius: 16, color: '#0F0F172A', offsetX: 0, offsetY: 4 })
    .margin({ bottom: 12 })
  }

  // 单项健康小徽章：标签 + 数值，醒目分隔，老人也看得清
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
          .fontSize(Theme.FS_SUBTITLE).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT).layoutWeight(1)
        Text(item.status_display)
          .fontSize(13).fontColor(Color.White)
          .padding({ left: 12, right: 12, top: 4, bottom: 4 })
          .backgroundColor(Theme.statusColor(item.status)).borderRadius(12)
      }.width('100%')
      Row() {
        Text('📅').fontSize(14)
        Text(item.scheduled_date).fontSize(Theme.FS_SMALL).fontColor(Theme.TEXT_MUTED).margin({ left: 4 }).layoutWeight(1)
        if (item.volunteer_name !== '') {
          Text(`志愿者：${item.volunteer_name}`).fontSize(Theme.FS_SMALL).fontColor(Theme.TEXT_MUTED)
        }
      }.width('100%').margin({ top: 10 })
      if (item.status === 'completed' && item.needs_health_record) {
        // 健康记录：分隔 + 徽章展示，更醒目易读
        Row() {
          Text('❤️').fontSize(14)
          Text('本次健康记录').fontSize(Theme.FS_SMALL).fontWeight(FontWeight.Medium).fontColor(Theme.SUCCESS).margin({ left: 6 })
        }.width('100%').margin({ top: 12, bottom: 6 })
        Row() {
          this.HealthBadge('血压', `${item.systolic ?? '—'}/${item.diastolic ?? '—'}`, 'mmHg')
          Divider().vertical(true).height(28).color(Theme.BORDER)
          this.HealthBadge('心率', `${item.heart_rate ?? '—'}`, '次/分')
          Divider().vertical(true).height(28).color(Theme.BORDER)
          this.HealthBadge('体温', `${item.temperature ?? '—'}`, '℃')
        }
        .width('100%').backgroundColor(Theme.SUCCESS_LIGHT).borderRadius(Theme.RADIUS_SM)
        if (item.health_note !== '') {
          Text(item.health_note).fontSize(Theme.FS_SMALL).fontColor(Theme.TEXT_BODY).margin({ top: 8 })
        }
      }
    }
    .width('100%').padding(16).alignItems(HorizontalAlign.Start)
    .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
    .shadow({ radius: 16, color: '#0F0F172A', offsetX: 0, offsetY: 4 })
    .margin({ bottom: 12 })
  }

  @Builder
  SubscribeForm() {
    Column() {
      Text(this.editingId > 0 ? '修改服务计划' : '申请周期服务').fontSize(18).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT).margin({ bottom: 14 })

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
      TextInput({ placeholder: '如 09:00', text: this.preferredTime }).width('100%').margin({ bottom: 12 })
        .onChange((v: string) => { this.preferredTime = v })

      Text('服务地址（上门位置）').fontSize(14).fontWeight(FontWeight.Medium).fontColor(Theme.PRIMARY).margin({ bottom: 8 })
      TextInput({ placeholder: '如 水磨沟区XX路X号楼X单元；留空取账号地址', text: this.serviceAddress })
        .width('100%').margin({ bottom: 12 })
        .onChange((v: string) => { this.serviceAddress = v })

      Text('备注').fontSize(14).fontWeight(FontWeight.Medium).fontColor(Theme.TEXT).margin({ bottom: 8 })
      TextArea({ placeholder: '补充说明，如老人情况、门禁信息等', text: this.note })
        .height(70).width('100%').margin({ bottom: 16 })
        .onChange((v: string) => { this.note = v })

      Row() {
        Button('取消')
          .layoutWeight(1).height(44).fontSize(15).fontColor(Theme.TEXT_BODY)
          .backgroundColor('#E5E7EB').borderRadius(Theme.RADIUS_SM)
          .onClick(() => { this.showSubscribe = false })
        Button(this.editingId > 0 ? '保存修改' : '提交申请')
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
          .height(36).fontSize(14).fontColor(Theme.PRIMARY).backgroundColor(Color.White)
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
            Row() {
              Column().width(4).height(18).backgroundColor(Theme.SUCCESS).borderRadius(2)
              Text('我的服务计划').fontSize(Theme.FS_SUBTITLE).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT).margin({ left: 10 })
            }.width('100%').alignItems(VerticalAlign.Center).margin({ top: 4, bottom: 12 })
            if (this.subscriptions.length === 0) {
              Column() {
                Text('🗒️').fontSize(40)
                Text('还没有服务计划').fontSize(Theme.FS_BODY).fontColor(Theme.TEXT_BODY).margin({ top: 10 })
                Text('点击右上角「申请服务」预约上门').fontSize(Theme.FS_SMALL).fontColor(Theme.TEXT_MUTED).margin({ top: 6 })
              }
              .width('100%').padding({ top: 24, bottom: 24 })
              .justifyContent(FlexAlign.Center).alignItems(HorizontalAlign.Center)
              .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS).margin({ bottom: 12 })
            } else {
              ForEach(this.subscriptions, (item: ServiceSubscriptionItem) => {
                this.SubscriptionCard(item)
              }, (item: ServiceSubscriptionItem) => `s-${item.id}`)
            }

            Row() {
              Column().width(4).height(18).backgroundColor(Theme.PRIMARY).borderRadius(2)
              Text('上门记录').fontSize(Theme.FS_SUBTITLE).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT).margin({ left: 10 })
            }.width('100%').alignItems(VerticalAlign.Center).margin({ top: 12, bottom: 12 })
            if (this.visits.length === 0) {
              Column() {
                Text('🚪').fontSize(40)
                Text('暂无上门记录').fontSize(Theme.FS_BODY).fontColor(Theme.TEXT_BODY).margin({ top: 10 })
                Text('志愿者上门服务后会显示在这里').fontSize(Theme.FS_SMALL).fontColor(Theme.TEXT_MUTED).margin({ top: 6 })
              }
              .width('100%').padding({ top: 24, bottom: 24 })
              .justifyContent(FlexAlign.Center).alignItems(HorizontalAlign.Center)
              .backgroundColor(Theme.CARD).borderRadius(Theme.RADIUS)
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
