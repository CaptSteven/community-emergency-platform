from django.db import models


class Shelter(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name='避难点名称'
    )

    address = models.CharField(
        max_length=255,
        verbose_name='避难点地址'
    )

    capacity = models.IntegerField(
        default=0,
        verbose_name='可容纳人数'
    )

    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='联系电话'
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        verbose_name='纬度'
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        verbose_name='经度'
    )

    is_available = models.BooleanField(
        default=True,
        verbose_name='是否可用'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '避难点'
        verbose_name_plural = '避难点'


class Material(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name='物资名称'
    )

    category = models.CharField(
        max_length=50,
        verbose_name='物资类别'
    )

    quantity = models.IntegerField(
        default=0,
        verbose_name='库存数量'
    )

    unit = models.CharField(
        max_length=20,
        default='件',
        verbose_name='单位'
    )

    storage_location = models.CharField(
        max_length=255,
        verbose_name='存放位置'
    )

    warning_quantity = models.IntegerField(
        default=10,
        verbose_name='库存预警值'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )

    def __str__(self):
        return f'{self.name} - {self.quantity}{self.unit}'

    class Meta:
        verbose_name = '应急物资'
        verbose_name_plural = '应急物资'