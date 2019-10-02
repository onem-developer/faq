import jwt
import requests

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View as _View
from onemsdk.schema.v1 import (
    Response,
    Menu, MenuItem, MenuItemType, MenuMeta, MenuItemFormItem,
    Form, FormItem, FormItemType, FormMeta, MenuFormItemMeta
)

from .models import Faq
from .helpers import truncatechars


class View(_View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *a, **kw):
        return super(View, self).dispatch(*a, **kw)

    def get_user(self):
        # return User.objects.filter()[0]
        token = self.request.headers.get('Authorization')
        if token is None:
            raise PermissionDenied

        data = jwt.decode(token.replace('Bearer ', ''), key='87654321')
        user, created = User.objects.get_or_create(
                id=data['sub'], username=str(data['sub']),
                is_staff=data['is_admin']
        )
        headers = {
            'X-API-KEY': settings.APP_APIKEY_POC,
            'Content-Type': 'application/json'
        }
        std_url = settings.RESTD_API_URL_POC.format(
            endpoint='users/{}'
        ).format(user.id)
        response = requests.get(url=std_url, headers=headers)
        if response.status_code == 200 and created:
            response = response.json()
            user_names = ['first_name', 'last_name']
            for user_name in user_names:
                user_data = response.get(user_name)
                if user_data:
                    setattr(user, user_name, user_data)
        user.save()
        return user

    def to_response(self, content):
        response = Response(content=content)
        return HttpResponse(response.json(),
                            content_type='application/json')


class HomeView(View):
    http_method_names = ['get']

    def get(self, request):
        menu_items = [
            MenuItem(description='Search',
                     method='GET',
                     path=reverse('search_wizard'))
        ]
        user = self.get_user()
        if user.is_staff:
            menu_items.insert(0, MenuItem(description='Add F.A.Q.',
                                          method='GET',
                                          path=reverse('add_faq')))
        faqs = Faq.objects.all()
        # sort into categories if there are at least 3 categories with 2 items
        # and no qa without a category
        categories_set = set([faq.category for faq in faqs])
        if not None in categories_set:
            categories_data = {}
            for faq in faqs:
                if not categories_data.get(faq.category):
                    categories_data[faq.category] = 1
                else:
                    categories_data[faq.category] += 1
            if len(categories_data.items()) > 2 and \
            len(list(filter(lambda x: x > 1, categories_data.values()))):
                menu_items.insert(0, MenuItem(description='Select a category'))
                for category, count in categories_data.items():
                    menu_items.append(MenuItem(
                        description='{category} ({count})'.format(
                            category=category.capitalize(), count=count
                        ), method='GET',
                        path=reverse('faqs', args=(category,))
                    ))
        else:
            for faq in faqs:
                menu_items.append(
                    MenuItem(description=truncatechars(faq.question, 15),
                             method='GET',
                             path=faq.get_absolute_url())
                )
        # check to see if we have notifications set in cache
        if cache.get('qa_added'):
            menu_items.insert(0, MenuItem(
                description='Q.A. added successfully')
            )
            cache.delete('qa_added')
        if cache.get('qa_edited'):
            menu_items.insert(0, MenuItem(
                description='Q.A. edited successfully'
            ))
            cache.delete('qa_edited')
        if cache.get('qa_deleted'):
            menu_items.insert(0, MenuItem(
                description='Q.A. deleted successfully'
            ))
            cache.delete('qa_deleted')
        content = Menu(body=menu_items, header='menu')
        return self.to_response(content)


class SearchView(View):
    http_method_names = ['get', 'post']

    def get(self, request):
        form_items = [
            FormItem(type=FormItemType.string, name='keyword',
                     description='Send keywords to search',
                     header='search', footer='Reply keywords')
        ]
        content = Form(body=form_items, method='POST',
                       path=reverse('search_wizard'),
                       meta=FormMeta(skip_confirmation=True))
        return self.to_response(content)

    def post(self, request):
        keyword = request.POST['keyword']
        faqs = Faq.objects.filter(Q(question__icontains=keyword) | Q(answer__icontains=keyword))
        if not faqs:
            form_items = [
                FormItem(type=FormItemType.string, name='keyword',
                         description='No results found. Please try again '
                                     'with different keywords',
                         header='search', footer='Reply keywords')
            ]
            content = Form(body=form_items, method='POST',
                           path=reverse('search_wizard'),
                           meta=FormMeta(skip_confirmation=True))
        else:
            menu_items = []
            for faq in faqs:
                menu_items.append(MenuItem(
                    description=truncatechars(faq.question, 30),
                    method='GET', path=faq.get_absolute_url()
                ))
            content = Menu(body=menu_items,
                           header='search: {}'.format(keyword))
        return self.to_response(content)


class FaqsView(View):
    http_method_names = ['get']

    def get(self, request, category):
        faqs = Faq.objects.filter(category=category)
        menu_items = []
        for faq in faqs:
            menu_items.append(MenuItem(
                description=truncatechars(faq.question, 30),
                method='GET', path=faq.get_absolute_url()
            ))

        content = Menu(body=menu_items, header='category: {}'.format(category))
        return self.to_response(content)


class FaqView(View):
    http_method_names = ['get']

    def get(self, request, id):
        try:
            faq = Faq.objects.filter(id=id)[0]
        except IndexError:
            return self.to_response(Menu([
                MenuItem(description='F.A.Q. unavailable')
            ], header='Unavailable', footer='Reply MENU'))

        menu_items = [
            MenuItem(description=faq.question),
            MenuItem(description=faq.answer)
        ]
        header = 'details'
        footer = 'Reply BACK/MENU'
        user = self.get_user()
        if user.is_staff:
            menu_items.append(MenuItem(
                description='Edit/Delete',
                method='GET', path=reverse('edit_faq', args=(faq.id, 'edit'))
            ))
            header = 'admin menu'
            footer = None
        content = Menu(body=menu_items, header=header, footer=footer)
        return self.to_response(content)


class AddFaqView(View):
    http_method_names = ['get', 'post']

    def get(self, request):
        form_items = [
            FormItem(type=FormItemType.string, name='category',
                     description='Send the category',
                     header='category', footer='Reply text/SKIP'),
            FormItem(type=FormItemType.string, name='question',
                     description='Send the question',
                     header='add question', footer='Reply text'),
            FormItem(type=FormItemType.string, name='answer',
                     description='Send the answer',
                     header='add answer', footer='Reply text'),
        ]

        content = Form(body=form_items, method='POST',
                       path=reverse('add_faq'),
                       meta=FormMeta(skip_confirmation=True))
        return self.to_response(content)

    def post(self, request):
        category = request.POST['category']
        if category.lower() == 'skip':
            category = None
        faq_create = Faq.objects.create(
            category=category.lower(),
            question=request.POST['question'],
            answer=request.POST['answer']
        )
        faq_create.save()
        cache.set('qa_added', True)
        return HttpResponseRedirect(reverse('home'))


class EditFaqView(View):
    http_method_names = ['get', 'post', 'delete']

    def get(self, request, **kwargs):
        try:
            faq = Faq.objects.filter(id=kwargs['id'])[0]
        except IndexError:
            return self.to_response(Menu([
                MenuItem(description='F.A.Q. unavailable')
            ], header='Unavailable', footer='Reply MENU'))

        menu_items = [
            MenuItem(
                description='Edit category: {}'.format(truncatechars(faq.category, 30)),
                method='POST',
                path=reverse('edit_faq', args=(faq.id, 'category'))
            ),
            MenuItem(
                description='Edit question: {}'.format(truncatechars(faq.question, 30)),
                method='POST',
                path=reverse('edit_faq', args=(faq.id, 'question'))
            ),
            MenuItem(
                description='Edit answer: {}'.format(truncatechars(faq.answer, 30)),
                method='POST',
                path=reverse('edit_faq', args=(faq.id, 'answer'))),
            MenuItem(
                description='Delete',
                method='DELETE',
                path=reverse('edit_faq', args=(faq.id, 'delete')))
        ]
        content = Menu(body=menu_items, header='edit/delete')
        return self.to_response(content)

    def post(self, request, **kwargs):
        faq = Faq.objects.filter(id=kwargs['id'])[0]
        qa_type = kwargs['type']
        qa_content = getattr(faq, qa_type)
        # check if we are at the beginning of the wizard
        if not request.POST:
            form_items = [
                FormItem(type=FormItemType.string, name=qa_type,
                         description='\n'.join([
                             'Current {qa_type}: {qa_content}'.format(
                                 qa_type=qa_type, qa_content=qa_content
                             ),
                             'Send text to edit'
                         ]),
                         header='edit {qa_type}'.format(qa_type=qa_type),
                         footer='Reply with text/BACK')
            ]
            content = Form(body=form_items, method='POST',
                           path=reverse(
                               'edit_faq', args=(kwargs['id'], qa_type)
                           ),
                           meta=FormMeta(skip_confirmation=True))
            return self.to_response(content)
        setattr(faq, qa_type, request.POST[qa_type].lower())
        faq.save()
        cache.set('qa_edited', True)
        return HttpResponseRedirect(reverse('home'))

    def delete(self, request, **kwargs):
        faq = Faq.objects.filter(id=kwargs['id'])[0]
        faq.delete()
        cache.set('qa_deleted', True)
        return HttpResponseRedirect(reverse('home'))
