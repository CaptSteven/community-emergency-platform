import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { Api, Session } from '../common/Api'
import { CompleteTaskPayload, TaskItem } from '../model/Models'

@Entry
@Component
struct VolunteerHomePage {
  @State tasks: TaskItem[] = []
  @State loading: boolean = false
  @State feedback: string = '已完成现场协助处理'

  aboutToAppear() {
    this.loadTasks()
  }

  async loadTasks() {
    this.loading = true

    try {
      this.tasks = await Api.get('/tasks/') as TaskItem[]
    } catch (err) {
      promptAction.showToast({ message: '任务加载失败，请检查后端服务' })
    } finally {
      this.loading = false
    }
  }

  async acceptTask(id: number) {
    try {
      await Api.postEmpty(`/tasks/${id}/accept/`)
      promptAction.showToast({ message: '接单成功' })
      this.loadTasks()
    } catch (err) {
      promptAction.showToast({ message: '接单失败' })
    }
  }

  async completeTask(id: number) {
    try {
      let payload: CompleteTaskPayload = {
        feedback: this.feedback
      }

      await Api.post<CompleteTaskPayload>(`/tasks/${id}/complete/`, payload)
      promptAction.showToast({ message: '任务已完成' })
      this.loadTasks()
    } catch (err) {
      promptAction.showToast({ message: '完成任务失败' })
    }
  }

  statusColor(status: string): string {
    if (status === 'completed') return '#16A34A'
    if (status === 'assigned') return '#D97706'
    if (status === 'processing' || status === 'accepted') return '#2563EB'
    return '#64748B'
  }

  build() {
    Column() {
      Row() {
        Column() {
          Text(`志愿者端 · ${Session.username}`)
            .fontSize(22)
            .fontWeight(FontWeight.Bold)
            .fontColor(Color.White)

          Text('接收任务、处理求助、反馈结果')
            .fontSize(13)
            .fontColor('#DBEAFE')
            .margin({ top: 6 })
        }
        .layoutWeight(1)

        Button('消息')
          .height(36)
          .backgroundColor('#0F766E')
          .onClick(() => {
            router.pushUrl({ url: 'pages/NotificationsPage' })
          })
      }
      .width('100%')
      .padding(18)
      .backgroundColor('#2563EB')

      Column() {
        TextInput({ placeholder: '完成任务时的反馈内容', text: this.feedback })
          .height(44)
          .backgroundColor(Color.White)
          .borderRadius(10)
          .padding({ left: 12, right: 12 })
          .onChange((value: string) => {
            this.feedback = value
          })

        Button('刷新任务')
          .width('100%')
          .height(42)
          .backgroundColor('#2563EB')
          .margin({ top: 10 })
          .onClick(() => {
            this.loadTasks()
          })
      }
      .width('100%')
      .padding(16)

      List() {
        ForEach(this.tasks, (item: TaskItem) => {
          ListItem() {
            Column() {
              Row() {
                Text(`任务 #${item.id}`)
                  .fontSize(18)
                  .fontWeight(FontWeight.Bold)
                  .layoutWeight(1)

                Text(item.status_display)
                  .fontSize(12)
                  .fontColor(Color.White)
                  .padding({ left: 8, right: 8, top: 4, bottom: 4 })
                  .backgroundColor(this.statusColor(item.status))
                  .borderRadius(12)
              }

              Text(item.help_request_type || '居民求助')
                .fontSize(14)
                .fontColor('#2563EB')
                .margin({ top: 10 })

              Text(item.help_request_description)
                .fontSize(14)
                .fontColor('#475569')
                .margin({ top: 8 })

              Text(`地址：${item.help_request_address || '-'}`)
                .fontSize(12)
                .fontColor('#64748B')
                .margin({ top: 8 })

              if (item.feedback) {
                Text(`反馈：${item.feedback}`)
                  .fontSize(12)
                  .fontColor('#16A34A')
                  .margin({ top: 8 })
              }

              Row() {
                if (item.status === 'assigned') {
                  Button('接单')
                    .layoutWeight(1)
                    .height(40)
                    .backgroundColor('#2563EB')
                    .onClick(() => {
                      this.acceptTask(item.id)
                    })
                }

                if (item.status === 'processing' || item.status === 'accepted') {
                  Button('完成任务')
                    .layoutWeight(1)
                    .height(40)
                    .backgroundColor('#16A34A')
                    .onClick(() => {
                      this.completeTask(item.id)
                    })
                }

                if (item.status === 'completed') {
                  Text('该任务已完成')
                    .fontSize(14)
                    .fontColor('#16A34A')
                }
              }
              .width('100%')
              .margin({ top: 14 })
            }
            .width('100%')
            .padding(14)
            .backgroundColor(Color.White)
            .borderRadius(14)
            .margin({ left: 16, right: 16, bottom: 12 })
          }
        }, (item: TaskItem) => item.id.toString())
      }
      .layoutWeight(1)
      .width('100%')
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F1F5F9')
  }
}