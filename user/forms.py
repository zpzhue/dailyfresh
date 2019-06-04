import re

from django import forms
from django.forms import ValidationError
from . import models



class UserForm(forms.Form):
    username = forms.CharField(min_length=4,
                               label='用户名',
                               widget=forms.TextInput(attrs={'class': 'input is-hovered',
                                                             'placeholder': '输入你的用户名'}),
                               error_messages={'required': '请输入用户名'})
    password = forms.CharField(label='密码',
                               widget=forms.PasswordInput(attrs={'class': 'input is-hovered',
                                                                 'placeholder': '输入你的密码'}),
                               error_messages={'required': '请输入密码'})


class RegForm(UserForm):

    cf_passwd = forms.CharField(label='确认密码',
                               widget=forms.PasswordInput(attrs={'class': 'input is-hovered',
                                                             'placeholder': '再次确认你的密码'}),
                                error_messages={'required': '请再次输入密码'})
    email = forms.EmailField(label='邮箱',
                              widget=forms.EmailInput(attrs={'class': 'input is-hovered',
                                                             'placeholder': '输入您的邮箱'}),
                              error_messages={'invalid': '请输入正确的邮箱地址','required': '请输入邮箱地址'})

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        cf_passwd = self.cleaned_data.get(('cf_passwd'))

        if models.User.objects.filter(username=username):
            raise ValidationError({'username': '用户名已经存在'})

        if password == cf_passwd:
            return self.cleaned_data
        else:
            raise ValidationError({'cf_passwd': '两次输入的密码不一致'})



class RegisterModelForm(forms.ModelForm):
    confirm_pwd = forms.CharField(max_length=20, label='确认密码:', widget=forms.PasswordInput(attrs={'id': 'cpwd', 'name': 'cpwd'}))
    allow = forms.CharField(label='同意“天天生鲜用户使用协议”', widget=forms.CheckboxInput(attrs={'id': 'allow', 'value': 'on'}))
    class Meta:
        model = models.User
        fields = ['username', 'password', 'confirm_pwd', 'email', 'allow']

        widgets = {
            'username': forms.TextInput(attrs={'id': 'user_name', 'name': 'user_name'}),
            'password': forms.PasswordInput(attrs={'id': 'pwd', 'name': 'pwd'}),
            'email': forms.TextInput(attrs={'id': 'email', 'name': 'email'}),
        }
        labels = {
            'username': '用户名:',
            'password': '密码:',
            'email': '邮箱:'
        }
    #
    # def clean_allow(self):
    #     print('clean_allow')
    #     allow = self.cleaned_data.get('allow')
    #     print(allow)
    #     if allow != 'on':
    #         raise ValidationError({'allow': '请勾选同意该协议'})
    #     else:
    #         return self.allow

    def clean(self):
        print('clena data ...')
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        confirm_pwd = self.cleaned_data.get(('confirm_pwd'))
        allow = self.cleaned_data.get('allow')

        if not allow:
            raise ValidationError({'allow': '请勾选同意协议'})

        if models.User.objects.filter(username=username):
            raise ValidationError({'username': '用户名已经存在'})

        if password == confirm_pwd:
            return self.cleaned_data
        else:
            raise ValidationError({'password': '两次输入的密码不一致'})

class LoginModelForm(forms.ModelForm):
    class Meta:
        model = models.User
        fields = ['username', 'password']

        widgets = {
            'username': forms.TextInput(attrs={'class': 'name_input', 'placeholder': '请输入用户名'}),
            'password': forms.PasswordInput(attrs={'class': 'pass_input', 'placeholder': '请输入密码'}),
        }
        labels = {
            'username': '用户名:',
            'password': '密码:',
        }


class AddressInfoForm(forms.ModelForm):
    class Meta:
        model = models.Address
        fields = ['receiver', 'addr', 'zip_code', 'phone']

        labels = {
            'receiver': '收件人',
            'addr': '详细地址',
            'zip_code': '邮编',
            'phone': '手机'
        }

        widgets = {
            'addr': forms.Textarea(attrs={'class': 'site_area'})
        }

    def clean_phone(self):
        '校验手机号码'
        phone = self.cleaned_data.get('phone')

        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
            raise ValidationError(('手机格式不正确'), code='phone')
        else:
            return phone