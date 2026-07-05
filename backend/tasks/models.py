from django.db import models
from django.contrib.auth.models import User
from requests_app.models import HelpRequest


class VolunteerTask(models.Model):
    STATUS_CHOICES = (
        ('assigned', '已分配'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    )

    help_request = models.OneToOneField(
        HelpRequest,
        on_delete=models.CASCADE,
        related_name='volunteer_task',
        verbose_name='关联求助'
    )

    volunteer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='volunteer_tasks',
        verbose_name='志愿者'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='assigned',
        verbose_name='任务状态'
    )

    feedback = models.TextField(
        blank=True,
        null=True,
        verbose_name='处理反馈'
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='分配时间'
    )

    accepted_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='接单时间'
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='完成时间'
    )

    def __str__(self):
        return f'任务 {self.id} - {self.get_status_display()}'

    class Meta:
        verbose_name = '志愿者任务'
        verbose_name_plural = '志愿者任务'
        ordering = ['-assigned_at']