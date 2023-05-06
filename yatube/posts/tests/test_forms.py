import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from ..models import Post, Group, Comment

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Тестовый комментарий'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.post.author)

    def test_authorized_user_create_post(self):
        """Проверка создания записи авторизированным клиентом."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовое описание',
            'group': self.group.id,
            'image': uploaded,
        }
        self.authorized_client.post(
            reverse('posts:post_create'), data=form_data, follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        post = Post.objects.latest('id')
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group.id, form_data.get('group'))
        self.assertEqual(post.image.name, 'posts/small.gif')

    def test_post_edit(self):
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Новое описание',
        }
        self.authorized_client.post(
            reverse('posts:post_edit',
                    kwargs={'post_id': '1'}), data=form_data, follow=True)
        self.post.refresh_from_db()
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(Post.objects.filter(text=form_data['text']).exists())

    def test_add_comment(self):
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый комментарий'
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': '1'}), data=form_data, follow=True)
        self.post.refresh_from_db()
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}
        ))
        self.assertFalse(Post.objects.filter(text=form_data['text']).exists())
