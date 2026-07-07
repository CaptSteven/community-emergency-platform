import router from '@ohos.router'
import promptAction from '@ohos.promptAction'
import { Api, Session } from '../common/Api'
import { MyStats, LeaderboardItem } from '../model/Models'
import { Theme } from '../common/Theme'

@Entry
@Component
struct VolunteerPointsPage {
  @State stats: MyStats | null = null
  @State board: LeaderboardItem[] = []
  @State loading: boolean = false

  onPageShow() {
    this.loadAll()
  }

  aboutToAppear() {
    this.loadAll()
  }

  async loadAll() {
    this.loading = true
    try {
      this.stats = await Api.get('/service-visits/my-stats/') as MyStats
      this.board = await Api.getList<LeaderboardItem>('/analytics/volunteer-leaderboard/')
    } catch (err) {
      promptAction.showToast({ message: '加载失败，请检查网络' })
    } finally {
      this.loading = false
    }
  }

  hoursText(minutes: number): string {
    let h: number = minutes / 60
    return (Math.round(h * 10) / 10).toString()
  }

  medal(rank: number): string {
    if (rank === 1) return '🥇'
    if (rank === 2) return '🥈'
    if (rank === 3) return '🥉'
    return rank.toString()
  }

  // 我的积分统计卡（蓝色渐变 + 徽章）
  @Builder
  StatItem(value: string, unit: string, label: string) {
    Column() {
      Row() {
        Text(value).fontSize(22).fontWeight(FontWeight.Bold).fontColor(Color.White)
        if (unit !== '') {
          Text(unit).fontSize(12).fontColor('#DBEAFE').margin({ left: 2, bottom: 2 })
        }
      }.alignItems(VerticalAlign.Bottom)
      Text(label).fontSize(12).fontColor('#DBEAFE').margin({ top: 4 })
    }.layoutWeight(1).alignItems(HorizontalAlign.Center)
  }

  @Builder
  MyStatsCard() {
    Column() {
      Row() {
        Column() {
          Text('我的积分').fontSize(13).fontColor('#DBEAFE')
          Row() {
            Text(`${this.stats?.points ?? 0}`).fontSize(46).fontWeight(FontWeight.Bold).fontColor(Color.White)
            Text('分').fontSize(16).fontColor('#DBEAFE').margin({ left: 4, bottom: 8 })
          }.alignItems(VerticalAlign.Bottom).margin({ top: 2 })
        }.layoutWeight(1).alignItems(HorizontalAlign.Start)

        Text('🏅 志愿之星')
          .fontSize(12).fontColor(Color.White)
          .padding({ left: 12, right: 12, top: 6, bottom: 6 })
          .backgroundColor('#33FFFFFF').borderRadius(14)
      }.width('100%').alignItems(VerticalAlign.Top)

      Divider().color('#33FFFFFF').margin({ top: 16, bottom: 14 })

      Row() {
        this.StatItem(this.hoursText(this.stats?.week_minutes ?? 0), 'h', '本周时长')
        Divider().vertical(true).height(36).color('#33FFFFFF')
        this.StatItem(this.hoursText(this.stats?.total_minutes ?? 0), 'h', '累计时长')
        Divider().vertical(true).height(36).color('#33FFFFFF')
        this.StatItem(`${this.stats?.completed_count ?? 0}`, '', '完成单数')
      }.width('100%')
    }
    .width('90%').padding(20).margin({ top: 16 }).alignItems(HorizontalAlign.Start)
    .borderRadius(Theme.RADIUS)
    .linearGradient({ angle: 135, colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY, 0.5], [Theme.PRIMARY_DARK, 1.0]] })
    .shadow({ radius: 18, color: '#332563EB', offsetX: 0, offsetY: 6 })
  }

  // 排行榜条目
  @Builder
  BoardRow(item: LeaderboardItem) {
    Row() {
      Text(this.medal(item.rank))
        .fontSize(item.rank <= 3 ? 22 : 16)
        .fontWeight(FontWeight.Bold)
        .fontColor(item.rank <= 3 ? Theme.TEXT : Theme.TEXT_MUTED)
        .width(40).textAlign(TextAlign.Center)

      Column() {
        Text(item.volunteer === Session.username ? `${item.volunteer}（我）` : item.volunteer)
          .fontSize(15).fontWeight(FontWeight.Medium)
          .fontColor(item.volunteer === Session.username ? Theme.PRIMARY : Theme.TEXT)
        Text(`累计 ${this.hoursText(item.total_minutes)} 小时 · 完成 ${item.completed_count} 单`)
          .fontSize(12).fontColor(Theme.TEXT_MUTED).margin({ top: 3 })
      }.layoutWeight(1).alignItems(HorizontalAlign.Start).margin({ left: 8 })

      Row() {
        Text('🏅').fontSize(13)
        Text(`${item.points}`).fontSize(16).fontWeight(FontWeight.Bold).fontColor(Theme.WARN).margin({ left: 4 })
        Text('分').fontSize(12).fontColor(Theme.TEXT_MUTED).margin({ left: 2 })
      }.alignItems(VerticalAlign.Center)
    }
    .width('100%').padding({ left: 12, right: 12, top: 12, bottom: 12 })
    .backgroundColor(item.volunteer === Session.username ? '#EFF6FF' : Theme.CARD)
    .borderRadius(12).margin({ bottom: 8 })
  }

  build() {
    Column() {
      // 头部
      Row() {
        Button('‹ 返回')
          .height(36).fontSize(14).fontColor(Theme.PRIMARY).backgroundColor(Color.White)
          .borderRadius(Theme.RADIUS_SM)
          .onClick(() => { router.back() })
        Column() {
          Text('我的积分').fontSize(20).fontWeight(FontWeight.Bold).fontColor(Color.White)
          Text('服务得积分 · 时长可追溯').fontSize(12).fontColor('#DBEAFE').margin({ top: 4 })
        }.layoutWeight(1).alignItems(HorizontalAlign.Start).margin({ left: 12 })
      }
      .width('100%').padding({ left: 16, right: 16, top: 22, bottom: 24 }).alignItems(VerticalAlign.Center)
      .linearGradient({ angle: 145, colors: [[Theme.PRIMARY_LIGHT, 0.0], [Theme.PRIMARY, 0.55], [Theme.PRIMARY_DARK, 1.0]] })
      .borderRadius({ bottomLeft: 28, bottomRight: 28 })

      Scroll() {
        Column() {
          this.MyStatsCard()

          Row() {
            Column().width(4).height(18).backgroundColor(Theme.WARN).borderRadius(2)
            Text('志愿排行榜').fontSize(Theme.FS_SUBTITLE).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT).margin({ left: 10 })
          }.width('90%').alignItems(VerticalAlign.Center).margin({ top: 22, bottom: 12 })

          if (this.board.length === 0) {
            Column() {
              Text('🏅').fontSize(44)
              Text('还没有排行数据').fontSize(Theme.FS_BODY).fontColor(Theme.TEXT_BODY).margin({ top: 10 })
              Text('完成上门服务即可获得积分与排名').fontSize(Theme.FS_SMALL).fontColor(Theme.TEXT_MUTED).margin({ top: 6 })
            }.width('90%').padding({ top: 30, bottom: 30 }).justifyContent(FlexAlign.Center).alignItems(HorizontalAlign.Center)
          } else {
            Column() {
              ForEach(this.board, (item: LeaderboardItem) => {
                this.BoardRow(item)
              }, (item: LeaderboardItem) => `${item.rank}-${item.volunteer}`)
            }.width('90%')
          }

          Text('积分规则：每完成一次上门服务 +10 分，服务每满 30 分钟额外 +5 分。积分后续可兑换奖励。')
            .fontSize(12).fontColor(Theme.TEXT_MUTED).lineHeight(19)
            .width('90%').margin({ top: 8, bottom: 24 })
        }
        .width('100%').alignItems(HorizontalAlign.Center)
      }.layoutWeight(1).width('100%').scrollBar(BarState.Off)
    }
    .width('100%').height('100%').backgroundColor(Theme.BG)
  }
}
