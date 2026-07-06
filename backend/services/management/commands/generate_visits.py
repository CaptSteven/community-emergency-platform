from datetime import datetime

from django.core.management.base import BaseCommand

from services import scheduler


class Command(BaseCommand):
    help = '为所有到期的社区服务计划生成上门工单并按技能匹配轮流自动派单（可配 cron 每日运行）。'

    def add_arguments(self, parser):
        parser.add_argument('--date', help='指定排班基准日期 YYYY-MM-DD（默认今天）')
        parser.add_argument('--no-notify', action='store_true', help='不发送站内/推送通知')

    def handle(self, *args, **options):
        today = None
        if options.get('date'):
            today = datetime.strptime(options['date'], '%Y-%m-%d').date()
        created = scheduler.generate_due_visits(today=today, notify=not options.get('no_notify'))
        assigned = sum(1 for v in created if v.volunteer_id)
        self.stdout.write(self.style.SUCCESS(
            f'生成 {len(created)} 张工单，已自动派单 {assigned} 张，'
            f'待人工指派 {len(created) - assigned} 张。'
        ))
