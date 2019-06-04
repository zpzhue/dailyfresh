from haystack import indexes
from goods.models import GoodsSKU


class GoodsSKUIndex(indexes.SearchIndex, indexes.Indexable):
    '指定对于某个类的某些数据建立索引'

    # 索引字段 use_template=True指定根据表中的哪些字段建立索引文件的说明放在一个文件中
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        # 返回要检索数据的模型类
        return GoodsSKU

    def index_queryset(self, using=None):
        '建立索引的数据'
        return self.get_model().objects.all()