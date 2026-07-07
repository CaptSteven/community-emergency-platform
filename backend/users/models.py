from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('resident', '居民'),
        ('volunteer', '志愿者'),
        ('admin', '管理员'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='用户'
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        verbose_name='用户角色'
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='联系电话'
    )

    community = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='所属社区'
    )

    address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='详细地址'
    )

    current_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        verbose_name='当前纬度'
    )

    current_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        verbose_name='当前经度'
    )

    location_updated_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='位置更新时间'
    )

    skills = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='擅长任务'
    )

    is_available = models.BooleanField(
        default=True,
        verbose_name='是否空闲'
    )

    points = models.IntegerField(
        default=0,
        verbose_name='志愿积分'
    )

    is_verified = models.BooleanField(
        default=False,
        verbose_name='是否已认证',
        help_text='志愿者资料经管理员审核/面试通过后置为已认证'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )

    def __str__(self):
        return f'{self.user.username} - {self.get_role_display()}'

    class Meta:
        verbose_name = '用户资料'
        verbose_name_plural = '用户资料'


class VolunteerApplication(models.Model):
    """志愿者线上申请：填表 + 上传证件图 → 管理员 web 端审核/线下面试 → 通过后开通账号。"""

    STATUS_CHOICES = (
        ('pending', '待审核'),
        ('interviewing', '面试中'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
    )

    # 申请时即创建的 inactive 志愿者账号（审核通过后激活）
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='volunteer_application', verbose_name='关联账号'
    )
    phone = models.CharField(max_length=20, blank=True, default='', verbose_name='联系电话')
    community = models.CharField(max_length=100, blank=True, default='', verbose_name='所属社区')
    address = models.CharField(max_length=255, blank=True, default='', verbose_name='详细地址')
    skills = models.CharField(max_length=255, blank=True, default='', verbose_name='擅长技能')
    note = models.TextField(blank=True, default='', verbose_name='自我介绍')

    # 证件图片
    id_card_front = models.FileField(upload_to='volunteer_apps/', null=True, blank=True, verbose_name='身份证正面')
    id_card_back = models.FileField(upload_to='volunteer_apps/', null=True, blank=True, verbose_name='身份证反面')
    skill_cert = models.FileField(upload_to='volunteer_apps/', null=True, blank=True, verbose_name='技能/资格证书')
    health_cert = models.FileField(upload_to='volunteer_apps/', null=True, blank=True, verbose_name='健康证')
    profile_photo = models.FileField(upload_to='volunteer_apps/', null=True, blank=True, verbose_name='个人形象照')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='审核状态')
    review_note = models.TextField(blank=True, default='', verbose_name='审核意见')
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_applications', verbose_name='审核人'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='申请时间')

    class Meta:
        verbose_name = '志愿者申请'
        verbose_name_plural = '志愿者申请'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} 的志愿者申请 - {self.get_status_display()}'