from django.urls import path,include
from . import views
urlpatterns = [
    path('index/', views.IndexView.as_view(), name='index'),                            # 首页
    path('detail/<int:goods_id>/', views.DetailView.as_view(), name='detail'),          # 商品详情页
    path('list/<int:type_id>/<int:page>/', views.GoodsListView.as_view(), name='list'), # 商品分类列表页
    path('search/', include('haystack.urls'))                                           # 全文检索框架
]
