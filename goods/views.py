from django.shortcuts import render, redirect, reverse
from django.views import View
from django.core.cache import cache
from django_redis import get_redis_connection

from goods import models
from order import models as order_models
from utils.pages import Paginator
# Create your views here.


'''
FastDFS:
tracker docker: docker run -ti -d --name trakcer -v ~/tracker_data:/fastdfs/tracker/data --net=host season/fastdfs tracker
storage docker: docker run -ti --name storage -v ~/storage_data:/fastdfs/storage/data -v ~/store_path:/fastdfs/store_path --net=host -e TRACKER_SERVER:192.168.1.2:22122 season/fastdfs storage

from fdfs_client.client import get_tracker_conf, Fdfs_client
client = Fdfs_client(get_tracker_conf('./utils/client.conf'))
client.upload_by_filename('./utils/a.png')
{
    'Group name': b'group1', 
    'Remote file_id': b'group1/M00/00/00/rBLk_lxmOXeAcMArAAFNqduP814053.png', 
    'Status': 'Upload successed.', 
    'Local file name': './utils/a.png', 
    'Uploaded size': '83.42KB', 
    'Storage IP': b'47.107.176.243'
}

'''

class IndexView(View):
    '首页处理视图类'
    def get(self, request):
        '显示首页页面'

        # 设置缓存
        context = cache.get('index_page_data')
        if not context:
            print('设置缓存')
            # 获取商品的种类信息
            types = models.GoodsType.objects.all()

            # 获取首页轮播商品信息
            index_banner_goods = models.IndexGoodsBanner.objects.all().order_by('index')

            # 获取首页促销活动信息
            index_promotion_goods = models.IndexPromotionBanner.objects.all().order_by('index')

            # 获取首页分类商品展示信息
            for type in types:
                # 获取展示为图片类型的商品
                image_type_goods = models.IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')

                # 获取展示为图片类型的商品
                title_title_goods = models.IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

                # 动态给type增加属性，分别保存首页分类商品的图片展示信息和文字展示信息
                type.image_type_goods = image_type_goods
                type.title_type_goods = title_title_goods
            context = {'types':types,
                       'index_banner_goods': index_banner_goods,
                       'index_promotion_goods': index_promotion_goods,}

            # 设置缓存
            cache.set('index_page_data', context, 3600)

        # 获取购物车数目数据
        cart_count = 0
        if request.user.is_authenticated:
            conn = get_redis_connection('default')
            cart_count = conn.hlen(f'cart_{request.user.id}')

        # 更新购物车数据 到模板所需的数据
        context.update(cart_count=cart_count)

        return render(request, 'goods/index.html', context)


class DetailView(View):
    '商品详情试图类'
    def get(self, request, goods_id):
        '显示商品详情页'

        # 获取sku
        try:
            sku = models.GoodsSKU.objects.get(id=goods_id)
        except models.GoodsSKU.DoesNotExist:
            # 商品不存在
            return redirect(to=reverse('goods:index'))

        # 获取所有的商品分类信息
        types = models.GoodsType.objects.all()

        # 获取新品信息
        new_skus = models.GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]

        # 获取同一spu的其他sku商品
        same_spu_skus = models.GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)

        # 获取评论信息
        sku_orders = order_models.OrderGoods.objects.filter(sku=sku).exclude(comment='')

        # 购物车相关
        cart_count = 0
        if request.user.is_authenticated:
            # 获取购物车数目数据
            conn = get_redis_connection('default')
            cart_count = conn.hlen(f'cart_{request.user.id}')

            # 添加用户的历史记录
            key = f'history_{request.user.id}'
            # 移除列表中的goods_id，count为0代表移除redis中hset中所有value值
            conn.lrem(key, 0, goods_id)

            # 把浏览过商品的goods_id添加到列表的左侧
            conn.lpush(key, goods_id)

            # 只保存用户最新浏览的5条信息
            conn.ltrim(key, 0, 4)

        # 组织模板上下文
        context = {
            'sku': sku,
            'types': types,
            'new_skus': new_skus,
            'same_spu_skus': same_spu_skus,
            'sku_orders': sku_orders,
            'cart_count': cart_count
        }

        return render(request, 'goods/detail.html', context)

# /list/种类id/页码?sort=排序方式
class GoodsListView(View):
    '商品分类列表展示类'

    def get(self, request, type_id, page):
        '显示列表页'

        # 获取种类信息
        try:
            type = models.GoodsType.objects.get(id=type_id)
        except models.GoodsType.DoesNotExist:
            # 种类信息不存在
            return redirect(to=reverse('goods:index'))

        # 获取商品的分类信息
        types = models.GoodsType.objects.all()

        sort = request.GET.get('sort')
        if sort == 'price':
            # 按照价格排序
            skus = models.GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            # 按照商品热度（销售量）排序
            skus = models.GoodsSKU.objects.filter(type=type).order_by('sales')
        else:
            # 默认排序方式，按照更新时间排序
            sort = 'default'
            skus = models.GoodsSKU.objects.filter(type=type).order_by('update_time')

        # 获取新品信息
        new_skus = models.GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]

        # 购物车相关
        cart_count = 0
        if request.user.is_authenticated:
            # 获取购物车数目数据
            conn = get_redis_connection('default')
            cart_count = conn.hlen(f'cart_{request.user.id}')

        page = Paginator(page, request, skus.count(), 4, 5)


        # 组织模板上下文
        context = {
            'type': type,
            'types': types,
            'new_skus': new_skus,
            'skus': skus,
            'cart_count': cart_count,
            'sort': sort,
            'page': page,
            'temp_list': [1,2,3,4,5,6]
        }

        return render(request, 'goods/list.html', context)


# from haystack.generic_views import SearchView
#
# class GoodsSearchView():   # (SearchView):
#     def get_context_data(self, *, object_list=None, **kwargs):
#         """Get the context for this view."""
#         queryset = object_list if object_list is not None else self.object_list
#         paginator = Paginator(queryset, None, queryset.count, 4, 5)
#
#         # context_object_name = self.get_context_object_name(queryset)
#         if paginator.total_data_count:
#             paginator, page, queryset, is_paginated = self.paginate_queryset(queryset, page_size)
#             context = {
#                 'paginator': paginator,
#                 'object_list': queryset
#             }
#         else:
#             context = {
#                 'paginator': None,
#                 'page_obj': None,
#                 'is_paginated': False,
#                 'object_list': queryset
#             }
#         return super().get_context_data(**context)


