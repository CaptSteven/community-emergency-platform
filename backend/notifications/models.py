from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    CATEGORY_CHOICES = (
        ('warning', '灾害预警'),
        ('help_request', '居民求助'),
        ('task', '志愿者任务'),
        ('service', '社区服务'),
        ('system', '系统消息'),
    )

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='接收人'
    )

    title = models.CharField(max_length=100, verbose_name='消息标题')
    content = models.TextField(verbose_name='消息内容')

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default='system',
        verbose_name='消息类型'
    )

    is_read = models.BooleanField(default=False, verbose_name='是否已读')

    related_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='关联对象类型'
    )

    related_id = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='关联对象ID'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '站内消息'
        verbose_name_plural = '站内消息'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.recipient.username} - {self.title}'