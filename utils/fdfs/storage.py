from django.conf import settings
from django.core.files.storage import Storage
from fdfs_client.client import get_tracker_conf, Fdfs_client

class FDFSStorage(Storage):
    '自定义文件存储类'
    def __init__(self, client_conf=None, base_url=None):
        self.client_conf = client_conf if client_conf else settings.FDFS_CLIENT_CONF
        self.base_url = base_url if base_url else settings.FDFS_URL

    def _open(self, name, mode='rb'):
        '打开文件时使用'
        pass

    def _save(self, name, content):
        '''
        保存文件时使用
        :param name: 你选择上传文件的名字
        :param content: 包含你上传文件内容的File对象
        :return:
        '''

        # 创建Fdfs_client对象
        client = Fdfs_client(get_tracker_conf(self.client_conf))

        # 上传文件到fast_dfs文件系统
        result = client.upload_by_buffer(content.read())

        # retsult
        #   {
        #       'Group name': b'group1',
        #       'Remote file_id': b'group1/M00/00/00/rBLk_lxmOXeAcMArAAFNqduP814053.png',
        #       'Status': 'Upload successed.',
        #       'Local file name': './utils/a.png',
        #       'Uploaded size': '83.42KB',
        #       'Storage IP': b'47.107.176.243'
        #   }

        if result.get('Status') != 'Upload successed.':
            # 上传失败
            raise Exception('上传文件到fast_fdfs失败')

        # 获取返回的文件id
        file_id = result.get('Remote file_id').decode()

        return file_id


    def exists(self, name):
        'Django 判断文件名是否可用'
        return False

    def url(self, name):
        '返回访问文件的路径'
        return self.base_url + name
