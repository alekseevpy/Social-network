import tempfile
import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile

from django import forms
from posts.models import Post, Group, Follow

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

POSTS_COUNT = 13
POSTS_SHOWED = 10
POSTS_SHOWED_SECOND_PAGE = 3


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='auth')
        cls.second_user = User.objects.create_user(username='auth2')
        cls.third_user = User.objects.create_user(username='auth3')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
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

        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.second_authorized_client = Client()
        self.third_authorized_client = Client()
        self.authorized_client.force_login(self.post.author)
        self.second_authorized_client.force_login(self.second_user)
        self.third_authorized_client.force_login(self.third_user)
        cache.clear()

    def test_guest_new_post(self):
        form_data = {
            'text': 'Пост от неавторизованного пользователя',
            'group': self.group.id
        }
        self.guest_client.post(
            reverse('posts:post_create'), data=form_data, follow=True
        )
        self.assertFalse(Post.objects.filter(
            text='Пост от неавторизованного пользователя').exists())

    def test_index_page_is_cached(self):
        Post.objects.create(author=self.user,
                            group=self.group,
                            text='Тестируем кэширование'
                            )
        response1 = self.client.get(reverse('posts:index')).content
        Post.objects.filter(id=self.post.id).delete()
        response2 = self.client.get(reverse('posts:index')).content
        self.assertEqual(response1, response2)
        cache.clear()
        response3 = self.client.get(reverse('posts:index')).content
        self.assertNotEqual(response1, response3)

    def test_guest_new_post(self):
        form_data = {
            'text': 'Пост от неавторизованного пользователя',
            'group': self.group.id
        }
        self.guest_client.post(
            reverse('posts:post_create'), data=form_data, follow=True
        )
        self.assertFalse(Post.objects.filter(
            text='Пост от неавторизованного пользователя').exists())

    def test_pages_uses_correct_template(self):
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            (reverse('posts:group_list', kwargs={'slug': 'test-slug'})
             ): 'posts/group_list.html',
            (reverse('posts:profile', kwargs={'username': 'auth'})
             ): 'posts/profile.html',
            (reverse('posts:post_edit', kwargs={'post_id': '1'})
             ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            (reverse('posts:post_detail', kwargs={'post_id': '1'})
             ): 'posts/post_detail.html',
            reverse('posts:follow_index'): 'posts/follow.html'
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_group_list_profile_follow_show_correct_context(self):
        pages_names_templates = {
            reverse('posts:index'): 'page_obj',
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}
                    ): 'page_obj',
            reverse('posts:profile', kwargs={'username': 'auth'}): 'page_obj',
            reverse('posts:post_detail', kwargs={'post_id': '1'}): 'post'
        }

        for reverse_name, context in pages_names_templates.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                if context != 'post':
                    post = response.context.get(context)[0]
                else:
                    post = response.context.get(context)
                self.assertEqual(
                    post.text, 'Тестовый пост')
                self.assertEqual(post.group.title, 'Тестовая группа')
                self.assertEqual(post.author.username, 'auth')
                self.assertTrue('/media/posts/small' in post.image.url)
                self.assertEqual(post.group.slug, 'test-slug')
                self.assertEqual(post.group.description, 'Тестовое описание')

    def test_post_detail_page_show_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': '1'})
        )
        self.assertEqual(response.context.get('post').author.username, 'auth')
        self.assertEqual(response.context.get('post').text, 'Тестовый пост')
        self.assertEqual(response.context.get('post').group.title,
                         'Тестовая группа')

    def test_update_post_page_show_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': '1'})
        )
        form_fields = {'text': forms.fields.CharField,
                       'group': forms.models.ModelChoiceField
                       }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_create_post_page_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {'text': forms.fields.CharField,
                       'group': forms.fields.ChoiceField,
                       }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_follow_and_unfollow(self):
        self.second_authorized_client.get(reverse(
            'posts:profile_follow', kwargs={'username': self.user.username}
        ))
        follow = Follow.objects.get(
            user=self.second_user.id,
            author=self.user.id
        )
        self.assertEqual(follow.author, self.user)
        self.assertEqual(follow.user, self.second_user)

        self.second_authorized_client.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.user.username})
        )
        follow = Follow.objects.filter(
            user=self.second_user.id,
            author=self.user.id
        ).exists()
        self.assertFalse(follow)

    def test_new_post_in_follow_page(self):
        Post.objects.create(text='Test follow post', author=self.user)
        Post.objects.create(
            text='Test follow post from NoName',
            author=self.second_user,
        )
        self.second_authorized_client.get(reverse(
            'posts:profile_follow', kwargs={'username': self.user.username}))
        self.third_authorized_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.second_user.username})
        )
        second_response = self.second_authorized_client.get(reverse(
            'posts:follow_index'))
        third_response = self.third_authorized_client.get(reverse(
            'posts:follow_index'))
        post_exist = second_response.context.get('page_obj')[0]
        post_unexist = third_response.context.get('page_obj')[0]
        self.assertEqual(post_exist.text, 'Test follow post')
        self.assertNotEqual(post_unexist.text, 'Test follow post')


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.authorized_client = Client()
        cls.user = User.objects.create(username='auth')
        cls.group = Group.objects.create(title='Тестовая группа',
                                         description='Тестовое описание',
                                         slug='test-slug'
                                         )
        posts = []
        for i in range(POSTS_COUNT):
            posts.append(Post(author=cls.user,
                              group=cls.group,
                              text=f'Тестовый текст {i}'))
        Post.objects.bulk_create(posts)

    def setUp(self):
        self.guest_client = Client()
        cache.clear()

    def test_first_page_contains_ten_records(self):
        templates_pages_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/group_list.html': reverse(
                'posts:group_list', kwargs={'slug': 'test-slug'}
            ),
            'posts/profile.html': reverse(
                'posts:profile', kwargs={'username': 'auth'}
            )
        }
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(template=template):
                response = self.client.get(reverse_name)
                self.assertEqual(
                    len(response.context['page_obj']), POSTS_SHOWED
                )

    def test_second_page_contains_three_records(self):
        templates_pages_names = {
            'posts/index.html': reverse('posts:index') + '?page=2',
            'posts/group_list.html': reverse(
                'posts:group_list', kwargs={'slug': 'test-slug'}
            ) + '?page=2',
            'posts/profile.html': reverse(
                'posts:profile', kwargs={'username': 'auth'}
            ) + '?page=2'
        }
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(template=template):
                response = self.client.get(reverse_name)
                self.assertEqual(
                    len(response.context['page_obj']), POSTS_SHOWED_SECOND_PAGE
                )
