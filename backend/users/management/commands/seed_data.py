from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.authtoken.models import Token

from users.models import UserProfile, VolunteerApplication
from alerts.models import Warning
from resources.models import Shelter, Material
from services.models import ServiceType, ServiceSubscription, ServiceVisit
from services import scheduler

# 演示社区：乌鲁木齐水磨沟社区（水磨沟区中心约 87.6417, 43.8256）
COMMUNITY = '乌鲁木齐水磨沟社区'
BASE_LNG = 87.6417
BASE_LAT = 43.8256


class Command(BaseCommand):
    help = '初始化演示数据（社区长期服务平台）。--reset 先清空全部演示账号与业务数据（保留超管）。'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='先删除全部通知/工单/计划/申请与非超管账号，再重建演示数据')

    def wipe(self):
        """清空演示数据：业务表全清，账号只保留超级管理员。"""
        from notifications.models import Notification, DeviceToken
        from tasks.models import TaskCancellation, VolunteerTask
        from requests_app.models import HelpRequest

        Notification.objects.all().delete()
        DeviceToken.objects.all().delete()
        TaskCancellation.objects.all().delete()
        VolunteerTask.objects.all().delete()
        HelpRequest.objects.all().delete()
        ServiceVisit.objects.all().delete()
        ServiceSubscription.objects.all().delete()
        VolunteerApplication.objects.all().delete()
        removed, _ = User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.WARNING(f'已清空演示数据（删除非超管账号及关联记录 {removed} 条）'))

    def create_user(self, username, password, role, phone='', community=COMMUNITY, address='', longitude=None, latitude=None, skills=''):
        user, created = User.objects.get_or_create(username=username)

        # 演示账号每次初始化都重置为固定密码，避免数据库中已存在旧账号时
        # 出现页面提示 123456、但实际密码不是 123456，导致 /api/auth/login/ 返回 400。
        user.set_password(password)
        user.is_active = True
        user.save()

        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'role': role,
                'phone': phone,
                'community': community,
                'address': address,
                'skills': skills,
                'current_longitude': longitude,
                'current_latitude': latitude,
                'is_available': True,
            }
        )

        profile.role = role
        profile.phone = phone
        profile.community = community
        profile.address = address
        profile.skills = skills
        if longitude is not None:
            profile.current_longitude = longitude
        if latitude is not None:
            profile.current_latitude = latitude
        if longitude is not None and latitude is not None:
            profile.location_updated_at = timezone.now()
        profile.save()

        Token.objects.get_or_create(user=user)
        return user

    def handle(self, *args, **options):
        if options.get('reset'):
            self.wipe()

        self.create_user('admin02', '123456', 'admin', '13800000001')

        # 鸿蒙端登录页默认展示 resident1 / volunteer1，因此后端初始化也创建同名账号。
        # 居民按“长期服务受益人”（如独居老人）设定。
        resident1 = self.create_user('resident1', '123456', 'resident', '13800000002',
                                     address='水磨沟区新兴街1号楼', longitude=BASE_LNG + 0.002, latitude=BASE_LAT + 0.001)
        resident02 = self.create_user('resident02', '123456', 'resident', '13800000012',
                                      address='水磨沟区南湖南路5号楼', longitude=BASE_LNG - 0.003, latitude=BASE_LAT + 0.002)
        resident03 = self.create_user('resident03', '123456', 'resident', '13800000014',
                                      address='水磨沟区七道湾路12号楼', longitude=BASE_LNG + 0.004, latitude=BASE_LAT - 0.0015)

        # 志愿者：技能决定可承接的服务类型（自动排班按技能关键字匹配）。
        self.create_user('volunteer1', '123456', 'volunteer', '13800000003',
                         longitude=BASE_LNG + 0.001, latitude=BASE_LAT + 0.0015, skills='医疗 护理 老人 急救')
        self.create_user('volunteer02', '123456', 'volunteer', '13800000013',
                         longitude=BASE_LNG + 0.004, latitude=BASE_LAT - 0.001, skills='医疗 护理 健康')
        self.create_user('volunteer03', '123456', 'volunteer', '13800000004',
                         longitude=BASE_LNG - 0.002, latitude=BASE_LAT + 0.003, skills='家政 保洁 代购')
        self.create_user('volunteer04', '123456', 'volunteer', '13800000005',
                         longitude=BASE_LNG - 0.004, latitude=BASE_LAT - 0.002, skills='陪诊 助浴 护理')
        self.create_user('volunteer05', '123456', 'volunteer', '13800000006',
                         longitude=BASE_LNG + 0.003, latitude=BASE_LAT + 0.004, skills='代购 跑腿 家政')
        # 覆盖新增服务类别所需技能（维修/搬运/康复/理发/送餐），保证演示可自动派单
        self.create_user('volunteer06', '123456', 'volunteer', '13800000007',
                         longitude=BASE_LNG + 0.005, latitude=BASE_LAT + 0.0005, skills='维修 搬运 家政')
        self.create_user('volunteer07', '123456', 'volunteer', '13800000008',
                         longitude=BASE_LNG - 0.005, latitude=BASE_LAT + 0.0025, skills='康复 护理 理疗')
        self.create_user('volunteer08', '123456', 'volunteer', '13800000009',
                         longitude=BASE_LNG + 0.0015, latitude=BASE_LAT - 0.003, skills='理发 送餐 家政')

        # 测试志愿者：全技能、已认证、位于水磨沟区（距 resident1 约 20 米），任何服务类型都能派给他，
        # 供联调/演示直接登录（tester / 123456）。报到想走「正常报到」路径时，
        # 把模拟器虚拟定位设为 (43.8268, 87.6439) 即可。
        self.create_user('tester', '123456', 'volunteer', '13800000010',
                         address='水磨沟区新兴街2号楼',
                         longitude=BASE_LNG + 0.0022, latitude=BASE_LAT + 0.0012,
                         skills='医疗 护理 老人 急救 陪诊 助浴 健康 家政 保洁 代购 跑腿 维修 搬运 康复 理疗 理发 送餐')

        # === 社区服务目录 ===
        service_types = [
            # —— 原有 5 类 ——
            dict(code='health_check', name='老人健康检查', category='医疗健康', required_skill='医疗',
                 default_frequency='weekly', service_mode='recurring', needs_health_record=True, icon='🩺',
                 description='为独居/高龄老人每周上门测量血压、心率、体温并记录健康档案。'),
            dict(code='home_bath', name='助浴服务', category='生活照护', required_skill='助浴',
                 default_frequency='weekly', service_mode='recurring', icon='🛁',
                 description='协助行动不便老人安全洗浴。'),
            dict(code='grocery', name='代购跑腿', category='生活便民', required_skill='代购',
                 default_frequency='weekly', service_mode='both', icon='🛒',
                 description='为老人代购米面粮油、药品等日常物资。'),
            dict(code='escort', name='陪同就医', category='医疗健康', required_skill='陪诊',
                 default_frequency='monthly', service_mode='both', icon='🏥',
                 description='陪同老人到医院挂号、就诊、取药。'),
            dict(code='cleaning', name='居家保洁', category='生活照护', required_skill='保洁',
                 default_frequency='biweekly', service_mode='both', icon='🧹',
                 description='为老人家庭提供居室清扫整理。'),
            # —— 新增 · 周期性 7 类 ——
            dict(code='meal_delivery', name='每日送餐', category='生活照护', required_skill='送餐',
                 default_frequency='daily', service_mode='recurring', icon='🍱',
                 description='为独居/高龄老人每日配送营养餐，可记录饮食情况。'),
            dict(code='rehab', name='康复理疗按摩', category='医疗健康', required_skill='康复',
                 default_frequency='weekly', service_mode='recurring', icon='💆',
                 description='为术后、慢病、行动不便老人定期上门做康复训练、推拿、艾灸。'),
            dict(code='medication', name='用药提醒送药', category='医疗健康', required_skill='医疗',
                 default_frequency='weekly', service_mode='recurring', icon='💊',
                 description='按周期提醒并协助老人按时服药，代取代送常用药。'),
            dict(code='companionship', name='精神慰藉陪伴', category='精神关怀', required_skill='护理',
                 default_frequency='weekly', service_mode='recurring', icon='💬',
                 description='定期上门陪伴聊天、读报，缓解独居老人孤独，做心理关怀。'),
            dict(code='walk_assist', name='助行散步陪同', category='生活照护', required_skill='护理',
                 default_frequency='weekly', service_mode='recurring', icon='🚶',
                 description='定期陪同老人室外散步、晒太阳、做轻度活动，保障安全。'),
            dict(code='haircut', name='上门理发', category='生活照护', required_skill='理发',
                 default_frequency='monthly', service_mode='recurring', icon='💈',
                 description='每月上门为行动不便老人理发、修面。'),
            dict(code='laundry', name='衣物换洗代收', category='生活便民', required_skill='家政',
                 default_frequency='weekly', service_mode='recurring', icon='👕',
                 description='定期收换床品衣物、代收送干洗。'),
            # —— 新增 · 单次 6 类 ——
            dict(code='repair', name='水电家电维修', category='居家维修', required_skill='维修',
                 default_frequency='weekly', service_mode='single', icon='🔧',
                 description='临时报修：水管、电路、灯具、家电等上门维修。'),
            dict(code='moving', name='搬运家具组装', category='居家维修', required_skill='搬运',
                 default_frequency='weekly', service_mode='single', icon='📦',
                 description='临时搬重物、家具组装、上下楼搬运帮扶。'),
            dict(code='errand', name='代办跑腿', category='生活便民', required_skill='跑腿',
                 default_frequency='weekly', service_mode='single', icon='🏃',
                 description='一次性代缴费、代取快递/证件、代排队办事。'),
            dict(code='escort_affairs', name='陪同办事', category='便民关怀', required_skill='陪诊',
                 default_frequency='weekly', service_mode='single', icon='🧾',
                 description='一次性陪同去银行、政务大厅、医院办理事务。'),
            dict(code='digital_help', name='智能手机数码帮助', category='便民关怀', required_skill='',
                 default_frequency='weekly', service_mode='single', icon='📱',
                 description='上门教用智能手机、连网、装App、防诈骗设置。'),
            dict(code='snow', name='冬季扫雪防滑助行', category='便民关怀', required_skill='',
                 default_frequency='weekly', service_mode='single', icon='❄️',
                 description='乌鲁木齐冬季：门前扫雪、结冰路面陪扶出行。'),
        ]
        type_objs = {}
        for st in service_types:
            obj, _ = ServiceType.objects.get_or_create(code=st['code'], defaults=st)
            # 保持演示目录随代码更新
            for k, v in st.items():
                setattr(obj, k, v)
            obj.is_active = True
            obj.save()
            type_objs[st['code']] = obj

        # === 服务计划（为老人建立周期性服务；preferred_slot=标准整点时段）===
        plans = [
            (resident1, 'health_check', 'weekly', 0, 9),
            (resident1, 'grocery', 'weekly', 2, 10),
            (resident02, 'health_check', 'weekly', 1, 14),
            (resident02, 'cleaning', 'biweekly', 4, 15),
        ]
        for res, code, freq, weekday, slot in plans:
            rp = getattr(res, 'profile', None)
            sub, _created = ServiceSubscription.objects.get_or_create(
                resident=res, service_type=type_objs[code],
                defaults=dict(
                    frequency=freq, preferred_weekday=weekday, preferred_slot=slot, is_active=True,
                    start_date=timezone.now().date(),
                    address=(rp.address if rp else ''),
                    longitude=(rp.current_longitude if rp else None),
                    latitude=(rp.current_latitude if rp else None),
                )
            )
            # 老库已有的计划补上标准时段
            if sub.preferred_slot is None:
                sub.preferred_slot = slot
                sub.save(update_fields=['preferred_slot'])

        # === 演示工单：铺设完整状态样本（时间相对今天，坐标全部位于水磨沟社区）===
        # 各状态：待派单(未落实)×3 / 已排班待报到×2 / 已报到×1 / 服务中×1 / 待居民确认×1 / 已完成×2 / 已错过×1
        vol_tester = User.objects.get(username='tester')
        vol1 = User.objects.get(username='volunteer1')
        vol3 = User.objects.get(username='volunteer03')
        vol4 = User.objects.get(username='volunteer04')
        vol5 = User.objects.get(username='volunteer05')
        vol8 = User.objects.get(username='volunteer08')
        today = date.today()
        now = timezone.now()

        def mk_visit(res, code, vol, status, day_offset, slot, **extra):
            rp = getattr(res, 'profile', None)
            return ServiceVisit.objects.create(
                subscription=None, service_type=type_objs[code], resident=res, volunteer=vol,
                scheduled_date=today + timedelta(days=day_offset), scheduled_slot=slot, status=status,
                address=(rp.address if rp else ''),
                latitude=(rp.current_latitude if rp else None),
                longitude=(rp.current_longitude if rp else None),
                **extra,
            )

        if not ServiceVisit.objects.exists():
            # ① 未落实：待管理员派单（单次任务地图演示）
            mk_visit(resident1, 'repair', None, 'assigned', 1, 10, note='卫生间水龙头漏水，需要上门维修')
            mk_visit(resident02, 'grocery', None, 'assigned', 0, 15, note='帮忙代购米面油和蔬菜')
            mk_visit(resident03, 'escort', None, 'assigned', 2, 9, note='陪同去水磨沟区医院复查')

            # ② 已排班待报到（今日晚间时段，不会立刻被超时扫描罚分）
            mk_visit(resident1, 'health_check', vol_tester, 'assigned', 0, 19, note='每周例行血压体温检查')
            mk_visit(resident02, 'cleaning', vol1, 'assigned', 1, 9)

            # ③ 已到场报到，待开始（报到坐标在居民楼下约 80 米）
            mk_visit(resident1, 'home_bath', vol4, 'checked_in', 0, 19,
                     checkin_latitude=BASE_LAT + 0.0017, checkin_longitude=BASE_LNG + 0.002,
                     checkin_distance_m=80, checkin_remote=False, checkin_at=now - timedelta(minutes=10))

            # ④ 服务中
            mk_visit(resident02, 'meal_delivery', vol8, 'processing', 0, 19,
                     checkin_latitude=BASE_LAT + 0.002, checkin_longitude=BASE_LNG - 0.003,
                     checkin_distance_m=45, checkin_remote=False,
                     checkin_at=now - timedelta(minutes=30), started_at=now - timedelta(minutes=25))

            # ⑤ 待居民确认（演示居民确认 + 志愿者催促；2 小时前提交，48h 内不会被自动确认）
            mk_visit(resident1, 'grocery', vol5, 'pending_confirm', 0, 9,
                     feedback='生活物资已代购送达，老人已签收',
                     checkin_distance_m=120, checkin_remote=False,
                     checkin_at=now - timedelta(hours=3), started_at=now - timedelta(hours=3),
                     completed_at=now - timedelta(hours=2), duration_minutes=60)

            # ⑥ 已完成（含健康记录与积分）
            mk_visit(resident1, 'health_check', vol1, 'completed', -2, 9,
                     systolic=128, diastolic=82, heart_rate=74, temperature=36.6,
                     health_note='血压略高，建议清淡饮食', feedback='老人状态良好',
                     checkin_distance_m=60, checkin_remote=False,
                     checkin_at=now - timedelta(days=2, hours=3),
                     started_at=now - timedelta(days=2, hours=3),
                     completed_at=now - timedelta(days=2, hours=2),
                     confirmed_at=now - timedelta(days=2, hours=1), duration_minutes=80)
            mk_visit(resident02, 'haircut', vol8, 'completed', -5, 14,
                     feedback='理发完成，老人很满意',
                     checkin_distance_m=95, checkin_remote=False,
                     checkin_at=now - timedelta(days=5, hours=2),
                     started_at=now - timedelta(days=5, hours=2),
                     completed_at=now - timedelta(days=5, hours=1),
                     confirmed_at=now - timedelta(days=5), duration_minutes=30)

            # ⑦ 已错过（昨日超时未报到，展示 DDL 罚分历史）
            mk_visit(resident03, 'escort_affairs', vol3, 'missed', -1, 9, note='陪同去社保局办事')

            # 完成单对应的志愿积分（10 + 每满30分钟加5）
            for u, pts in ((vol1, 20), (vol8, 15)):
                up = u.profile
                up.points = pts
                up.save(update_fields=['points'])

        # 为 resident1 的健康检查计划编排循环组（web 端轮换演示）
        hc_sub = ServiceSubscription.objects.filter(
            resident=resident1, service_type=type_objs['health_check']).first()
        if hc_sub and not hc_sub.rotation_volunteers:
            scheduler.build_rotation_group(hc_sub)

        # 已在册志愿者默认为已认证
        UserProfile.objects.filter(role='volunteer').update(is_verified=True)

        # 一条待审核的志愿者线上申请示例（inactive 账号 + 申请记录，无图，供审核演示）
        applicant, created = User.objects.get_or_create(username='apply_wang')
        if created:
            applicant.set_password('123456')
            applicant.is_active = False
            applicant.save()
            UserProfile.objects.get_or_create(
                user=applicant,
                defaults=dict(role='volunteer', is_verified=False, phone='13900000001',
                              community=COMMUNITY, skills='维修 家政'))
            VolunteerApplication.objects.get_or_create(
                user=applicant,
                defaults=dict(phone='13900000001', community=COMMUNITY, skills='维修 家政',
                              note='本人有 3 年水电维修经验，希望加入社区志愿服务。', status='pending'))

        # === 应急模块（保留为次要能力）===
        Warning.objects.get_or_create(
            title='暴雨蓝色预警',
            defaults={
                'warning_type': 'rainstorm',
                'level': 'blue',
                'content': '预计未来数小时水磨沟区可能出现强降雨，请居民注意出行安全并防范内涝。',
                'community': COMMUNITY,
                'is_active': True,
            }
        )

        Shelter.objects.get_or_create(
            name='水磨沟区应急避难点',
            defaults={
                'address': '水磨沟区人民广场',
                'capacity': 300,
                'contact_phone': '13800000000',
                'longitude': BASE_LNG,
                'latitude': BASE_LAT,
                'is_available': True,
            }
        )

        Material.objects.get_or_create(
            name='矿泉水',
            defaults={
                'category': '饮用水',
                'quantity': 100,
                'unit': '箱',
                'storage_location': '社区仓库A区',
                'warning_quantity': 20,
                'production_date': timezone.now().date() - timedelta(days=120),
                'expire_date': timezone.now().date() + timedelta(days=20),
                'expiry_warning_days': 30,
            }
        )

        self.stdout.write(self.style.SUCCESS('演示数据初始化完成（乌鲁木齐水磨沟社区 · 社区长期服务）'))
