from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.authtoken.models import Token

from users.models import UserProfile
from alerts.models import Warning
from resources.models import Shelter, Material
from services.models import ServiceType, ServiceSubscription
from services import scheduler

# 演示社区：乌鲁木齐水磨沟社区（水磨沟区中心约 87.6417, 43.8256）
COMMUNITY = '乌鲁木齐水磨沟社区'
BASE_LNG = 87.6417
BASE_LAT = 43.8256


class Command(BaseCommand):
    help = '初始化演示数据（社区长期服务平台）'

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
        self.create_user('admin02', '123456', 'admin', '13800000001')

        # 鸿蒙端登录页默认展示 resident1 / volunteer1，因此后端初始化也创建同名账号。
        # 居民按“长期服务受益人”（如独居老人）设定。
        resident1 = self.create_user('resident1', '123456', 'resident', '13800000002',
                                     address='水磨沟区新兴街1号楼', longitude=BASE_LNG + 0.002, latitude=BASE_LAT + 0.001)
        resident02 = self.create_user('resident02', '123456', 'resident', '13800000012',
                                      address='水磨沟区南湖南路5号楼', longitude=BASE_LNG - 0.003, latitude=BASE_LAT + 0.002)

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

        # === 社区服务目录 ===
        service_types = [
            dict(code='health_check', name='老人健康检查', category='医疗健康', required_skill='医疗',
                 default_frequency='weekly', needs_health_record=True, icon='🩺',
                 description='为独居/高龄老人每周上门测量血压、心率、体温并记录健康档案。'),
            dict(code='home_bath', name='助浴服务', category='生活照护', required_skill='助浴',
                 default_frequency='weekly', icon='🛁',
                 description='协助行动不便老人安全洗浴。'),
            dict(code='grocery', name='代购跑腿', category='生活便民', required_skill='代购',
                 default_frequency='weekly', icon='🛒',
                 description='为老人代购米面粮油、药品等日常物资。'),
            dict(code='escort', name='陪同就医', category='医疗健康', required_skill='陪诊',
                 default_frequency='monthly', icon='🏥',
                 description='陪同老人到医院挂号、就诊、取药。'),
            dict(code='cleaning', name='居家保洁', category='生活照护', required_skill='保洁',
                 default_frequency='biweekly', icon='🧹',
                 description='为老人家庭提供居室清扫整理。'),
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

        # === 服务计划（为老人建立周期性服务）===
        plans = [
            (resident1, 'health_check', 'weekly', 0),
            (resident1, 'grocery', 'weekly', 2),
            (resident02, 'health_check', 'weekly', 1),
            (resident02, 'cleaning', 'biweekly', 4),
        ]
        for res, code, freq, weekday in plans:
            rp = getattr(res, 'profile', None)
            ServiceSubscription.objects.get_or_create(
                resident=res, service_type=type_objs[code],
                defaults=dict(
                    frequency=freq, preferred_weekday=weekday, is_active=True,
                    start_date=timezone.now().date(),
                    address=(rp.address if rp else ''),
                    longitude=(rp.current_longitude if rp else None),
                    latitude=(rp.current_latitude if rp else None),
                )
            )

        # 生成一批到期工单并自动派单，方便演示（不发通知，避免刷屏）
        scheduler.generate_due_visits(notify=False)

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
