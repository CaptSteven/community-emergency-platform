import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import picker from '@ohos.file.picker'
import fs from '@ohos.file.fs'
import { common } from '@kit.AbilityKit'
import { BusinessError } from '@ohos.base'
import { Api } from '../common/Api'
import { VolunteerApplyPayload } from '../model/Models'
import { Theme } from '../common/Theme'

interface Slot {
  key: string
  label: string
}

@Entry
@Component
struct VolunteerApplyPage {
  @State username: string = ''
  @State password: string = ''
  @State phone: string = ''
  @State community: string = ''
  @State skills: string = ''
  @State note: string = ''
  @State pickedFlags: boolean[] = [false, false, false, false, false]
  @State submitting: boolean = false
  private paths: string[] = ['', '', '', '', '']
  private slots: Slot[] = [
    { key: 'id_card_front', label: '身份证正面' },
    { key: 'id_card_back', label: '身份证反面' },
    { key: 'skill_cert', label: '技能/资格证' },
    { key: 'health_cert', label: '健康证' },
    { key: 'profile_photo', label: '个人形象照' }
  ]

  // 选择一张图片并拷贝到应用缓存，供提交后按槽位上传
  async pickImage(index: number) {
    try {
      let photoPicker = new picker.PhotoViewPicker()
      let res = await photoPicker.select({ MIMEType: picker.PhotoViewMIMETypes.IMAGE_TYPE, maxSelectNumber: 1 })
      if (res.photoUris && res.photoUris.length > 0) {
        let uri: string = res.photoUris[0]
        let ctx = getContext(this) as common.UIAbilityContext
        let name: string = 'apply_' + index + '.jpg'
        let dest: string = ctx.cacheDir + '/' + name
        let src = fs.openSync(uri, fs.OpenMode.READ_ONLY)
        let dst = fs.openSync(dest, fs.OpenMode.READ_WRITE | fs.OpenMode.CREATE)
        fs.copyFileSync(src.fd, dst.fd)
        fs.closeSync(src)
        fs.closeSync(dst)
        this.paths[index] = 'internal://cache/' + name
        let flags: boolean[] = this.pickedFlags.slice()
        flags[index] = true
        this.pickedFlags = flags
      }
    } catch (err) {
      let e = err as BusinessError
      promptAction.showToast({ message: '选择图片失败：' + (e.message ? e.message : '') })
    }
  }

  async submit() {
    if (this.username.trim() === '' || this.password.length < 6) {
      promptAction.showToast({ message: '请填写用户名和至少 6 位密码' })
      return
    }
    if (this.skills.trim() === '') {
      promptAction.showToast({ message: '请填写擅长技能' })
      return
    }
    this.submitting = true
    try {
      let payload: VolunteerApplyPayload = {
        username: this.username.trim(), password: this.password,
        phone: this.phone, community: this.community, address: '',
        skills: this.skills, note: this.note
      }
      let resp = await Api.post<VolunteerApplyPayload>('/volunteer-applications/', payload) as Record<string, Object>
      let appId: number = resp['application_id'] as number
      // 逐张上传已选证件图（未选则跳过，后端允许无图申请）
      let i: number = 0
      while (i < this.slots.length) {
        if (this.pickedFlags[i]) {
          await Api.uploadFile(`/volunteer-applications/${appId}/upload-image/`, this.paths[i], this.slots[i].key)
        }
        i++
      }
      promptAction.showToast({ message: '申请已提交，等待管理员审核', duration: 3000 })
      router.back()
    } catch (err) {
      promptAction.showToast({ message: '提交失败：' + (err as Error).message })
    } finally {
      this.submitting = false
    }
  }

  @Builder
  FieldLabel(text: string) {
    Text(text).fontSize(14).fontWeight(FontWeight.Medium).fontColor(Theme.TEXT).margin({ top: 12, bottom: 6 }).width('100%')
  }

  build() {
    Column() {
      Row() {
        Button('‹ 返回')
          .height(36).fontSize(14).fontColor(Theme.PRIMARY).backgroundColor(Color.White)
          .borderRadius(Theme.RADIUS_SM).onClick(() => { router.back() })
        Column() {
          Text('申请成为志愿者').fontSize(20).fontWeight(FontWeight.Bold).fontColor(Color.White)
          Text('填资料 + 传证件 · 审核面试通过后开通').fontSize(12).fontColor('#DBEAFE').margin({ top: 4 })
        }.layoutWeight(1).alignItems(HorizontalAlign.Start).margin({ left: 12 })
      }
      .width('100%').padding({ left: 16, right: 16, top: 22, bottom: 24 }).alignItems(VerticalAlign.Center)
      .linearGradient({ angle: 145, colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY, 0.55], [Theme.PRIMARY_DARK, 1.0]] })
      .borderRadius({ bottomLeft: 28, bottomRight: 28 })

      Scroll() {
        Column() {
          this.FieldLabel('登录用户名')
          TextInput({ placeholder: '审核通过后用它登录', text: this.username }).width('100%')
            .onChange((v: string) => { this.username = v })
          this.FieldLabel('登录密码')
          TextInput({ placeholder: '至少 6 位', text: this.password }).type(InputType.Password).width('100%')
            .onChange((v: string) => { this.password = v })
          this.FieldLabel('手机号')
          TextInput({ placeholder: '联系电话', text: this.phone }).type(InputType.Number).width('100%')
            .onChange((v: string) => { this.phone = v })
          this.FieldLabel('所属社区')
          TextInput({ placeholder: '如 乌鲁木齐水磨沟社区', text: this.community }).width('100%')
            .onChange((v: string) => { this.community = v })
          this.FieldLabel('擅长技能')
          TextInput({ placeholder: '如 医疗 护理 维修 家政（空格分隔）', text: this.skills }).width('100%')
            .onChange((v: string) => { this.skills = v })
          this.FieldLabel('自我介绍')
          TextArea({ placeholder: '简述经历、可服务时间等', text: this.note }).height(70).width('100%')
            .onChange((v: string) => { this.note = v })

          Text('上传证件材料（选填，管理员将下载核验）')
            .fontSize(14).fontWeight(FontWeight.Medium).fontColor(Theme.PRIMARY).margin({ top: 16, bottom: 4 }).width('100%')
          ForEach(this.slots, (s: Slot, i: number) => {
            Row() {
              Text(s.label).fontSize(14).fontColor(Theme.TEXT).layoutWeight(1)
              Button(this.pickedFlags[i] ? '✓ 已选' : '选择图片')
                .height(36).fontSize(13)
                .fontColor(this.pickedFlags[i] ? Theme.SUCCESS : Theme.PRIMARY)
                .backgroundColor(this.pickedFlags[i] ? '#F0FDF4' : '#EEF2FF')
                .borderRadius(Theme.RADIUS_SM)
                .onClick(() => { this.pickImage(i) })
            }.width('100%').padding({ top: 8, bottom: 8 })
          }, (s: Slot) => s.key)

          Button(this.submitting ? '提交中...' : '提交申请')
            .width('100%').height(46).fontSize(16).fontWeight(FontWeight.Medium).fontColor(Color.White)
            .backgroundColor(Theme.PRIMARY).borderRadius(Theme.RADIUS_SM).enabled(!this.submitting)
            .margin({ top: 18, bottom: 24 })
            .onClick(() => { this.submit() })
        }
        .width('90%').margin({ top: 12 }).alignItems(HorizontalAlign.Start)
      }.layoutWeight(1).width('100%').scrollBar(BarState.Off)
    }
    .width('100%').height('100%').backgroundColor(Theme.BG)
  }
}
