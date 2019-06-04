from django.contrib import admin
from django.core.cache import cache

from . import models
# Register your models here.


class BaseModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        '增加或者更新表中数据事触发'
        # 调用父类的save_model方法
        super().save_model(request, obj, form, change)

        # 发出更新任务，让celery worker触发更新，重写生成首页
        from celery_task.tasks import generic_static_index_html
        generic_static_index_html.delay()

        # 清除首页的缓存数据（触发更新）
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        '增加或者更新表中数据事触发'
        # 调用父类的save_model方法
        super().delete_model(request, obj)

        # 发出更新任务，让celery worker触发更新，重写生成首页
        from celery_task.tasks import generic_static_index_html
        generic_static_index_html.delay()

        # 清除首页的缓存数据（触发更新）
        cache.delete('index_page_data')


@admin.register(models.IndexGoodsBanner)
class IndexGoodsBannerAdmin(BaseModelAdmin):pass


@admin.register(models.IndexTypeGoodsBanner)
class IndexTypeGoodsBannerAdmin(BaseModelAdmin):pass


@admin.register(models.IndexPromotionBanner)
class IndexPromotionBanner(BaseModelAdmin):pass


@admin.register(models.Goods)
class GoodsAdmin(admin.ModelAdmin):
    list_display = ['name']
    list_display_links = None
    list_editable = ['name']


@admin.register(models.GoodsSKU)
class GoodsSKUAdmin(admin.ModelAdmin):
    list_filter = ['type', 'goods']


@admin.register(models.GoodsType)
class GoodsTypeAdmin(admin.ModelAdmin):pass



# admin.site.register(models.GoodsType)
# admin.site.register(models.Goods, GoodsAdmin)
# admin.site.register(models.GoodsSKU, GoodsSKUAdmin)
#
# admin.site.register(models.IndexGoodsBanner)
# admin.site.register(models.IndexTypeGoodsBanner)
# admin.site.register(models.IndexPromotionBanner)
