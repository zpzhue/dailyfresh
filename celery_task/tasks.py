from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
from django.template import loader


# 在任务处理者一端加这几句
import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
# django.setup()
from goods import models

# 创建celery的实例对象
app = Celery('celery_task', broker='redis://47.107.176.243:6379/3')

@app.task
def send_register_active_mail(to_mail, username, token):
    'celery异步发送邮件'
    # 组织邮件信息
    subject = '天天生鲜欢迎信息'
    message = ''
    sender = settings.EMAIL_FROM
    recive = [to_mail]
    html_message = f'''
    <h1>{username}, 欢迎您成为天天生鲜注册会员</h1>
    请点击下面链接激活您的账户<br/>
    <a href="http://127.0.0.1:8000/user/active/{token}">
        http://127.0.0.1:8000/user/active/{token}
    </a>'''
    send_mail(subject, message, sender, recive, html_message=html_message)


@app.task
def generic_static_index_html():
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
               'index_promotion_goods': index_promotion_goods}

    # 使用模板
    # 1. 加载模板文件，返回一个模板对象
    template = loader.get_template('goods/static_index.html')

    # 2. 渲染模板文件
    static_html = template.render(context)

    # 生成对应的首页htlm文件
    with open(os.path.join(settings.BASE_DIR, 'static/index.html'), 'w') as f:
        f.write(static_html)
