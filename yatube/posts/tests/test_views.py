import shutil
import tempfile
from time import sleep

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Follow, Group, Post, User
from posts.views import LIST_LIMIT

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
TEST_POST_COUNT = 13
REMAINDER = TEST_POST_COUNT - LIST_LIMIT


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        for k in range(1, 3):
            Group.objects.create(
                title=f'Тестовая группа #{k}',
                slug=f'test-slug{k}',
                description=f'Тестовое описание группы #{k}',
            )
        cls.group = Group.objects.get(pk=1)
        for i in range(1, TEST_POST_COUNT + 1):
            sleep(0.01)  # Задержка для гарантированного порядка постов
            Post.objects.create(
                author=cls.user,
                group=cls.group,
                text=f'Тестовый пост #{i}'
            )
        cls.post = Post.objects.get(pk=1)
        cls.user2 = User.objects.create_user(username='another_author')
        cls.follower = User.objects.create_user(username='follower')
        cls.not_follower = User.objects.create_user(username='not follower')
        Follow.objects.create(user=cls.follower, author=cls.user)
        Follow.objects.create(user=cls.not_follower, author=cls.user2)
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)
        self.post_id = PostPagesTests.post.id
        self.pages_for_tests = (
            # Первые 3 страницы из кортежа ниже содержат список постов
            ('posts:index', {}, 'posts/index.html'),
            ('posts:profile', {'username': 'auth'}, 'posts/profile.html'),
            ('posts:group_list', {'slug': 'test-slug1'},
                'posts/group_list.html'),
            ('posts:post_detail', {'post_id': self.post_id},
                'posts/post_detail.html'),
            ('posts:post_edit', {'post_id': self.post_id},
                'posts/create_post.html'),
            ('posts:post_create', {}, 'posts/create_post.html'),
        )
        cache.clear()

    def test_pages_use_correct_templates(self):
        """.Проверяем правильность использования шаблонов для имён ссылок."""
        for url_name, kwargs, template in self.pages_for_tests:
            with self.subTest(url_name=url_name):
                response = self.authorized_client.get(
                    reverse(url_name, kwargs=kwargs))
                self.assertTemplateUsed(response, template)

    def test_context_for_pages_with_post_lists(self):
        """.Проверяем посты в списках и paginator-ы."""
        # Проверяем первые 3 страницы из кортежа - они со списком постов
        for url, kwargs, _ in self.pages_for_tests[:3]:
            with self.subTest(url_name=url):
                # Сначала проверяем paginator
                response = self.guest_client.get(reverse(url, kwargs=kwargs))
                self.assertEqual(
                    len(response.context.get('page_obj')), LIST_LIMIT)
                response = self.guest_client.get(
                    reverse(url, kwargs=kwargs) + '?page=2')
                self.assertEqual(
                    len(response.context.get('page_obj')), REMAINDER)
                # Затем на 2-й странице проверяем 2-й пост с конца
                object_2 = response.context.get('page_obj')[-2]
                self.assertEqual(object_2.author.username, 'auth')
                self.assertEqual(object_2.group.title, 'Тестовая группа #1')
                self.assertEqual(object_2.text, 'Тестовый пост #2')

    def test_post_detail_show_correct_context(self):
        """.Проверяем: контекст /posts/id/ содержит ожидаемые значения."""
        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post_id})
        )
        post = response.context.get('post')
        self.assertEqual(post.author.username, 'auth')
        self.assertEqual(post.group.title, 'Тестовая группа #1')
        self.assertEqual(post.text, 'Тестовый пост #1')

    def test_post_form_uses_correst_context(self):
        """.Проверяем правильность контекста на страницах с формами."""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        forms_for_test = (
            ('posts:post_edit', {'post_id': self.post_id},
                'posts/create_post.html'),
            ('posts:post_create', {}, 'posts/create_post.html'),
        )
        for url, kwargs, _ in forms_for_test:
            with self.subTest(url_name=url):
                response = self.authorized_client.get(
                    reverse(url, kwargs=kwargs))
                for field, expected_type in form_fields.items():
                    with self.subTest(form_field_name=field):
                        form_field = response.context['form'].fields.get(field)
                        self.assertIsInstance(form_field, expected_type)

    def test_post_to_another_group(self):
        """.Проверяем, что новый пост попадает только в нужную группу."""
        group2 = Group.objects.get(pk=2)
        Post.objects.create(
            author=PostPagesTests.user,
            group=group2,
            text='Тестовый пост для 2-й группы'
        )
        # Если кол-во постов в 1-й группе осталось 13, то всё ок
        response1 = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug1'}))
        group1_post_count = response1.context['page_obj'].paginator.count
        self.assertEqual(group1_post_count, TEST_POST_COUNT)
        # Если кол-во постов во 2-й группе 1, то ок; проверим его тоже
        response2 = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug2'}))
        group2_post_count = response2.context['page_obj'].paginator.count
        self.assertEqual(group2_post_count, 1)
        post_to_group2 = response2.context['page_obj'][0]
        self.assertEqual(post_to_group2.text, 'Тестовый пост для 2-й группы')

    def test_displaying_post_images(self):
        """.Проверяем передачу картинки на страницы с постами."""
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
            content_type='image/gif',
        )
        self.new_post = Post.objects.create(
            author=PostPagesTests.user,
            group=PostPagesTests.group,
            text='Тестовый пост с изображением',
            image=uploaded
        )

        def assert_new_post_with_image_ok(post):
            self.assertEqual(post.author.username, 'auth')
            self.assertEqual(post.group.title, 'Тестовая группа #1')
            self.assertEqual(post.text, 'Тестовый пост с изображением')
            self.assertEqual(post.image, 'posts/small.gif')

        # Проверяем пост с картинкой в списках - самый свежий с индексом 0
        for url, kwargs, _ in self.pages_for_tests[:3]:
            with self.subTest(url_name=url):
                response = self.guest_client.get(reverse(url, kwargs=kwargs))
                new_post = response.context.get('page_obj')[0]
                assert_new_post_with_image_ok(new_post)
        # Проверяем страницу поста с картинкой
        url, kwargs = 'posts:post_detail', {'post_id': self.new_post.id}
        with self.subTest(url_name=url):
            response = self.guest_client.get(reverse(url, kwargs=kwargs))
            new_post = response.context.get('post')
            assert_new_post_with_image_ok(new_post)

    def test_new_comment_for_authorized_users(self):
        """.Проверяем создание комментария для авторизованного пользователя.
        """
        url = reverse('posts:add_comment', kwargs={'post_id': self.post.id})
        data = {'text': 'Тестовый комментарий.'}
        response = self.authorized_client.post(url, data, follow=True)
        self.assertRedirects(response, f'/posts/{self.post.id}/')
        new_response = self.guest_client.get(f'/posts/{self.post.id}/')
        new_comment = new_response.context.get('comments')[0].text
        self.assertEqual(new_comment, data['text'])

    def test_cache_for_the_index_page(self):
        """.Проверяем кэширование главной страницы."""
        response1 = self.guest_client.get(reverse('posts:index'))
        Post.objects.all().order_by('-id')[0].delete()  # удаляем самый свежий
        response2 = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(response1.content, response2.content)
        cache.clear()
        response3 = self.guest_client.get(reverse('posts:index'))
        self.assertNotEqual(response1.content, response3.content)

    def test_new_post_displayed_for_followers(self):
        """.Проверяем показ нового поста для подписчиков и для нормальных."""
        self.follower_client = Client()
        self.follower_client.force_login(user=self.follower)
        self.not_follower_client = Client()
        self.not_follower_client.force_login(user=self.not_follower)
        new_post = Post.objects.create(
            author=self.user, text='Тестовый пост для подписчиков')
        Post.objects.create(author=self.user2, text='Пост от иного автора')
        response1 = self.follower_client.get(reverse('posts:follow_index'))
        top_post1 = response1.context.get('page_obj')[0]
        self.assertEqual(top_post1, new_post)
        response2 = self.not_follower_client.get(reverse('posts:follow_index'))
        top_post2 = response2.context.get('page_obj')[0]
        self.assertNotEqual(top_post2, new_post)

    def test_users_can_subscribe_to_others(self):
        """.Проверяем, что пользователи могут подписываться на других
        авторов.
        """
        self.assertFalse(
            Follow.objects.filter(user=self.user, author=self.user2).exists())
        self.authorized_client.get(reverse(
            'posts:profile_follow', kwargs={'username': 'another_author'}))
        self.assertTrue(
            Follow.objects.filter(user=self.user, author=self.user2).exists())

    def test_users_can_unsubscribe_from_others(self):
        """.Проверяем, что пользователи могут отписываться от других
        авторов.
        """
        Follow.objects.create(user=self.user, author=self.user2)
        self.authorized_client.get(reverse(
            'posts:profile_unfollow', kwargs={'username': 'another_author'}))
        self.assertFalse(
            Follow.objects.filter(user=self.user, author=self.user2).exists())

    def test_users_cannot_subsribe_to_themselves(self):
        """.Проверяем, что пользователи не могут подписаться на самих себя."""
        self.authorized_client.get(reverse(
            'posts:profile_follow', kwargs={'username': 'auth'}))
        self.assertFalse(
            Follow.objects.filter(user=self.user, author=self.user).exists())
