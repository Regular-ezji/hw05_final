from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache
from http import HTTPStatus
from posts.models import Post, Group

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
        )
        cls.user = User.objects.create_user(username='TestUser')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
        )
        cache.clear()

    def setUp(self) -> None:
        self.guest_client = Client()
        cache.clear()

    def test_non_authorized_urls_are_available(self) -> None:
        '''Проверка доступа к страницам доступным всем пользователям'''
        urls_tuple: tuple = (
            reverse('posts:index'),
            reverse('posts:group_list', args=[self.group.slug]),
            reverse('posts:profile', args=[self.post.author]),
            reverse('posts:post_detail', args=[self.post.pk]),
        )
        for page_url in urls_tuple:
            response = self.guest_client.get(page_url)
            error: str = f'Ошибка: Страница по адресу {page_url} недоступна'
            self.assertEqual(response.status_code, HTTPStatus.OK, error)

    def test_non_authorized_redirect(self) -> None:
        '''Проверка редиректа с недоступных неавторизованному пользователю
           старниц на страницу авторизации'''
        urls_dict = {
            reverse('posts:post_create'): reverse(
                'auth:login'
            ) + '?next=' + reverse(
                'posts:post_create'
            )
        }
        for page_url, redirect_url in urls_dict.items():
            response = self.guest_client.get(page_url, follow=True)
            with self.subTest(page_url=page_url):
                self.assertRedirects(response, redirect_url)

    def test_author_access(self) -> None:
        '''Проверка доступности страниц только для конкретного пользователя'''
        urls_tuple = (
            reverse('posts:post_edit', args=[self.post.pk])
        )
        for page_url in urls_tuple:
            with self.subTest(page_url=page_url):
                response = self.authorized_client.get(page_url)
                if self.authorized_client == self.post.author:
                    error: str = f'Ошибка: Страница по адресу {page_url}'
                    +'недоступна'
                    self.assertEqual(
                        response.status_code, HTTPStatus.OK, error
                    )

    def test_urls_uses_correct_template(self) -> None:
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user}/': 'posts/profile.html',
            f'/posts/{self.post.pk}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{self.post.pk}/edit/': 'posts/create_post.html',
            '/access_denied/': 'posts/access_denied.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
