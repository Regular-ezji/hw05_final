import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse
from posts.models import Post, Group, Comment, Follow
from django import forms
from yatube.settings import POSTS_COUNT
from django.core.cache import cache
from http import HTTPStatus


User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
        )
        cls.user = User.objects.create_user(username='TestUser')
        cls.user_following = User.objects.create_user(
            username='TestFollowingUser'
        )
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded,
        )
        cls.comment = Comment.objects.create(
            text='Тестовый комментарий',
            post=cls.post,
            author=cls.user,
        )
        cls.follower = Follow.objects.create(
            author=cls.user_following,
            user=cls.user,
        )
        cls.followers_count = Follow.objects.count()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        cache.clear()

    def setUp(self) -> None:
        self.guest_client = Client()

    def asserts_with_first_obj(self, first_object):
        '''Тестирование первого объекта (поста)
           на странице'''
        post_text_0 = first_object.text
        post_group_0 = first_object.group.title
        post_image_0 = first_object.image
        page_obj_context_elements = {
            post_text_0: 'Тестовый пост',
            post_group_0: 'Тестовая группа',
            post_image_0: self.post.image,
        }
        for value, expected in page_obj_context_elements.items():
            with self.subTest(value=value):
                return self.assertEqual(value, expected)

    def test_urls_uses_correct_template(self) -> None:
        """URL-адрес использует соответствующий шаблон."""
        cache.clear()
        templates_url_names = {
            reverse('posts:index'):
            'posts/index.html',
            reverse('posts:group_list', args=[self.group.slug]):
            'posts/group_list.html',
            reverse('posts:profile', args=[self.post.author]):
            'posts/profile.html',
            reverse('posts:post_detail', args=[self.post.pk]):
            'posts/post_detail.html',
            reverse('posts:post_create'):
            'posts/create_post.html',
            reverse('posts:post_edit', args=[self.post.pk]):
            'posts/create_post.html',
            reverse('posts:access_denied'):
            'posts/access_denied.html'
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_create_post_show_correct_context(self) -> None:
        """Шаблон создания поста сформирован с правильным контекстом."""
        response = (self.authorized_client.get(
            reverse('posts:post_create'))
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(
                    value
                )
                self.assertIsInstance(form_field, expected)

    def test_edit_post_show_correct_context(self) -> None:
        """Шаблон редактирования поста сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', args=[self.post.pk])
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        if self.authorized_client == self.post.author:
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context.get('form').fields.get(
                        value
                    )
                    self.assertIsInstance(form_field, expected)

    def test_index_show_correct_context(self) -> None:
        '''Шаблон главной страницы сформирован
           с правильным контекстом'''
        cache.clear()
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        first_object = response.context['page_obj'][0]
        self.asserts_with_first_obj(first_object)

    def test_profile_show_correct_context(self) -> None:
        '''Шаблон страницы профиля сформирован
           с правильным контекстом'''
        response = self.authorized_client.get(
            reverse('posts:profile', args=[self.post.author])
        )
        first_object = response.context['page_obj'][0]
        self.asserts_with_first_obj(first_object)

    def test_group_list_show_correct_context(self) -> None:
        '''Шаблон страницы всех постов группы
           сформирован с правильным контекстом'''
        response = self.authorized_client.get(
            reverse('posts:group_list', args=[self.group.slug])
        )
        first_object = response.context['page_obj'][0]
        self.asserts_with_first_obj(first_object)

    def test_post_detail_show_correct_context(self) -> None:
        '''Шаблон страницы с детальным отображением поста
           сформирован с правильным контекстом'''
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(response.context.get('post'), self.post)

    def test_post_appears(self) -> None:
        '''При создании поста пост повяляется на главной странице,
        странице группы, в профиле пользователя'''
        cache.clear()
        responses = (
            self.authorized_client.get(
                reverse('posts:index')
            ),
            self.authorized_client.get(
                reverse('posts:group_list', args=[self.group.slug])
            ),
            self.authorized_client.get(
                reverse('posts:profile', args=[self.post.author])
            ),
        )
        for response in responses:
            first_object = response.context['page_obj'][0]
            self.assertEqual(first_object, self.post)

    def test_post_not_appears_wrong_group(self) -> None:
        '''При создании пост не появляется в не предназначенной
        для него группе'''
        group_two = Group.objects.create(
            title='Тестовая группа №2',
            slug='test-slug-two',
        )
        Post.objects.create(
            text='Тестовый пост №2',
            author=self.user,
            group=group_two,
        )
        response = self.authorized_client.get(
            reverse('posts:group_list', args=[group_two.slug])
        )
        first_object = response.context['page_obj'][0]
        self.assertNotEqual(first_object, self.post)

    def test_cache(self) -> None:
        '''Проверка работы кэша'''
        cache_test_post = Post.objects.create(
            text='Тестовый пост для проверки кэша',
            author=self.user,
        )
        response_before = self.authorized_client.get(
            reverse('posts:index')
        )
        cache_test_post.delete()
        posts_before_cache_clear = response_before.content
        cache.clear()
        response_after = self.authorized_client.get(
            reverse('posts:index')
        )
        posts_after_cache_clear = response_after.content
        self.assertNotEqual(posts_before_cache_clear, posts_after_cache_clear)

    def test_error_page(self) -> None:
        '''Проверка страницы 404: она отдаёт кастомный шаблон'''
        response = self.client.get('/nonexist-page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        template = 'core/404.html'
        self.assertTemplateUsed(response, template)

    def test_user_can_subscribe_other_users(self) -> None:
        '''Авторизованный пользователь может подписываться
           на других пользователей'''
        ONE_MORE_FOLLOWER = 1
        post_data = {
            'author': self.user_following,
            'user': self.user,
        }
        response = self.authorized_client.post(
            reverse('posts:profile_follow', args=[self.user_following]),
            data=post_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse('posts:profile', args=[self.user_following])
        )
        self.assertEqual(
            Follow.objects.count(),
            self.followers_count + ONE_MORE_FOLLOWER
        )

    def test_user_can_delete_other_users_from_following_users(self) -> None:
        '''Авторизованный пользователь может отписываться
           от других пользователей'''
        ONE_LESS_FOLLOWER = 1
        response = self.authorized_client.post(
            reverse('posts:profile_unfollow', args=[self.user_following])
        )
        self.assertRedirects(
            response, reverse('posts:profile', args=[self.user_following])
        )
        self.assertEqual(
            Follow.objects.count(), self.followers_count - ONE_LESS_FOLLOWER
        )

    def test_post_appears_on_following_page(self) -> None:
        '''Новая запись пользователя появляется
           в ленте тех, кто на него подписан'''
        test_post = Post.objects.create(
            text='Тестовый пост',
            author=self.user_following
        )
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object, test_post)

    def test_post_not_appears_on_following_page(self) -> None:
        '''Новая запись пользователя не появляется
           в ленте тех, кто на него не подписан'''
        test_post = Post.objects.create(
            text='Тестовый пост',
            author=self.user,
        )
        Post.objects.create(
            text='Тестовый пост',
            author=self.user_following,
        )
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        first_object = response.context['page_obj'][0]
        self.assertNotEqual(first_object, test_post)


class PaginatorViewsTest(TestCase):
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
        more_posts_count = 3
        test_posts_count = POSTS_COUNT + more_posts_count
        cls.post = Post.objects.bulk_create(
            [
                Post(
                    text=f'Тестовый пост №{i}',
                    author=cls.user,
                )
                for i in range(test_posts_count)
            ]
        )

    def setUp(self) -> None:
        self.guest_client = Client()

    def test_first_page_contains_ten_records(self) -> None:
        '''Проверка наличия 10 записей на первой странице'''
        cache.clear()
        responses_tuple = {
            self.client.get(
                reverse('posts:index')
            ),
            self.client.get(
                reverse('posts:group_list', args=[self.group.slug])
            ),
            self.client.get(
                reverse('posts:profile', args=[self.user])
            ),
        }
        for response in responses_tuple:
            with self.subTest(response=response):
                self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_records(self) -> None:
        '''Проверка наличия 3х записей на первой странице'''
        responses_tuple = {
            self.client.get(
                reverse('posts:index') + '?page=2'
            ),
            self.client.get(
                reverse('posts:group_list', args=[self.group.slug])
                + '?page=2'
            ),
            self.client.get(
                reverse('posts:profile', args=[self.user])
                + '?page=2'
            ),
        }
        for response in responses_tuple:
            with self.subTest(response=response):
                self.assertEqual(len(response.context['page_obj']), 3)
