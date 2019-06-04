import os
from datetime import datetime

from django.views import View
from django.http import JsonResponse
from django.shortcuts import render, redirect, reverse
from django.db import transaction
from django_redis import get_redis_connection
from django.conf import settings
from alipay import AliPay

from goods.models import GoodsSKU
from user.models import Address
from order import models
from utils.mixin import LoginRequiredMixin

# Create your views here.


# /order/place
class OrderPlaceView(LoginRequiredMixin, View):
    '''订单显示页'''
    def post(self, request):
        # 1. 获取sku_ids参数
        sku_ids = request.POST.getlist('sku_ids')
        if not sku_ids:
            return redirect(reverse('cart:cart_info'))

        # 2. 业务处理，获取商品订单信息
        conn = get_redis_connection('default')
        cart_key = f'cart_{request.user.id}'

        # 遍历sku_ids获取用户购物车中的商品信息
        skus = []
        total_count = 0
        total_amount = 0
        for sku_id in sku_ids:
            # 根据id获取商品的信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 从redis获取购物车商品信息,并给sku动态赋值
            sku.count = int(conn.hget(cart_key, sku_id))
            # 计算单间商品的总价，并给sku动态赋值
            sku.amount = sku.price * sku.count
            # 把每个sku添加到商品列表：skus
            skus.append(sku)

            total_count += sku.count
            total_amount += sku.amount

        # 运费：此处暂时写死为10元，具体应该根据实际业务计算
        transit_price = 10

        # 用户最终要支付的总费用
        finall_pay = total_amount + transit_price

        # 获取当前用户的所有地址
        address = request.user.address_set.all()

        # 组织上下文
        sku_ids = ','.join(sku_ids)  # [1,25]->1,25
        context = {'skus': skus,
                   'total_count': total_count,
                   'total_amount': total_amount,
                   'transit_price': transit_price,
                   'finall_pay': finall_pay,
                   'address': address,
                   'sku_ids': sku_ids}

        # 使用模板
        return render(request, 'order/place_order.html', context)


# 前端传递的参数:地址id(addr_id) 支付方式(pay_method) 用户要购买的商品id字符串(sku_ids)
# mysql事务: 一组sql操作，要么都成功，要么都失败
# 高并发
# #### 悲观锁 ####
class OrderCommitView(View):
    @transaction.atomic
    def post(self, request):
        # todo: 1. 校验
        if not request.user.is_authenticated:
            return {'status_code':1, 'msg': '用户未登陆，请先登陆'}

        # 接收参数
        addr_id = request.POST.get('addr_id')
        pay_metod = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')
        # 校验参数完整性
        if not all([addr_id, pay_metod, sku_ids]):
            return JsonResponse({'status_code':2, 'msg': '参数不完整'})
        # 校验支付方式
        if pay_metod not in models.OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'status_code':3, 'msg': '非法的支付方式参数'})
        # 校验地址的正确性
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'status_code':4, 'msg': '地址不存在，请重新选择'})

        # todo：2. 创建订单核心业务
        # 组织参数
        # 订单ID：日期时间+userid：20190306105310+user_id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S')

        transit_price = 10
        total_count = 0
        total_price = 0

        # 设置事务保存点
        save_point = transaction.savepoint()

        try:
            # todo: 向df_order_info表中添加一条记录
            order = models.OrderInfo.objects.create(order_id=order_id,
                                                    user=request.user,
                                                    address=addr,
                                                    pay_method=pay_metod,
                                                    total_count=total_count,
                                                    total_price=total_price,
                                                    transit_price=transit_price,
                                                    )

            # todo: 3. 用户的订单中有几个商品，需要向df_order_goods表中加入几条记录
            conn = get_redis_connection('default')
            cart_key = f'cart_{request.user.id}'

            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                # 商品信息
                try:
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    # 事务回滚
                    transaction.savepoint_rollback(save_point)
                    return JsonResponse({'status_code': 5, 'msg': '商品不存在'})
                # 商品数量
                count = int(conn.hget(cart_key, sku_id))

                # todo 判断商品的库存
                if count > sku.stock:
                    transaction.savepoint_rollback(save_point)
                    return JsonResponse({'status_code': 6, 'msg': '商品库存不足'})

                # todo: 向df_order_goods表中添加对应的订单商品记录
                models.OrderGoods.objects.create(order=order, sku=sku, count=count, price=sku.price)

                # 更新商品数量和销量
                sku.stock -= count
                sku.sales += count
                sku.save()

                # todo: 累加计算订单商品的总数量和总价格
                total_count += count
                total_price += (sku.price * count)

            # 更新订单信息表中总数量和总价格
            order.tatol_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            # 事务回滚
            transaction.savepoint_rollback(save_point)
            return JsonResponse({'status_code': 7, 'msg': '下单失败'})

        # todo：4. 清除购物车中对应商品的记录
        conn.hdel(cart_key, *sku_ids)

        return JsonResponse({'status_code':0, 'msg': '创建订单成功'})


class OrderPayView(View):
    def post(self, request):
        # 1. 校验是否登陆
        if not request.user.is_authenticated:
            return JsonResponse({'status_code':1, 'msg': '用户未登陆'})

        # 2. 校验post参数
        order_id = request.POST.get('order_id')
        if not order_id :
            return JsonResponse({'status_code':2, 'msg': '未接收到订单id'})
        try:
            order = models.OrderInfo.objects.get(order_id=order_id,
                                            user=request.user,
                                            pay_method=3,
                                            order_status=1)
        except models.OrderInfo.DoesNotExist:
            return JsonResponse({'status_code':3, 'msg': '无效的订单id'})

        # 3. 业务处理:使用python sdk调用支付宝的支付接口
        # todo 初始化
        app_private_key_string = open(os.path.join(settings.BASE_DIR, 'order', 'app_private_key.pem')).read()
        alipay_public_key_string = open(os.path.join(settings.BASE_DIR, 'order', 'alipay_public_key.pem')).read()

        alipay = AliPay(
            appid="2016092800614716",
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            alipay_public_key_string=alipay_public_key_string,  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",                                    # RSA 或者 RSA2
            debug = True  # 默认False,此处为沙箱环境
        )
        # todo 使用第三方sdk向支付宝发送支付请求，创建支付订单
        # 电脑网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(order.total_price + order.transit_price),
            subject=f'天天生鲜-{order_id}',
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'status_code':0, 'msg': '请求订单支付页面成功', 'pay_url':pay_url})