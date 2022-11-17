import shutil
import tempfile

from django.contrib.auth import get_user_model
from posts.forms import PostForm
from posts.models import Post, Group, Comment
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.shortcuts import get_object_or_404


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


class PostFormTests(TestCase):
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
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
        )
        cls.form = PostForm()
        cls.posts_count = Post.objects.count()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self) -> None:
        self.guest_client = Client()

    def test_create_post(self) -> None:
        '''Тест формы создания поста'''
        ONE_MORE_POST = 1
        form_data = {
            'text': 'Тестовый пост',
            'group': self.group.id,
            'image': self.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse('posts:profile', args=[self.user])
        )
        self.assertEqual(
            Post.objects.count(), self.posts_count + ONE_MORE_POST
        )
        self.assertEqual(
            response.context.get('post').author, self.post.author
        )
        self.assertEqual(
            response.context.get('post').group, self.post.group
        )

    def test_post_edit(self) -> None:
        '''Тест формы редактирования поста'''
        form_data = {
            'text': 'Отредактированный тестовый пост',
            'group': self.post.group.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=[self.post.pk]),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse('posts:post_detail', args=[self.post.pk])
        )
        self.assertEqual(
            Post.objects.count(), self.posts_count
        )
        last_obj = get_object_or_404(Post, pk=self.post.pk)
        fields_dict = {
            last_obj.text: form_data['text'],
            last_obj.author: self.user,
            last_obj.group: self.post.group
        }
        for value, expected in fields_dict.items():
            with self.subTest(value=value):
                self.assertEqual(value, expected)
        self.assertEqual(
            response.context.get('post').author, self.post.author
        )
        self.assertEqual(
            response.context.get('post').group, self.post.group
        )

    def test_add_comment(self) -> None:
        '''Проверка формы комментария'''
        self.comment = Comment.objects.create(
            text='Тестовый комментарий',
            post=self.post,
            author=self.user
        )
        self.comments_count = Comment.objects.count()
        ONE_MORE_COMMENT = 1
        form_data = {
            'text': 'Тестовый комментарий'
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=[self.post.pk]),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse('posts:post_detail', args=[self.post.pk])
        )
        self.assertEqual(
            Comment.objects.count(), self.comments_count + ONE_MORE_COMMENT
        )
