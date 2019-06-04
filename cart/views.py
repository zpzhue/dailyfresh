from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from django_redis import get_redis_connection

from goods.models import GoodsSKU
from utils.mixin import LoginRequiredMixin
# Create your views here.


class CartAddView(View):
    '''添加购物车视图类'''
    def post(self, request):
        user = request.user

        # 1. 检验用户是否登陆
        if not user:
            return JsonResponse({'status_code': 1, 'msg': '用户未登陆'})

        # 2. 检验数据完整性
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        if not all([sku_id, count]):
            return JsonResponse({'status_code': 2, 'msg': '数据不完整'})

        # 3. 校验商品id及商品数量
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'status_code': 3, 'msg': '商品数目出错'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist as e:
            # 商品sku_id错误
            return JsonResponse({'status_code': 4, 'msg': '商品不存在'})

        # 4. 获取购物车信息
        # 业务处理，添加购物车记录
        conn = get_redis_connection('default')
        cart_key = f'cart_{user.id}'
        # 尝试获取sku_id对应的数量， hget cart_user_id sku_id
        # hget -> 如果键不存在，则返回None, hset返回的是字节：b'1'
        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            # 累加购物车中商品的数目
            count += int(cart_count)

        # 校验商品的库存
        if count > sku.stock:
            return JsonResponse({'status_code': 5, 'msg': '商品库存不足'})

        # 设置hset中sku_id对应的值
        # hset -> 如果sku_存在，则更新sku_id所对应的数据，否则添加数据
        conn.hset(cart_key, sku_id, count)

        # 获取用户购物车中商品的条目数
        total_count = conn.hlen(cart_key)
        print(total_count)

        return JsonResponse({'status_code': 0, 'total_count':total_count, 'msg': '更新成功'})


class CartInfoView(LoginRequiredMixin, View):
    '''用户购物车展示视图类'''
    def get(self, request):
        # 获取用户购物车所有商品信息
        conn = get_redis_connection('default')
        # hgetall 返回格式：{b'4': b'2', b'2': b'3', b'1': b'2'}
        cart_dict = conn.hgetall(f'cart_{request.user.id}')

        sku_list = []
        total_count = 0
        total_price = 0

        for sku_id, count in cart_dict.items():
            sku = GoodsSKU.objects.get(id=sku_id)
            # 给单个sku增加总价格和总数量的属性，用于前端展示
            sku.amount = sku.price * int(count)
            sku.count = int(count)
            sku_list.append(sku)

            # 累加商品的总数量和总价格
            total_count += int(count)
            total_price += sku.amount

        # 组织上下文
        context = {
            'sku_list': sku_list,
            'total_count': total_count,
            'total_price': total_price,
        }

        return render(request, 'cart/cart.html', context)


class CartUpdateView(View):
    '''添加购物车视图类'''
    def post(self, request):
        user = request.user

        # 1. 检验用户是否登陆
        if not user:
            return JsonResponse({'status_code': 1, 'msg': '用户未登陆'})

        # 2. 检验数据完整性
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        if not all([sku_id, count]):
            return JsonResponse({'status_code': 2, 'msg': '数据不完整'})

        # 3. 校验商品id及商品数量
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'status_code': 3, 'msg': '商品数目出错'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist as e:
            # 商品sku_id错误
            return JsonResponse({'status_code': 4, 'msg': '商品不存在'})

        # 4. 获取购物车信息
        # 业务处理，添加购物车记录
        conn = get_redis_connection('default')
        cart_key = f'cart_{user.id}'

        # 校验商品的库存
        if count > sku.stock:
            return JsonResponse({'status_code': 5, 'msg': '商品库存不足'})

        # 设置hset中sku_id对应的值
        # hset -> 如果sku_存在，则更新sku_id所对应的数据，否则添加数据
        # #### 更新 ####
        conn.hset(cart_key, sku_id, count)

        # 获取用户购物车中商品的条目数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        return JsonResponse({'status_code': 0, 'total_count':total_count, 'msg': '更新成功'})


class CartDeleteView(View):
    '''删除购物车商品视图类'''

    def post(self, request):
        user = request.user

        # 1. 检验用户是否登陆
        if not user:
            return JsonResponse({'status_code': 1, 'msg': '用户未登陆'})

        # 2. 检验数据完整性
        sku_id = request.POST.get('sku_id')
        if not sku_id:
            return JsonResponse({'status_code': 2, 'msg': '无效的商品id'})

        # 3. 校验商品id
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist as e:
            # 商品sku_id错误
            return JsonResponse({'status_code': 3, 'msg': '商品不存在'})

        # 4. 获取购物车信息
        # 业务处理，添加购物车记录
        conn = get_redis_connection('default')
        cart_key = f'cart_{user.id}'

        # 删除购物车商品记录
        conn.hdel(cart_key, sku_id)

        # 获取用户购物车中商品的条目数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        return JsonResponse({'status_code': 0, 'total_count': total_count, 'msg': '删除成功'})