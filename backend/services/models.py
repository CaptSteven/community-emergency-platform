from django.db import models
from django.contrib.auth.models import User


FREQUENCY_CHOICES = (
    ('daily', '每日'),
    ('weekly', '每周'),
    ('biweekly', '每两周'),
    ('monthly', '每月'),
)

# 服务适用方式：单次任务 / 周期计划 / 两者皆可
SERVICE_MODE_CHOICES = (
    ('single', '单次'),
    ('recurring', '周期'),
    ('both', '通用'),
)

WEEKDAY_CHOICES = (
    (0, '周一'),
    (1, '周二'),
    (2, '周三'),
    (3, '周四'),
    (4, '周五'),
    (5, '周六'),
    (6, '周日'),
)


class ServiceType(models.Model):
    """社区服务目录：健康检查/助浴/代购/陪诊/保洁等长期服务类型。"""

    name = models.CharField(max_length=50, verbose_name='服务名称')
    code = models.CharField(max_length=30, unique=True, verbose_name='服务标识')
    category = models.CharField(max_length=30, blank=True, default='', verbose_name='服务分类')
    description = models.TextField(blank=True, default='', verbose_name='服务说明')
    required_skill = models.CharField(
        max_length=50, blank=True, default='',
        verbose_name='所需技能',
        help_text='志愿者 skills 中需包含该关键字才能被自动排班'
    )
    default_frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, default='weekly', verbose_name='默认服务周期'
    )
    service_mode = models.CharField(
        max_length=20, choices=SERVICE_MODE_CHOICES, default='both', verbose_name='适用方式',
        help_text='single=只用于单次任务；recurring=只用于周期计划；both=两者皆可'
    )
    duration_minutes = models.IntegerField(default=30, verbose_name='预计时长(分钟)')
    needs_health_record = models.BooleanField(default=False, verbose_name='是否录入健康记录')
    icon = models.CharField(max_length=8, blank=True, default='🛎️', verbose_name='图标')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '服务类型'
        verbose_name_plural = '服务类型'
        ordering = ['-is_active', 'name']

    def __str__(self):
        return f'{self.name}({self.get_default_frequency_display()})'


class ServiceSubscription(models.Model):
    """服务计划/订阅：为某位居民（如独居老人）建立的周期性上门服务。"""

    resident = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='service_subscriptions', verbose_name='受益居民'
    )
    service_type = models.ForeignKey(
        ServiceType, on_delete=models.PROTECT, related_name='subscriptions', verbose_name='服务类型'
    )
    frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, default='weekly', verbose_name='服务周期'
    )
    preferred_weekday = models.IntegerField(
        choices=WEEKDAY_CHOICES, default=0, verbose_name='首选星期'
    )
    preferred_time = models.CharField(
        max_length=10, blank=True, default='', verbose_name='首选时段'
    )
    address = models.CharField(max_length=255, blank=True, default='', verbose_name='服务地址')
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, blank=True, null=True, verbose_name='纬度'
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7, blank=True, null=True, verbose_name='经度'
    )
    note = models.TextField(blank=True, default='', verbose_name='备注')
    is_active = models.BooleanField(default=True, verbose_name='是否生效')
    start_date = models.DateField(null=True, blank=True, verbose_name='起始日期')
    last_generated_date = models.DateField(null=True, blank=True, verbose_name='最近排班日期')
    # 循环组：智能筛选出的合格志愿者(按距离+技能)有序 id 列表；rotation_index 指向下一位轮到的人
    rotation_volunteers = models.JSONField(default=list, blank=True, verbose_name='轮换循环组(志愿者ID有序表)')
    rotation_index = models.IntegerField(default=0, verbose_name='当前轮换位置')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_subscriptions', verbose_name='创建人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '服务计划'
        verbose_name_plural = '服务计划'
        ordering = ['-is_active', '-created_at']

    def __str__(self):
        return f'{self.resident.username} - {self.service_type.name} - {self.get_frequency_display()}'


class ServiceVisit(models.Model):
    """上门服务工单：一次具体的上门服务，由系统按技能匹配轮流自动派给志愿者。"""

    STATUS_CHOICES = (
        ('assigned', '已排班'),
        ('processing', '服务中'),
        ('pending_confirm', '待居民确认'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('missed', '已错过'),
    )

    subscription = models.ForeignKey(
        ServiceSubscription, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='visits', verbose_name='关联服务计划'
    )
    service_type = models.ForeignKey(
        ServiceType, on_delete=models.PROTECT, related_name='visits', verbose_name='服务类型'
    )
    resident = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='service_visits', verbose_name='受益居民'
    )
    volunteer = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='service_duties', verbose_name='服务志愿者'
    )
    scheduled_date = models.DateField(verbose_name='计划上门日期')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='assigned', verbose_name='工单状态'
    )
    address = models.CharField(max_length=255, blank=True, default='', verbose_name='服务地址')
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, blank=True, null=True, verbose_name='纬度'
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7, blank=True, null=True, verbose_name='经度'
    )
    note = models.TextField(blank=True, default='', verbose_name='需求说明')
    duration_minutes = models.IntegerField(null=True, blank=True, verbose_name='服务时长(分钟)')
    feedback = models.TextField(blank=True, default='', verbose_name='服务反馈')
    completion_photo = models.FileField(
        upload_to='service_visits/', null=True, blank=True, verbose_name='完成凭证照片'
    )
    # 居民确认完成时上传的凭证照片（与志愿者 completion_photo 并存）
    confirm_photo = models.FileField(
        upload_to='service_visits/', null=True, blank=True, verbose_name='居民确认照片'
    )

    # 健康记录字段（仅健康检查类服务使用，其余留空）
    systolic = models.IntegerField(null=True, blank=True, verbose_name='收缩压(高压)')
    diastolic = models.IntegerField(null=True, blank=True, verbose_name='舒张压(低压)')
    heart_rate = models.IntegerField(null=True, blank=True, verbose_name='心率')
    temperature = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='体温(℃)'
    )
    health_note = models.TextField(blank=True, default='', verbose_name='健康备注')

    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='志愿者提交完成时间')
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name='居民确认完成时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '上门服务工单'
        verbose_name_plural = '上门服务工单'
        ordering = ['-scheduled_date', '-created_at']

    def __str__(self):
        return f'{self.resident.username} - {self.service_type.name} - {self.get_status_display()}'
