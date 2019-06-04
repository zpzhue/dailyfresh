from django.conf import settings
from django.contrib import auth
from django.views.generic import View
from django.shortcuts import render,redirect, reverse, HttpResponse
from django_redis import get_redis_connection
from django.core.paginator import Paginator
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired

from order.models import OrderInfo
from user import models
from goods import models as goods_model
from celery_task import tasks
from utils.mixin import LoginRequiredMixin
from .forms import RegisterModelForm, LoginModelForm, AddressInfoForm


class RegisterView(View):
    '''注册视图类'''

    def get(self, request):
        '显示注册页面'
        form = RegisterModelForm()
        return render(request, 'user/register.html', {'form': form})

    def post(self, request):
        '处理注册请求'
        form = RegisterModelForm(request.POST)

        # 校验数据
        if not form.is_valid():
            return render(request, 'user/register.html', {'form': form})

        # 创建用户
        user = models.User.objects.create_user(username=form.cleaned_data.get('username'),
                                        password=form.cleaned_data.get('password'),
                                        email=form.cleaned_data.get('email'))
        # 标记用户为未激活
        user.is_active = 0
        user.save()

        # 发送激活邮件，包含激活链接：http://127.0.0.1:8000/user/active/<user_id>
        # 使用 itsdangerous 加密要嵌入进url中的user_id
        serializer = Serializer(settings.SECRET_KEY, expires_in=3600)
        token = serializer.dumps({'reg_user_id': user.id})                   # 得到的是byte
        token = token.decode()

        # 使用celery异步发送邮件
        tasks.send_register_active_mail(form.cleaned_data.get('email'), user.username, token)

        return redirect(reverse('user:login'))


class LoginView(View):
    '''登陆视图类'''
    def get(self, request):
        '显示登陆页面'
        username = request.COOKIES.get('username', '')
        checked = 'checked' if username else ''
        form = LoginModelForm()
        return render(request, 'user/login.html', {'username': username, 'checked': checked, 'form': form})

    def post(self, request):
        username = request.POST.get('username')
        pwd = request.POST.get('password')
        form = LoginModelForm(request.POST)

        # 判断用户是否激活
        user = models.User.objects.filter(username=username).first()
        if not user:
            return render(request, 'user/login.html', {'error_msg': '用户名不存在', 'form': form})
        if user.is_active:
            # 校验用户身份信息
            user = auth.authenticate(username=username, password=pwd)
            if user:
                # 使用django内置认证系统记录登陆状态
                auth.login(request, user)

                # 构建响应请求
                response = redirect(reverse('goods:index'))

                # 判断是否勾选记住用户名
                remember = request.POST.get('remember')
                if remember == 'on':
                    response.set_cookie('username', user.username, max_age= 3 * 3600)
                else:
                    response.delete_cookie('username')
                # 返回响应
                return response
            else:
                return render(request, 'user/login.html', {'error_msg': '用户名或密码错误', 'form': form})
        else:
            # 用户未激活
            return render(request, 'user/login.html', {'error_msg': '账户未激活', 'form':form})


class ActiveRegisterView(View):
    def get(self, request, token):
        serializer = Serializer(settings.SECRET_KEY, expires_in=3600)
        try:
            info = serializer.loads(token)

            # 获取用户对象
            user = models.User.objects.get(id=info['reg_user_id'])
            # 激活用户
            user.is_active = 1
            user.save()

            # 跳转到登页面
            return redirect(reverse('user:login'))
        except SignatureExpired:
            return HttpResponse('激活链接已失效')


class LogoutView(LoginRequiredMixin, View):
    '处理退出登陆视图'
    def get(self, request):
        '清除用户的session信息'
        auth.logout(request)

        return redirect(reverse('goods:index'))



class UserInfoView(LoginRequiredMixin, View):
    '用户中心-信息页视图类'
    def get(self, request):
        # 获取用户信息
        address = models.Address.objects.get_default_address(request.user)

        # 获取使用django-redis获取redis连接
        conn = get_redis_connection('default')

        # 获取用户最新浏览的5个商品的id
        sku_ids = conn.lrange(f'history_{request.user.id}', 0, 4)

        # 从数据库中查询用户浏览的商品的具体信息
        goods_list = []
        for id in sku_ids:
            goods = goods_model.GoodsSKU.objects.get(id=id)
            goods_list.append(goods)

        return render(request, 'user/user_center_info.html', {'page': 'user', 'address': address, 'goods_list': goods_list})


class OrderView(LoginRequiredMixin, View):
    '用户中心-订单详情类'
    def get(self, request, page=1):
        '显示用户订单信息页面'
        orders = OrderInfo.objects.filter(user=request.user).order_by('-create_time')

        # 分页
        paginator = Paginator(orders, 1)

        # 获取第page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1
        order_page = paginator.page(page)
        # todo: 进行页码的控制，页面上最多显示5个页码
        # 1.总页数小于5页，页面上显示所有页码
        # 2.如果当前页是前3页，显示1-5页
        # 3.如果当前页是后3页，显示后5页
        # 4.其他情况，显示当前页的前2页，当前页，当前页的后2页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        return render(request, 'user/user_center_order.html', {'orders': orders,
                                                               'order_page': order_page,
                                                               'pages': pages,
                                                               'page': 'order',
                                                               })


class AddressView(View):
    '用户中心-地址信息页面'
    def get(self, request):
        '显示用户中心-信息页面'
        # 获取用户的地址记录
        address = models.Address.objects.get_default_address(request.user)

        # 收货地址信息表单
        form = AddressInfoForm()

        return render(request, 'user/user_center_site.html', {'page': 'address', 'address': address, 'form': form})

    def post(self, request):
        '处理添加地址请求'
        # 使用modelform验证数据
        form = AddressInfoForm(request.POST)

        # 验证表单数据
        if form.is_valid():
            # 添加地址
            models.Address.objects.create(
                user=request.user,
                receiver=form.cleaned_data.get('receiver'),
                addr=form.cleaned_data.get('addr'),
                zip_code=form.cleaned_data.get('zip_code'),
                phone=form.cleaned_data.get('phone'),
                is_default=True
            )
            return redirect(to='user:address')
        else:
            address = models.Address.objects.get_default_address(request.user)
            return render(request, 'user/user_center_site.html', {'page': 'adderss', 'address': address, 'form': form})